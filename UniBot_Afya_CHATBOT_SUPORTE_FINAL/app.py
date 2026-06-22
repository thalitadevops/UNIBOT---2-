
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "unibot.db")

ISSUES = {
    "outlook": {
        "title": "Outlook / E-mail",
        "problem": "Outlook não abre, não sincroniza ou e-mail institucional com erro",
        "icon": "📧",
        "sector": "DTI - Microsoft 365",
        "priority": "Média",
        "keywords": ["outlook", "email", "e-mail", "correio", "caixa", "mensagem"],
        "solution": [
            "Feche o Outlook completamente.",
            "Abra o Gerenciador de Tarefas e finalize processos OUTLOOK.EXE, se existirem.",
            "Confirme se a internet está funcionando.",
            "Abra o Outlook novamente.",
            "Se persistir, reinicie o computador.",
            "Caso continue, o DTI precisa validar perfil, licença ou caixa de e-mail."
        ]
    },
    "teams": {
        "title": "Teams",
        "problem": "Teams não entra, fica carregando ou apresenta erro de login",
        "icon": "💬",
        "sector": "DTI - Microsoft 365",
        "priority": "Média",
        "keywords": ["teams", "reunião", "reuniao", "chamada", "microsoft teams"],
        "solution": [
            "Feche o Teams completamente.",
            "Tente acessar pelo navegador em teams.microsoft.com.",
            "Confirme se está usando o e-mail institucional correto.",
            "Verifique se a senha funciona em outros serviços.",
            "Se o erro persistir, o DTI precisa validar a conta ou o aplicativo."
        ]
    },
    "senha": {
        "title": "Senha e Acessos",
        "problem": "Senha esquecida, expirada, bloqueada ou erro de acesso",
        "icon": "🔐",
        "sector": "DTI - Contas e Acessos",
        "priority": "Alta",
        "keywords": ["senha", "login", "bloqueada", "bloqueado", "acesso", "entrar", "usuário", "usuario"],
        "solution": [
            "Confira se o usuário ou e-mail foi digitado corretamente.",
            "Verifique se o Caps Lock está ativado.",
            "Tente acessar novamente em outro navegador.",
            "Se aparecer conta bloqueada, senha expirada ou credencial inválida, será necessário reset pelo DTI."
        ]
    },
    "wifi": {
        "title": "Wi‑Fi / Internet",
        "problem": "Wi‑Fi não conecta, internet lenta ou sem rede",
        "icon": "📶",
        "sector": "DTI - Redes",
        "priority": "Alta",
        "keywords": ["wifi", "wi-fi", "internet", "rede", "conexão", "conexao", "sem sinal"],
        "solution": [
            "Desative e ative o Wi‑Fi do equipamento.",
            "Esqueça a rede e conecte novamente.",
            "Confirme se está conectado à rede correta.",
            "Reinicie o equipamento.",
            "Se outros usuários também estiverem sem rede, pode ser incidente de rede e deve ser encaminhado ao DTI."
        ]
    },
    "impressora": {
        "title": "Impressora",
        "problem": "Impressora não imprime, fila travada, toner ou papel",
        "icon": "🖨️",
        "sector": "DTI - Impressão",
        "priority": "Média",
        "keywords": ["impressora", "imprimir", "impressão", "impressao", "papel", "toner"],
        "solution": [
            "Verifique se a impressora está ligada.",
            "Confirme se há papel e toner.",
            "Selecione a impressora correta no computador.",
            "Reinicie a impressora.",
            "Tente imprimir uma página de teste.",
            "Se persistir, o DTI precisa verificar a fila, driver ou equipamento."
        ]
    },
    "projetor": {
        "title": "Projetor / TV / HDMI",
        "problem": "Projetor, TV, HDMI ou imagem da sala não funciona",
        "icon": "📽️",
        "sector": "DTI - Audiovisual",
        "priority": "Alta",
        "keywords": ["projetor", "tv", "hdmi", "imagem", "tela", "duplicar", "datashow"],
        "solution": [
            "Confira se o cabo HDMI/VGA está conectado corretamente.",
            "Pressione Windows + P e selecione 'Duplicar'.",
            "Verifique se a TV ou projetor está na entrada correta.",
            "Reinicie o notebook, se possível.",
            "Se for aula em andamento, o atendimento deve ser priorizado pelo DTI."
        ]
    },
    "computador": {
        "title": "Computador",
        "problem": "Computador lento, travando, sem ligar ou com erro",
        "icon": "💻",
        "sector": "DTI - Suporte Técnico",
        "priority": "Média",
        "keywords": ["computador", "pc", "notebook", "lento", "travando", "liga", "mouse", "teclado"],
        "solution": [
            "Reinicie o computador.",
            "Feche programas desnecessários.",
            "Verifique se há muitos arquivos ou abas abertas.",
            "Confirme se há espaço disponível em disco.",
            "Se o problema for recorrente, o DTI precisa analisar desempenho, hardware ou sistema."
        ]
    },
    "sistema": {
        "title": "Sistemas Institucionais",
        "problem": "Portal, sistema acadêmico ou site institucional com erro",
        "icon": "🧩",
        "sector": "DTI - Sistemas Institucionais",
        "priority": "Média",
        "keywords": ["portal", "sistema", "site", "acadêmico", "academico", "erro", "página", "pagina"],
        "solution": [
            "Atualize a página.",
            "Limpe cache e cookies do navegador.",
            "Teste em guia anônima.",
            "Teste em outro navegador.",
            "Anote ou tire print da mensagem de erro.",
            "Se continuar, o DTI precisa receber o print e a descrição do erro."
        ]
    }
}

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT,
            sector TEXT NOT NULL,
            priority TEXT NOT NULL,
            issue_key TEXT NOT NULL,
            issue_title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resolved (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            issue_key TEXT NOT NULL,
            issue_title TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.before_request
def ensure_db():
    init_db()

@app.route("/")
def index():
    public_issues = {k: {
        "title": v["title"],
        "problem": v["problem"],
        "icon": v["icon"],
        "sector": v["sector"],
        "priority": v["priority"],
        "solution": v["solution"]
    } for k, v in ISSUES.items()}
    return render_template("index.html", issues=public_issues)

@app.route("/api/match", methods=["POST"])
def match_issue():
    payload = request.get_json(force=True)
    text = payload.get("text", "").lower().strip()
    best_key = "sistema"
    for key, issue in ISSUES.items():
        if any(word in text for word in issue["keywords"]):
            best_key = key
            break
    issue = ISSUES[best_key]
    return jsonify({
        "key": best_key,
        "issue": {
            "title": issue["title"],
            "problem": issue["problem"],
            "icon": issue["icon"],
            "sector": issue["sector"],
            "priority": issue["priority"],
            "solution": issue["solution"]
        }
    })

@app.route("/api/resolved", methods=["POST"])
def resolved():
    payload = request.get_json(force=True)
    issue_key = payload.get("issue_key", "")
    issue = ISSUES.get(issue_key)
    if not issue:
        return jsonify({"ok": False, "error": "Problema inválido."}), 400

    created_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO resolved (created_at, issue_key, issue_title) VALUES (?, ?, ?)",
                (created_at, issue_key, issue["title"]))
    conn.commit()
    conn.close()

    with open(os.path.join(os.path.dirname(__file__), "data", "resolvidos.txt"), "a", encoding="utf-8") as f:
        f.write(f"{created_at} | Resolvido pelo UniBot | {issue['title']}\n")

    return jsonify({"ok": True})

