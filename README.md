# Assistente de Estudos com RAG

Aplicação web para estudantes universitários e professores estudarem materiais em PDF. O
assistente responde com base nos PDFs da disciplina (RAG com Google Gemini), cita arquivo e
página e abre o PDF na página citada. Público: maiores de 18 anos (exigência dos termos da API
Gemini).

## Funcionalidades

- **Contas:** cadastro de aluno e professor (professor exige `CODIGO_PROFESSOR`), confirmação de
  e-mail, recuperação de senha, troca de e-mail por link, encerramento de outras sessões.
- **Disciplinas e materiais:** catálogo, matrícula, envio de PDFs processados em segundo plano com
  barra de progresso e OCR para PDF escaneado (Tesseract).
- **Assistente:** chat com resposta em streaming e citações `[n]` que abrem o PDF na página; frase
  fixa quando o material não cobre a pergunta; resumo, flashcards e simulado corrigido no servidor.
- **Trilha até a prova:** plano semanal até a data-alvo (prova da disciplina, ENADE, transferência,
  segunda graduação) e baralho de flashcards com revisão espaçada (SM-2).
- **Turma:** atividades com entrega e correção, calendário, videoaulas (youtube-nocookie), chat.
- **Painel do professor:** notas (com exportação CSV), perguntas, temas das dúvidas agrupados sem
  IA e ranking "o que reforçar" por aula.
- **Universidades e vestibulares:** aba informativa com cursos de TI, CPC do MEC e datas de
  inscrição, com fontes (`backend/dados/universidades.json`). Não há parceria formal.
- **Privacidade (LGPD):** aviso de privacidade com dados da instalação, ciência e declaração de
  idade no cadastro, exportação e exclusão da conta pelo titular, canal LGPD no Suporte com prazo
  de 15 dias, retenção automática. Detalhes em `docs/lgpd/`.
- **Admin:** métricas de uso sem dado pessoal (com consumo de tokens do dia), chamados de suporte,
  destino de disciplinas de professores que excluíram a conta.

## Arquitetura

```
Navegador (HTML, CSS, JS sem frameworks; CSP sem scripts de terceiros)
    ↓ fetch / JSON / SSE / cookie HttpOnly
backend/api/             rotas FastAPI e autorização (participação na disciplina)
backend/aplicacao/       regras de negócio: chat, estudo, trilha, custo, conta, retenção...
backend/infraestrutura/  SQLite, índice vetorial NumPy, Gemini, e-mail, métricas, logs
backend/core/            hash de senha e tokens
backend/middlewares/     request id, cabeçalhos de segurança, checagem de origem
```

**RAG:** o PDF é lido por página (OCR se a página for imagem), dividido em trechos de 1.000
caracteres com 200 de sobreposição e transformado em embeddings (`gemini-embedding-001`). O índice
é um arquivo NumPy único gravado de forma atômica. Na pergunta, os 5 trechos mais parecidos
(cosseno) vão ao Gemini entre marcações neutralizadas (defesa contra injeção de prompt), e a
resposta volta em streaming (SSE). Respostas repetidas saem de um cache por disciplina, sem dado de
quem perguntou.

## Instalação

