
# UniBot Afya - Chatbot de Suporte Final

Versão focada em demonstração para liderança:
- Tela principal como chat de suporte real
- Interface simples e intuitiva para professor/usuário
- Opções de problemas comuns
- Campo livre para digitar o problema
- Solução guiada antes de abrir chamado
- Encaminhamento automático para setor responsável
- Chamado com nome, telefone, local e descrição
- Área administrativa separada em `/admin`
- Banco SQLite local
- Logs em TXT

## Rodar localmente

1. Abra o CMD dentro da pasta do projeto.
2. Execute:

```cmd
pip install -r requirements.txt
python app.py
```

3. Abra:

```text
http://localhost:5000
```

## Abrir em outro computador na mesma rede

Use:

```text
http://SEU_IP:5000
```

Exemplo:

```text
http://10.1.24.173:5000
```

## Área administrativa

```text
http://localhost:5000/admin
```

## Railway

Suba a pasta para o GitHub e conecte o repositório no Railway.
O projeto já tem:
- `requirements.txt`
- `Procfile`
- `runtime.txt`
