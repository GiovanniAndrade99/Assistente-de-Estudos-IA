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

```
[Navegador: HTML/CSS/JS]  login.html → index.html
        │  fetch() JSON + cookie de sessão
        ▼
[Backend: Python + FastAPI]
   ├─ /api/auth/...                      → cadastro, login, logout, usuário atual
   ├─ /api/disciplinas                   → listar / criar / remover disciplinas
   ├─ /api/disciplinas/{id}/documentos   → upload: PDF → trechos → embeddings → banco vetorial
   ├─ /api/disciplinas/{id}/chat         → pergunta → busca → prompt → Gemini → resposta com citações
   ├─ /api/disciplinas/{id}/resumo       → documento inteiro → Gemini → resumo
   ├─ /api/disciplinas/{id}/flashcards   → documento inteiro → Gemini (JSON) → cartões
   ├─ /api/disciplinas/{id}/simulado     → documento inteiro → Gemini (JSON) → questões
   ├─ /api/disciplinas/{id}/{eventos|atividades|videos|mensagens} → recursos da turma
   └─ /api/professor/{notas|perguntas}   → painel da turma (só professores)
        │
        ├──► SQLite (data/app.db): usuários, sessões, disciplinas, documentos, histórico
        ├──► Banco vetorial próprio (NumPy, data/indice): trechos + embeddings
        └──► Gemini API: embeddings + geração de texto (com modelos reserva)
```

## Estrutura

```
assistente-estudos/
├── backend/
│   ├── main.py      # rotas da API (FastAPI) e servidor do frontend
│   ├── auth.py      # cadastro, login, sessões e hash de senhas (PBKDF2)
│   ├── db.py        # banco SQLite: tabelas e funções de consulta
│   ├── rag.py       # pipeline RAG: extração, trechos, embeddings, busca, resposta
│   ├── estudo.py    # resumo, flashcards e simulado
│   ├── turma.py     # calendário, atividades, videoaulas e chat da turma
│   ├── vetores.py   # banco vetorial com NumPy (similaridade de cosseno)
│   ├── prompts.py   # todos os prompts do projeto
│   └── config.py    # chaves, modelos e parâmetros (tamanho do trecho, top-k...)
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

Segurança: senhas guardadas só como hash PBKDF2-SHA256 com sal (200 mil iterações) e sessão
em cookie HttpOnly. *Limitação conhecida:* a nota do simulado é calculada no navegador, então um
aluno com conhecimento técnico poderia enviar uma nota falsa. Em produção, a correção deveria
ser feita no servidor.

## Como rodar

1. Instale o **Python 3.11 ou mais novo** (em python.org, marque "Add Python to PATH").
2. Pegue uma chave gratuita do Gemini em https://aistudio.google.com/apikey
3. Na pasta do projeto:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # depois edite o .env e cole a chave
uvicorn backend.main:app --reload --port 8002
```

4. Abra http://localhost:8002

### Criar uma conta administrativa

Com o ambiente virtual ativado e na pasta raiz do projeto, execute `python -m scripts.criar_admin`.
O comando pede nome, e-mail e senha no terminal; a senha não é exibida nem salva em texto puro.
Administradores têm acesso às funções de professor.

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