Requisitos: Python 3.12+ (testado em 3.12 e 3.14), chave da API Gemini e, para OCR, Tesseract com o
idioma português.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env         # Linux/macOS: cp .env.example .env
```

Preencha no `.env` pelo menos `GEMINI_API_KEY` e `SEGREDO_APP`. Depois:

```powershell
uvicorn backend.main:app --port 8002
python -m scripts.criar_admin       # conta de administrador (pede nome, e-mail e senha)
```

Acesse http://localhost:8002. Sem SMTP configurado, os links de e-mail (confirmação e recuperação de
senha) aparecem no log do servidor em desenvolvimento.

### Docker

```powershell
docker compose up -d --build        # usa o .env; porta 8002 só em 127.0.0.1
```

A imagem roda como usuário sem privilégios, com Tesseract em português, sistema de arquivos somente
leitura e volumes para `data/` e `backups/`. Em produção (`APP_ENV=production`, padrão da imagem) o
servidor não sobe sem `SEGREDO_APP`, `CONTROLADOR_NOME` e `CONTROLADOR_CONTATO`. Use um proxy com
HTTPS na frente.

## Configuração

Todas as variáveis, com comentários, estão em `.env.example`. As principais:

| Variável | Padrão | Para quê |
|---|---|---|
| `APP_ENV` | development | `production`: cookie Secure, HSTS, sem `/docs`, sem dados demo |
| `GEMINI_API_KEY` | — | Chave da API Gemini |
| `GEMINI_MODEL` / `GEMINI_MODELS_FALLBACK` | gemini-3.6-flash / 3.5-flash, 3.1-flash-lite | Modelo principal e reservas (429, 5xx, tempo esgotado) |
| `GEMINI_PLANO_PAGO` | false | Informa no aviso de privacidade se o plano pago (com DPA) está ativo |
| `SEGREDO_APP` | — | Segredo do HMAC de IP/e-mail no controle de tentativas |
| `CODIGO_PROFESSOR` | — | Código do cadastro de professor; vazio desativa esse cadastro |
| `CONTROLADOR_*`, `ENCARREGADO_*` | — | Quem trata os dados e o encarregado (aviso de privacidade) |
| `COTA_IA_DIA_ALUNO` / `_PROFESSOR` | 60 / 200 | Pedidos ao Gemini por pessoa em 24 h |
| `CACHE_RESPOSTAS_DIAS` | 7 | Validade do cache de respostas |
| `ALERTA_TOKENS_DIA` / `TETO_TOKENS_DIA` | 0 | Alerta e teto diário de tokens do sistema |
| `RETENCAO_*` | 12 meses, backup 30 dias | Prazos da limpeza automática |
| `SMTP_*`, `APP_URL_BASE` | — | Envio de e-mails de conta e endereço dos links |
| `OCR_HABILITADO`, `OCR_IDIOMAS` | true, por+eng | Leitura de PDF escaneado |

## Rotas da API

Públicas: saúde, cadastro, login, recuperação de senha e aviso de privacidade. As demais exigem
sessão e, nas rotas `/api/disciplinas/{id}/...`, participação na disciplina.

| Grupo | Rotas principais |
|---|---|
| Conta | `/api/auth/...`, `/api/conta/meus-dados`, `/api/conta/email`, `DELETE /api/conta`, `/api/conta/ciencia-privacidade` |
| Disciplinas | `/api/disciplinas`, `/publico`, `/matricular` |
| Materiais | `/api/disciplinas/{id}/documentos` (envio responde 202), `/documentos/{doc}/arquivo` (PDF) |
| Assistente | `/chat`, `/chat/stream` (SSE), `/resumo`, `/flashcards`, `/simulado`, `/simulados/{id}/respostas` |
| Trilha | `/trilha`, `/baralho`, `/baralho/hoje`, `/api/baralho/{id}/revisao`, `/api/universidades` |
| Turma | `/eventos`, `/atividades`, `/videos`, `/mensagens` |
| Professor | `/api/professor/notas`, `/notas.csv`, `/perguntas`, `/temas`, `/reforcar` |
| Admin | `/api/admin/metricas`, `/api/admin/disciplinas-sem-professor` |
| Outros | `/api/visao-geral`, `/api/lembretes`, `/api/suporte/...`, `/api/privacidade`, `/api/ia/sobre`, `/api/health` |

## Testes e qualidade

```powershell
pip install -r requirements-dev.txt
ruff check .
python -m pytest -q
```

**168 testes** (última execução). Cobrem autenticação, autorização (com teste estrutural de
rotas), privacidade (exportação e exclusão com testes estruturais de tabelas), links de e-mail,
indexação e OCR, streaming, injeção de prompt, cache e cotas, trilha e SM-2, painel do professor
e CSV. Usam SQLite temporário e um Gemini falso: nunca chamam a API nem tocam em `data/`.

O CI (`.github/workflows/ci.yml`) roda lint e testes em Python 3.12 e 3.14 e constrói a imagem
Docker a cada push e pull request.

### Avaliação da IA

`python -m scripts.avaliar_ia` monta a disciplina demo "Algoritmos e Programação" numa pasta
temporária, indexa os PDFs (mais um PDF com instrução escondida) e faz 45 perguntas do conjunto
`avaliacao/conjunto_algoritmos.json`: no material, fora do material e tentativas de injeção. Sai com
erro se o acerto ficar abaixo de `--meta` (0,9). Usa o Gemini real (só conteúdo demo, sem dado
pessoal). No GitHub, o workflow manual "Avaliação da IA" faz o mesmo com o segredo `GEMINI_API_KEY`.
Resultados registrados em `docs/prompts.md`.

## Operação

| Tarefa | Comando |
|---|---|
| Backup (banco, PDFs, índice; rotação de 30 dias) | `python -m scripts.backup` |
| Restaurar (servidor parado) | `python -m scripts.restaurar_backup backups/<pasta> --confirmar` |
| Aplicar a retenção agora | `python -m scripts.limpeza` |
| Curso demo de Ciência da Computação | `python -m scripts.popular_curso` (servidor parado; gera senha aleatória se faltar `--senha`) |
| Criar administrador | `python -m scripts.criar_admin` |

## Estrutura

```
backend/        API, regras de negócio, infraestrutura, prompts, dados das universidades
frontend/       páginas, estilos, scripts, fontes e ícones locais
scripts/        admin, backup, restauração, limpeza, curso demo, avaliação da IA
avaliacao/      conjunto de perguntas e métricas da avaliação da IA
tests/          testes automatizados
docs/           diário, prompts, privacidade e segurança, docs/lgpd/
data/           banco, PDFs e índice (gerado localmente, fora do Git)
```

## Limitações conhecidas

- O plano gratuito da API Gemini permite ao Google usar o conteúdo enviado para melhorar produtos;
  para alunos reais, ative o plano pago e marque `GEMINI_PLANO_PAGO=true`.
- A idade mínima é declarada, não verificada.
- A matrícula nas disciplinas é livre: qualquer pessoa com conta pode entrar numa turma e ver o chat.
- OCR depende da qualidade da imagem; resumo, flashcards e simulado usam no máximo 200 mil
  caracteres do documento.
- Um único processo do servidor (o índice vetorial e a fila de indexação assumem um worker).
- Nomes, cotas e disponibilidade dos modelos Gemini mudam; ajuste no `.env`.
- Itens jurídicos e operacionais estão em `docs/lgpd/pendencias-do-controlador.md`.

## Documentação

- `docs/diario-desenvolvimento.md`: decisões, problemas e verificações.
- `docs/prompts.md`: prompts, versões e resultados da avaliação.
- `docs/privacidade-e-seguranca.md`: controles técnicos.
- `docs/lgpd/`: registro das operações, atendimento ao titular, resposta a incidentes, legítimo
  interesse, RIPD simplificado e pendências do controlador.
