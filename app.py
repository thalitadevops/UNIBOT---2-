"""UniBot: isolated public demo and authenticated operational console."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.security import check_password_hash
from werkzeug.exceptions import HTTPException
from knowledge import ISSUES


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def retrieve(text):
    """Rank curated articles by independent keyword hits; abstain on no evidence."""
    text = normalize(text)
    ranked = []
    for key, item in ISSUES.items():
        hits = [word for word in item['keywords'] if re.search(r'(?<!\w)' + re.escape(normalize(word)) + r'(?!\w)', text)]
        if hits:
            generic = {'erro', 'travando', 'mensagem', 'acesso', 'entrar', 'tela', 'pagina', 'liga'}
            score = sum(0.2 if term in generic else 1 for term in set(map(normalize, hits)))
            ranked.append((score, key, item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    if not ranked or (len(ranked) > 1 and ranked[0][0] == ranked[1][0]):
        return None
    score, key, item = ranked[0]
    return {'key': key, 'title': item['title'], 'sector': item['sector'], 'priority': item['priority'],
            'steps': item['solution'], 'source': f'KB-{key.upper()}', 'match_score': score}


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        DATABASE=os.environ.get('DATABASE_PATH', str(Path(__file__).parent / 'instance' / 'unibot.db')),
        ADMIN_PASSWORD_HASH=os.environ.get('ADMIN_PASSWORD_HASH', ''),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', 'false').lower() == 'true',
        MAX_CONTENT_LENGTH=8192, DEMO_TTL_HOURS=24,
        ANTHROPIC_API_KEY=os.environ.get('ANTHROPIC_API_KEY', ''),
        ANTHROPIC_MODEL=os.environ.get('ANTHROPIC_MODEL', ''))
    if config:
        app.config.update(config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, owner TEXT NOT NULL, created REAL NOT NULL,
        kind TEXT NOT NULL, issue TEXT NOT NULL, latency INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY, owner TEXT NOT NULL, created REAL NOT NULL,
        issue TEXT NOT NULL, sector TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Aberto');
        CREATE TABLE IF NOT EXISTS limits(bucket TEXT PRIMARY KEY, start REAL NOT NULL, count INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS tickets_owner ON tickets(owner);
        CREATE INDEX IF NOT EXISTS events_owner ON events(owner);
        ''')

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=10)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close(_error):
        if 'db' in g:
            g.db.close()

    @app.before_request
    def protect():
        session.setdefault('owner', secrets.token_hex(16))
        session.setdefault('csrf', secrets.token_hex(24))
        g.start = time.perf_counter()
        if request.method in ('POST', 'PATCH', 'DELETE'):
            if not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), session['csrf']):
                return jsonify(error='Atualize a página e tente novamente.'), 403
            # SQLite-backed limits survive restarts and are shared by Gunicorn workers.
            identity = request.remote_addr or 'unknown'
            bucket = hashlib.sha256(identity.encode()).hexdigest() + (':login' if request.path == '/api/login' else ':api')
            now = time.time()
            cap = 5 if request.path == '/api/login' else 60
            conn = db()
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('DELETE FROM limits WHERE start < ?', (now - 60,))
            conn.execute('INSERT INTO limits(bucket,start,count) VALUES(?,?,1) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (bucket,now))
            count = conn.execute('SELECT count FROM limits WHERE bucket=?', (bucket,)).fetchone()[0]
            conn.commit()
            if count > cap:
                return jsonify(error='Limite temporário. Tente novamente em um minuto.'), 429
        cutoff = time.time() - app.config['DEMO_TTL_HOURS'] * 3600
        db().execute('DELETE FROM tickets WHERE created < ?', (cutoff,))
        db().execute('DELETE FROM events WHERE created < ?', (cutoff,))
        db().commit()

    @app.after_request
    def headers(response):
        response.headers.update({'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'same-origin',
            'X-Frame-Options': 'DENY', 'Cache-Control': 'no-store',
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'})
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    def payload():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            return None
        return value

    def event(kind, issue):
        db().execute('INSERT INTO events(owner,created,kind,issue,latency) VALUES(?,?,?,?,?)',
            (session['owner'],time.time(),kind,issue,int((time.perf_counter()-g.start)*1000)))
        db().commit()

    @app.get('/')
    def index():
        return render_template('index.html', csrf=session['csrf'], issues=ISSUES)

    @app.get('/health')
    def health():
        db().execute('SELECT 1')
        return jsonify(status='ok', version='2.0.0')

    @app.post('/api/assist')
    def assist():
        data = payload()
        if not data or not isinstance(data.get('text'), str) or not 3 <= len(data['text'].strip()) <= 1000:
            return jsonify(error='Informe um problema entre 3 e 1.000 caracteres.'), 400
        article = retrieve(data['text'])
        mode = 'curated'
        answer = None
        if article and app.config['ANTHROPIC_API_KEY'] and app.config['ANTHROPIC_MODEL']:
            # Only curated material is sent to the external provider, never the visitor's text.
            body = {'model':app.config['ANTHROPIC_MODEL'], 'max_tokens':300,
                'system':'Reescreva as instruções de suporte em português claro. Use apenas os passos fornecidos. Não acrescente comandos, links ou procedimentos. Retorne JSON com uma única propriedade "summary" (string).',
                'messages':[{'role':'user','content':json.dumps({'title':article['title'],'steps':article['steps']},ensure_ascii=False)}]}
            try:
                req = Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json','x-api-key':app.config['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'})
                with urlopen(req,timeout=8) as response:
                    result=json.loads(response.read(32768))
                output=json.loads(''.join(x.get('text','') for x in result.get('content',[]) if x.get('type')=='text'))
                if isinstance(output.get('summary'),str) and 0 < len(output['summary']) <= 2000:
                    answer=output['summary'];mode='ai-assisted'
            except (URLError, TimeoutError, ValueError, KeyError, TypeError, OSError):
                mode='fallback'
        event('matched' if article else 'abstained',article['key'] if article else 'unknown')
        session['issue'] = article['key'] if article else 'unknown'
        session['interaction'] = secrets.token_hex(12)
        return jsonify(article=article, mode=mode, summary=answer,
            message='Orientação encontrada na base revisada.' if article else 'Não encontrei uma orientação inequívoca. Encaminhe para análise humana.')

    @app.post('/api/outcome')
    def outcome():
        data=payload()
        if not data or data.get('outcome') not in ('resolved','ticket'):
            return jsonify(error='Resultado inválido.'),400
        interaction=session.get('interaction')
        if not interaction:
            return jsonify(error='Consulte uma orientação primeiro.'),409
        # A unique interaction marker provides durable idempotency even on retries.
        marker='done:'+interaction
        conn=db()
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM limits WHERE bucket=?',(marker,)).fetchone():
            conn.rollback();return jsonify(error='Resultado já registrado.'),409
        issue=session.get('issue','unknown')
        if data['outcome']=='resolved' and issue=='unknown':
            conn.rollback();return jsonify(error='Não há orientação para confirmar.'),400
        conn.execute('INSERT INTO limits VALUES(?,?,1)',(marker,time.time()+86400))
        ticket_id=None
        if data['outcome']=='ticket':
            article=ISSUES.get(issue,{})
            cur=conn.execute('INSERT INTO tickets(owner,created,issue,sector,priority) VALUES(?,?,?,?,?)',
                (session['owner'],time.time(),issue,article.get('sector','Suporte • Triagem'),article.get('priority','A avaliar')))
            ticket_id=cur.lastrowid
        conn.commit()
        event(data['outcome'],issue)
        session.pop('interaction',None)
        return jsonify(ok=True,ticket_id=ticket_id)

    @app.get('/api/dashboard')
    def dashboard():
        owner=session['owner']
        tickets=[dict(row) for row in db().execute('SELECT id,issue,sector,priority,status FROM tickets WHERE owner=? ORDER BY id DESC LIMIT 50',(owner,))]
        counts={row['kind']:row['n'] for row in db().execute('SELECT kind,count(*) n FROM events WHERE owner=? GROUP BY kind',(owner,))}
        return jsonify(tickets=tickets,counts=counts)

    @app.post('/api/reset')
    def reset():
        for table in ('events','tickets'):
            db().execute(f'DELETE FROM {table} WHERE owner=?',(session['owner'],))
        db().commit();session.pop('interaction',None)
        return jsonify(ok=True)

    @app.post('/api/login')
    def login():
        data=payload()
        password=data.get('password') if data else None
        stored=app.config['ADMIN_PASSWORD_HASH']
        if not isinstance(password,str) or len(password)>256 or not stored or not check_password_hash(stored,password):
            return jsonify(error='Acesso não autorizado.'),401
        session.clear();session['admin']=True
        session['owner']=secrets.token_hex(16);session['csrf']=secrets.token_hex(24)
        return jsonify(ok=True)

    @app.post('/api/logout')
    def logout():
        session.clear();return jsonify(ok=True)

    @app.get('/admin')
    def admin():
        if not session.get('admin'):
            return render_template('login.html',csrf=session['csrf']),401
        rows=db().execute('SELECT status,count(*) n FROM tickets GROUP BY status').fetchall()
        return render_template('admin.html',csrf=session['csrf'],rows=rows)

    return app


app=create_app()
if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.environ.get('PORT',5000)))
