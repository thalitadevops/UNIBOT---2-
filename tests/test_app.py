import json
import os
import tempfile
import unittest
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from app import create_app, retrieve

class UniBotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'SECRET_KEY':'test-only','DATABASE':os.path.join(self.tmp.name,'db.sqlite'), 'ADMIN_PASSWORD_HASH':generate_password_hash('test-password')})
        self.c=self.app.test_client();self.c.get('/')
    def tearDown(self):
        self.tmp.cleanup()
    def post(self,path,data,client=None):
        client=client or self.c
        with client.session_transaction() as s: token=s['csrf']
        return client.post(path,json=data,headers={'X-CSRF-Token':token})
    def test_pages_and_headers(self):
        for url in ['/','/health','/static/app.js','/static/style.css']:
            r=self.c.get(url);self.assertEqual(r.status_code,200)
            self.assertIn("script-src 'self'",r.headers['Content-Security-Policy']);r.close()
        self.assertEqual(self.c.get('/admin').status_code,401)
    def test_input_validation(self):
        for text in [None,42,[],{},'','x'*1001]:
            self.assertEqual(self.post('/api/assist',{'text':text}).status_code,400)
        self.assertEqual(self.c.post('/api/assist',json={'text':'wifi'}).status_code,403)
    def test_abstention(self):
        r=self.post('/api/assist',{'text':'cafeteira quebrada'}).json
        self.assertIsNone(r['article']);self.assertEqual(r['mode'],'curated')
        self.assertEqual(self.post('/api/outcome',{'outcome':'resolved'}).status_code,400)
    def test_session_isolation_and_reset(self):
        self.post('/api/assist',{'text':'wifi sem sinal'})
        self.assertEqual(self.post('/api/outcome',{'outcome':'ticket'}).status_code,200)
        self.assertEqual(len(self.c.get('/api/dashboard').json['tickets']),1)
        other=self.app.test_client();other.get('/')
        self.assertEqual(other.get('/api/dashboard').json['tickets'],[])
        self.assertEqual(self.post('/api/outcome',{'outcome':'ticket'}).status_code,409)
        self.post('/api/reset',{});self.assertEqual(self.c.get('/api/dashboard').json['tickets'],[])
    def test_resolved_and_auth(self):
        self.post('/api/assist',{'text':'outlook parou'})
        self.assertEqual(self.post('/api/outcome',{'outcome':'resolved'}).status_code,200)
        self.assertEqual(self.post('/api/login',{'password':'wrong'}).status_code,401)
        self.assertEqual(self.post('/api/login',{'password':'test-password'}).status_code,200)
        self.assertEqual(self.c.get('/admin').status_code,200)
        self.post('/api/logout',{});self.assertEqual(self.c.get('/admin').status_code,401)
    def test_rate_limit(self):
        for _ in range(5): self.post('/api/login',{'password':'wrong'})
        self.assertEqual(self.post('/api/login',{'password':'wrong'}).status_code,429)
    def test_no_raw_html_in_frontend(self):
        with open('static/app.js') as f: self.assertNotIn('innerHTML',f.read())
    def test_ai_fallback(self):
        self.app.config.update(ANTHROPIC_API_KEY='test',ANTHROPIC_MODEL='test-model')
        with patch('app.urlopen',side_effect=TimeoutError):
            r=self.post('/api/assist',{'text':'wifi caiu'}).json
        self.assertEqual(r['mode'],'fallback');self.assertIsNotNone(r['article'])
    def test_ai_summary_contract_and_privacy(self):
        self.app.config.update(ANTHROPIC_API_KEY='test',ANTHROPIC_MODEL='test-model')
        from unittest.mock import MagicMock
        result=MagicMock();result.__enter__.return_value.read.return_value=json.dumps({'content':[{'type':'text','text':'{"summary":"Confira a rede e tente novamente."}'}]}).encode()
        with patch('app.urlopen',return_value=result) as mocked:
            r=self.post('/api/assist',{'text':'wifi caiu contato privado@example.com'}).json
            sent=json.loads(mocked.call_args.args[0].data)
            self.assertNotIn('privado@example.com',json.dumps(sent))
        self.assertEqual(r['mode'],'ai-assisted')
    def test_expiration(self):
        self.post('/api/assist',{'text':'wifi sem sinal'});self.post('/api/outcome',{'outcome':'ticket'})
        import sqlite3
        with sqlite3.connect(self.app.config['DATABASE']) as db: db.execute('UPDATE tickets SET created=0')
        self.assertEqual(self.c.get('/api/dashboard').json['tickets'],[])

if __name__=='__main__':unittest.main()
