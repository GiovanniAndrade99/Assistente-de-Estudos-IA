# 📚 Assistente de Estudos com RAG

Aplicação para alunos e professores estudarem os materiais das disciplinas (PDFs) com IA
generativa (Gemini):

- **Chat com o material** (técnica RAG): responde **citando a fonte** (arquivo e página) e
  admite quando a resposta não está no material
- **Resumo**, **flashcards** e **simulado** gerados a partir de um PDF
- **Login** de alunos e professores, com materiais organizados **por disciplina**
- **Painel do professor**: notas dos simulados e perguntas feitas pelos alunos
- **Menu lateral** com as áreas de cada disciplina:
  - **Simulados**: gera simulados e mostra o histórico de notas do aluno
  - **Atividades**: professor publica com prazo e corrige com nota/comentário; aluno entrega
  - **Calendário**: eventos da turma (professor), lembretes pessoais (aluno) e prazos das atividades
  - **Videoaulas**: professor cadastra links (vídeos do YouTube tocam na própria página)
  - **Chat da turma**: conversa entre alunos e professor (atualiza a cada 4 s)
  - **Configurações**: nome, troca de senha, tema claro/escuro e encerrar outras sessões

## Arquitetura

O backend segue uma Clean Architecture "leve", em camadas (cada uma só conhece a de baixo):

```
[Navegador: HTML/CSS/JS]  login.html → index.html
        │  fetch() JSON + cookie de sessão HttpOnly
        ▼
[api/]            rotas FastAPI: leem a requisição, chamam a camada de aplicação, devolvem JSON
        │
        ▼
[aplicacao/]       regra de negócio (auth, disciplinas, documentos, chat, estudo, turma, professor, progresso)
        │
        ▼
[infraestrutura/]  acesso a dados: SQLite (db.py), banco vetorial (vetores.py), Gemini (rag.py)
        │
        ▼
[core/]            funções puras sem dependência de framework (hash de senha/token)
```

Toda requisição passa antes por uma middleware (`middlewares/observabilidade.py`) que gera um
**Request ID** único (ou aproveita o `X-Request-ID` enviado pelo cliente), devolve esse id no
cabeçalho da resposta e em qualquer corpo de erro (`{"detail": ..., "request_id": ...}`), e grava
uma linha de **log estruturado em JSON** (`infraestrutura/logging_setup.py`) com método, rota,
status, duração e esse mesmo id — assim dá para achar, a partir de um erro relatado pelo usuário,
exatamente as linhas de log daquela chamada.

Rotas da API:
```
   ├─ /api/health                         → healthcheck (usado por monitoramento)
   ├─ /api/auth/...                       → cadastro, login, logout, usuário atual
   ├─ /api/disciplinas                    → listar / criar / remover disciplinas
   ├─ /api/disciplinas/{id}/documentos    → upload: PDF → trechos → embeddings → banco vetorial
   ├─ /api/disciplinas/{id}/chat          → pergunta → busca → prompt → Gemini → resposta com citações
   ├─ /api/disciplinas/{id}/resumo        → documento inteiro → Gemini → resumo
   ├─ /api/disciplinas/{id}/flashcards    → documento inteiro → Gemini (JSON) → cartões
   ├─ /api/disciplinas/{id}/simulado      → documento inteiro → Gemini (JSON) → questões
   ├─ /api/disciplinas/{id}/{eventos|atividades|videos|mensagens} → recursos da turma
   └─ /api/professor/{notas|perguntas}    → painel da turma (só professores)
        │
        ├──► SQLite (data/app.db): usuários, sessões, disciplinas, documentos, histórico
        ├──► Banco vetorial próprio (NumPy, data/indice): trechos + embeddings
        └──► Gemini API: embeddings + geração de texto (com modelos reserva)
```

## Estrutura

