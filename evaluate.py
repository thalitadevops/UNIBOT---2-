"""Small, transparent regression corpus. Not a generalization benchmark."""
from app import retrieve
CASES=[('outlook não sincroniza','outlook'),('e-mail com erro','outlook'),('teams não abre','teams'),('reunião travando','teams'),('senha expirada','senha'),('usuário bloqueado','senha'),('internet caiu','wifi'),('wi-fi sem sinal','wifi'),('impressora sem papel','impressora'),('toner acabou','impressora'),('projetor sem imagem','projetor'),('HDMI falhou','projetor'),('computador lento','computador'),('notebook travando','computador'),('portal acadêmico caiu','sistema'),('página não abre','sistema'),('cafeteira quebrada',None),('ar condicionado pingando',None),('olá bom dia',None),('outlook e impressora',None)]
def evaluate():
    correct=0;failures=[]
    for text,expected in CASES:
        result=retrieve(text);actual=result['key'] if result else None
        correct+=actual==expected
        if actual!=expected:failures.append({'input':text,'expected':expected,'actual':actual})
    return {'cases':len(CASES),'correct':correct,'accuracy':correct/len(CASES),'failures':failures}
if __name__=='__main__':
    import json
    result=evaluate();print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(result['failures']))
