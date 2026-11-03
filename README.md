# UniBot · Support Operations

Assistente de triagem de TI com orientações rastreáveis, encaminhamento humano e demonstração isolada por visitante. Projeto independente de **Thalita Neves**, inspirado em problemas de suporte técnico. Sem vínculo oficial ou integração com Afya, iFood ou ServiceNow.

## Problema e comportamento

Solicitações recorrentes chegam ao suporte sem orientação inicial. O UniBot recupera um artigo revisado, apresenta os passos e registra a resolução ou um chamado de demonstração. Quando não encontra evidência suficiente ou há empate, pede análise humana. A prioridade é uma regra da categoria, não uma avaliação inteligente do impacto real.

## Demonstração em 90 segundos

1. Descreva “Outlook não sincroniza”. Confira os passos e a referência `KB-OUTLOOK`.
2. Marque “Resolveu” e acompanhe o contador da sua sessão.
3. Consulte “internet caiu” e abra um chamado de demonstração.
4. Confira setor e prioridade na fila. Nada é enviado a uma equipe externa.
5. Consulte “cafeteira quebrada”: o sistema se abstém e permite triagem humana.
6. Abra uma janela anônima: ela não verá os chamados da sessão anterior.

Não forneça informações pessoais, credenciais nem incidentes reais. O aplicativo não pede nomes, telefone ou e-mail. O relato não é persistido. Registros de categoria e resultado expiram em 24 horas; a limpeza ocorre na próxima requisição. A demonstração não tem usuários cadastrados nem garantia de retenção permanente.

## Executar

Python 3.12. Na raiz deste repositório:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python app.py
```

Abra http://127.0.0.1:5000. No Windows, ative `.venv\Scripts\activate` e defina as variáveis pelo PowerShell. `.env.example` documenta as opções; `python app.py` não carrega `.env` automaticamente.

## Publicar com HTTPS

Use um host Python com Gunicorn ou Docker. Configure **raiz do projeto: raiz do repositório**, comando do `Procfile` e variáveis no painel do provedor:

- `SECRET_KEY`: segredo aleatório estável, igual para todos os workers. A ausência gera um segredo efêmero adequado apenas ao desenvolvimento com um processo.
- `COOKIE_SECURE=true`: exige HTTPS para a sessão.
- `DATABASE_PATH`: caminho para um volume persistente gravável, por exemplo `/data/unibot.db`.
- `ADMIN_PASSWORD_HASH`: hash Werkzeug, opcional. Vazio desabilita o login administrativo. Gere localmente com `generate_password_hash`; nunca compartilhe a senha ou o hash.

Para Docker local: defina `SECRET_KEY` em `.env`, mantenha `COOKIE_SECURE=false` para localhost HTTP e rode `docker compose up --build`. O Compose publica somente em localhost. Para acesso externo use um proxy HTTPS, sem expor o servidor de desenvolvimento Flask. Limites de requisição usam o endereço de conexão: atrás de proxy podem ser compartilhados por visitantes; não há confiança automática em `X-Forwarded-For`.

SQLite e rate limit compartilhado funcionam com workers em **uma instância**. Escala horizontal exige PostgreSQL/Redis e outra estratégia de sessão/limitação. O resumo opcional usa timeout de 8 segundos; cada consulta pode consumir uma chamada ao provedor. Configure também um teto de gastos no provedor antes de habilitá-lo publicamente.

## IA: capacidade e limites

O caminho padrão é **recuperação determinística por palavras-chave**, sem embeddings, treinamento ou LLM. As respostas mostram a referência da base. O corpus é pequeno e empates geram abstenção; isso não equivale a compreensão semântica nem a confiança probabilística.

Um adaptador opcional da API Anthropic resume **somente o artigo revisado**. Para habilitar, configure `ANTHROPIC_API_KEY` e `ANTHROPIC_MODEL` com um modelo disponível na sua conta. Nenhum relato bruto do visitante é enviado ao provedor. Os passos originais continuam visíveis. O resumo gerado pode conter erros: não é uma resposta automaticamente verificada. Falhas de rede, formato ou provedor mantêm a orientação revisada. A integração externa é coberta com simulações; a validação real depende de credencial e modelo do operador.

## Arquitetura e decisões

Navegador → Flask → recuperação da base → artigo referenciado → resultado/chamado → SQLite. Opcionalmente o artigo passa pelo adaptador Anthropic. JavaScript renderiza texto com `textContent`; CSP proíbe scripts inline. Backend valida tipos/tamanhos, exige CSRF, limita chamadas e protege administração por senha com hash. O painel público filtra pelo identificador da sessão; a administração expõe apenas contagens agregadas.

Decisões: monólito pequeno para facilitar execução e revisão; base curada antes de respostas generativas; SQLite para demonstração de uma instância; nenhum dado pessoal necessário. A sessão é assinada no cookie, não criptografada. Não incluir segredos nela. Rotação do segredo encerra sessões existentes.

## Verificação

```bash
python -m unittest discover -s tests -v
python evaluate.py
```

Testes cobrem isolamento, CSRF, validação, abstenção, fluxo, autenticação, repetição de resultado, expiração e integração simulada. `evaluate.py` mede 20 exemplos pequenos e explícitos, incluindo fora de escopo e ambiguidade. É uma regressão curada, **não uma estimativa de desempenho em produção**. CI executa testes, avaliação e build Docker.

Métricas da sessão: consultas, resoluções confirmadas e chamados. Não representam ganho de produtividade comprovado. Cliques de confirmação não validam resolução real.

## Evolução para um case AI Builder

- Validar o problema com usuários e medir uma linha de base de tempo/reincidência.
- Criar corpus independente de paráfrases, erros de digitação e múltiplos problemas; separar desenvolvimento de avaliação.
- Comparar regras, BM25 e embeddings com métricas de recuperação, abstenção e custo/latência.
- Adicionar RAG com citações verificadas, avaliação de groundedness e proteção contra prompt injection antes de fontes não confiáveis.
- Medir utilidade com avaliação humana e documentar falhas, não apenas exemplos bem-sucedidos.
- Integrar um sistema de tickets em sandbox, com confirmação e trilha de auditoria.

Esta entrega é um MVP de portfólio com controles para demonstração, não uma certificação de segurança ou um sistema de service desk pronto para dados corporativos.