```
assistente-estudos/
├── backend/
│   ├── main.py                 # app factory: logging, middlewares, routers, exception handlers
│   ├── excecoes.py             # exception handlers (sempre com request_id no corpo)
│   ├── config.py               # chaves, modelos, parâmetros e variáveis de ambiente
│   ├── prompts.py              # todos os prompts do projeto
│   ├── core/
│   │   └── seguranca.py        # hash de senha (PBKDF2) e de token de sessão — sem dependências
│   ├── infraestrutura/
│   │   ├── db.py                # banco SQLite: tabelas e funções de consulta
│   │   ├── rag.py                # pipeline RAG: extração, trechos, embeddings, busca, resposta
│   │   ├── vetores.py            # banco vetorial com NumPy (similaridade de cosseno)
│   │   └── logging_setup.py     # logging estruturado em JSON
│   ├── aplicacao/               # regra de negócio, um módulo por área
│   │   ├── auth_service.py, disciplinas_service.py, documentos_service.py,
│   │   │   chat_service.py, estudo_service.py, turma_service.py,
│   │   │   professor_service.py, progresso_service.py
│   ├── api/                     # rotas FastAPI (finas) + dependências de autenticação
│   │   ├── dependencias.py, auth_router.py, disciplinas_router.py, documentos_router.py,
│   │   │   chat_router.py, estudo_router.py, turma_router.py, professor_router.py,
│   │   │   progresso_router.py, saude_router.py
│   └── middlewares/
│       └── observabilidade.py   # request ID, log de acesso e cabeçalhos de segurança
├── frontend/
│   ├── login.html / login.js   # tela de entrar / criar conta
│   ├── index.html / app.js     # app principal: menu, assistente IA e painel do professor
│   ├── simulados.js / atividades.js / calendario.js
│   ├── videos.js / turma.js / config.js   # uma tela do menu em cada arquivo
│   └── style.css
├── docs/
│   ├── prompts.md                # histórico de versões dos prompts (para o relatório)
│   └── diario-desenvolvimento.md # problemas, decisões e testes (para o relatório)
├── exemplos/
│   └── exemplo_aulas_ia.pdf      # PDF de demonstração
├── requirements.txt
└── .env.example
```

## Permissões

| | Aluno | Professor |
|---|:-:|:-:|
| Criar disciplinas e enviar PDFs | ✅ | ✅ |
| Chat, resumo, flashcards, simulado | ✅ | ✅ |
| Remover disciplina | só quem criou | só quem criou |
| Painel da turma (notas e perguntas dos alunos) | ❌ | ✅ |

Segurança:
- Senhas: hash PBKDF2-SHA256 com sal (200 mil iterações).
- Sessão: cookie HttpOnly + SameSite=Lax, `secure` quando `APP_ENV=production`; no banco fica só
  o hash SHA-256 do token (nunca o valor bruto) e cada sessão expira (`DURACAO_SESSAO_SEGUNDOS`,
  padrão 7 dias).
- Login/cadastro: bloqueio temporário (429) após várias tentativas com senha errada seguidas
  (`LIMITE_TENTATIVAS_LOGIN`/`JANELA_TENTATIVAS_LOGIN_MINUTOS` em `config.py`).
- Upload de PDF: limitado a `TAMANHO_MAX_UPLOAD_MB` (padrão 20MB); nome de arquivo sempre
  saneado (`Path(...).name`), sem permitir caminhos como `../../`.
- Cabeçalhos de resposta: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` sempre;
  `Strict-Transport-Security` quando `APP_ENV=production`.
- Toda resposta de erro traz um `request_id` correlacionável com os logs do servidor (ver
  "Arquitetura"), sem vazar detalhes internos em erros inesperados.

*Limitação conhecida:* a nota do simulado é calculada no navegador, então um aluno com
conhecimento técnico poderia enviar uma nota falsa. Em produção, a correção deveria ser feita
no servidor.

## Como rodar

1. Instale o **Python 3.11 ou mais novo** (em python.org, marque "Add Python to PATH").
2. Pegue uma chave gratuita do Gemini em https://aistudio.google.com/apikey
3. Na pasta do projeto:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # depois edite o .env e cole a chave
uvicorn backend.main:app --reload
```

4. Abra http://localhost:8000

## Dados de demonstração: curso de Ciência da Computação

Com o servidor **parado**, rode na pasta raiz:

```
python -m scripts.popular_curso
```

O script cria 11 disciplinas (do 1º ao 6º semestre), cada uma com 3 aulas em PDF já indexadas
no RAG, as aulas e a prova no calendário e uma atividade com prazo. O conteúdo fica em
`scripts/dados_curso_cc.py`. As disciplinas pertencem ao professor `professor.cc@exemplo.com`
(senha `professor123`), criado se não existir; use `--email` para outro professor.
Rodar de novo não duplica nada: só tenta de novo o que falhou.

## Parâmetros para experimentar (em `backend/config.py`)

| Parâmetro | Padrão | Efeito |
|---|---|---|
| `TAMANHO_TRECHO` | 1000 | Trechos maiores dão mais contexto, mas a busca fica menos precisa |
| `SOBREPOSICAO` | 200 | Evita cortar uma ideia no meio de dois trechos |
| `TOP_K` | 5 | Quantos trechos vão para o modelo por pergunta |

Variar esses valores e registrar o resultado é um bom material para a **visão crítica** do relatório.

## Limitações conhecidas
- PDFs escaneados (só imagem) não têm texto extraível. Seria preciso usar OCR.
- O nível gratuito do Gemini tem limite de requisições por minuto.