@app.route("/api/ticket", methods=["POST"])
def ticket():
    payload = request.get_json(force=True)
    issue_key = payload.get("issue_key", "")
    issue = ISSUES.get(issue_key)
    if not issue:
        return jsonify({"ok": False, "error": "Problema inválido."}), 400

    name = payload.get("name", "").strip()
    phone = payload.get("phone", "").strip()
    location = payload.get("location", "").strip()
    description = payload.get("description", "").strip()

    if not name or not phone:
        return jsonify({"ok": False, "error": "Nome e telefone são obrigatórios."}), 400

    if not description:
        description = "Usuário tentou a solução orientada pelo UniBot, mas informou que o problema não foi resolvido."

    created_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tickets
        (created_at, name, phone, location, sector, priority, issue_key, issue_title, description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (created_at, name, phone, location, issue["sector"], issue["priority"], issue_key, issue["title"], description, "Aberto"))
    ticket_id = cur.lastrowid
    conn.commit()
    conn.close()

    with open(os.path.join(os.path.dirname(__file__), "data", "solicitacoes.txt"), "a", encoding="utf-8") as f:
        f.write(f"{created_at} | #{ticket_id} | {name} | {phone} | {location} | {issue['sector']} | {issue['priority']} | {issue['title']} | {description}\n")

    return jsonify({
        "ok": True,
        "ticket_id": ticket_id,
        "sector": issue["sector"],
        "priority": issue["priority"]
    })

@app.route("/admin")
def admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM resolved")
    total_resolved = cur.fetchone()[0]
    cur.execute("SELECT id, created_at, name, phone, location, sector, priority, issue_title, description, status FROM tickets ORDER BY id DESC LIMIT 50")
    tickets = cur.fetchall()
    cur.execute("SELECT sector, COUNT(*) FROM tickets GROUP BY sector ORDER BY COUNT(*) DESC")
    by_sector = cur.fetchall()
    conn.close()
    return render_template("admin.html", total_tickets=total_tickets, total_resolved=total_resolved, tickets=tickets, by_sector=by_sector)

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
