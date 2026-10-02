# Assistente de Estudos com RAG

Aplicação web para apoiar alunos e professores no estudo de materiais em PDF. O sistema usa recuperação de trechos (RAG) e modelos Google Gemini para responder perguntas com referências ao arquivo e à página.

## Funcionalidades

- Cadastro e login de alunos e professores; o cadastro de professor exige um código configurado pelo responsável.
- Disciplinas e materiais PDF organizados por turma.
- Chat com o conteúdo indexado, com citações de arquivo e página e resposta de ausência de informação quando o material não sustenta a pergunta.
- Resumo, flashcards e simulados gerados a partir de um PDF.
- Atividades com prazo, entrega do aluno e correção pelo professor responsável.
- Calendário com eventos da turma, lembretes individuais e prazos.
- Videoaulas por links do YouTube e chat da turma com atualização periódica.
- Painel do professor com perguntas e resultados de simulados da disciplina.
- Visão geral de aulas concluídas, atividades e progresso.
- Suporte com FAQ e chamados; administradores podem responder chamados.
- Configurações de perfil, senha, tema e encerramento de outras sessões.
- Aviso de privacidade e cookies: a aplicação usa cookie de sessão essencial, sem cookies próprios de analytics ou publicidade.

- A tela **Parcerias com universidades** mostra um exemplo de interface com universidades, cursos, notas e vestibulares fictícios. Ela não consulta fontes oficiais nem representa parcerias reais.

## Arquitetura

O backend é organizado em camadas:

```
Navegador (HTML, CSS, JavaScript)
    ↓ fetch() / JSON / cookie HttpOnly
backend/api/             rotas FastAPI e dependências de autorização
    ↓
backend/aplicacao/       regras de negócio e limites de uso
    ↓
backend/infraestrutura/  SQLite, índice vetorial e integração Gemini
backend/core/            funções de segurança independentes do framework
```

O pipeline de documentos extrai texto por página, divide em trechos, gera embeddings e os guarda em um índice vetorial próprio baseado em NumPy. No chat, a pergunta também vira embedding; os trechos mais semelhantes são enviados ao Gemini para produzir uma resposta com referências.

O SQLite guarda usuários, sessões, disciplinas, documentos, perguntas e respostas, notas, eventos, atividades e entregas, mensagens, chamados e registros de limites de uso. PDFs ficam em data/uploads e os vetores em data/indice.

A middleware de observabilidade atribui um Request ID, registra método, rota, status e duração em logs JSON e inclui o identificador em respostas. Também define cabeçalhos de segurança. Respostas da API recebem Cache-Control: no-store.

## Rotas principais da API

As rotas de saúde, cadastro, login e logout são públicas. As demais rotas de dados exigem sessão autenticada, com permissões adicionais por função e pela disciplina quando aplicável.

| Grupo | Rotas principais | Uso |
|---|---|---|
| Saúde | GET /api/health | Verifica acesso ao banco local |
| Autenticação | /api/auth/... | Cadastro, login, logout, perfil, troca de senha e sessões |
| Disciplinas | /api/disciplinas | Listagem, criação e remoção |
| Materiais | /api/disciplinas/{id}/documentos | Listar, enviar e remover PDFs |
| Estudo | /api/disciplinas/{id}/chat, /resumo, /flashcards, /simulado | Consultar material e gerar recursos |
| Turma | /api/disciplinas/{id}/eventos, /atividades, /videos, /mensagens | Calendário, atividades, vídeos e chat |
| Professor | /api/professor/notas, /api/professor/perguntas | Consultas da disciplina do professor |
| Progresso | /api/visao-geral, /api/aulas/{id}/concluida, /api/lembretes | Acompanhamento de estudo |
| Suporte | /api/suporte/chamados | Criar, listar, responder e remover chamados |
| IA | /api/ia/sobre | Informa provedor, modelos e parâmetros RAG |

## Permissões

| Ação | Aluno | Professor responsável | Administrador |
|---|:---:|:---:|:---:|
| Consultar material e usar recursos de estudo | Sim | Sim | Sim |
| Criar disciplina | Não | Sim | Sim |
| Enviar/remover PDFs da disciplina | Não | Sim | Sim |
| Gerenciar atividades, correções e videoaulas da disciplina | Não | Sim | Sim |
| Entregar atividade e usar chat da turma | Sim | Sim | Sim |
| Ver painel de notas e perguntas da disciplina | Não | Sim | Sim |
| Responder chamados | Não | Não | Sim |

A autorização para gerenciar uma disciplina confere se o usuário é o professor que a criou; administradores podem gerenciar todas. O cadastro público de professor só funciona quando CODIGO_PROFESSOR está definido no arquivo .env.

## Segurança implementada

- Senhas derivadas com PBKDF2-HMAC-SHA256, sal individual e 600.000 iterações. Hashes antigos válidos são atualizados após login.
- Tokens aleatórios de sessão; o banco guarda apenas o hash SHA-256 do token.
- Cookie de sessão HttpOnly e SameSite=Lax, com validade de até sete dias; Secure é ativado quando APP_ENV=production.
- Limite de cinco falhas de login por e-mail em 15 minutos e cinco cadastros por IP em 15 minutos.
- Limites de uso no banco: 20 perguntas ao chat, 15 operações de estudo e 10 uploads por usuário, cada grupo em uma janela de cinco minutos.
- Upload limitado a TAMANHO_MAX_UPLOAD_MB (20 MB por padrão), apenas PDF, nome saneado e leitura limitada em blocos.
- Cabeçalhos X-Content-Type-Options, X-Frame-Options e Referrer-Policy; HSTS quando APP_ENV=production.
- Mensagens de falha de login não registram o e-mail digitado nos logs.
- Chaves e configuração local ficam em .env, que é ignorado pelo Git.

## Requisitos

- Python 3.11 ou mais recente.
- Chave de API do Google Gemini para embeddings e geração de conteúdo.
- Acesso à internet para chamadas ao Gemini, fontes do Google Fonts e recursos externos carregados pela interface.

## Instalação e execução

Na pasta do projeto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite .env e configure pelo menos GEMINI_API_KEY. Para permitir cadastros de professor, substitua o valor de exemplo de CODIGO_PROFESSOR por um código compartilhado apenas com os professores.

Inicie o servidor:

```powershell
uvicorn backend.main:app --reload --port 8002
```

Acesse http://localhost:8002. Para Linux/macOS, a ativação do ambiente virtual é source .venv/bin/activate e a cópia do arquivo é cp .env.example .env.

As configurações do Gemini podem ser alteradas no .env:

| Variável | Padrão | Finalidade |
|---|---|---|
| GEMINI_API_KEY | vazio | Chave de acesso ao Gemini |
| GEMINI_MODEL | gemini-3.6-flash | Modelo principal de geração |
| GEMINI_MODELS_FALLBACK | gemini-3.5-flash,gemini-3.1-flash-lite | Modelos tentados como reserva |
| GEMINI_EMBED_MODEL | gemini-embedding-001 | Modelo de embeddings |
| APP_ENV | development | Em production ativa Secure no cookie e HSTS |
| LOG_LEVEL | INFO | Nível dos logs |
| TAMANHO_MAX_UPLOAD_MB | 20 | Limite do PDF enviado |

O nome e a disponibilidade dos modelos dependem do provedor e da conta configurada. Se uma chamada falhar, confira os modelos disponíveis e atualize os valores no .env.

## Criar administrador

Com o ambiente virtual ativado, execute na pasta raiz:

```powershell
python -m scripts.criar_admin
```

O script solicita nome, e-mail e senha no terminal, sem exibir a senha digitada.

## Dados de demonstração

Para criar o curso de Ciência da Computação com disciplinas, PDFs, eventos e atividades, pare o servidor e execute:

```powershell
python -m scripts.popular_curso
```

O processo usa a API do Gemini para indexar os PDFs, portanto depende de uma chave válida e de cota disponível. Pode ser retomado: itens já criados são ignorados. Por padrão, se ainda não existir a conta de demonstração, o script cria professor.cc@exemplo.com com a senha professor123. Essa credencial é somente para demonstração local; use --email para associar os dados a uma conta de professor existente e nunca reutilize a senha padrão.

## Estrutura do repositório

```
backend/
  prompts.py           instruções usadas pelo modelo
  api/                 rotas e autorização
  aplicacao/           regras de negócio e limites
  core/                hashing de senha e tokens
  infraestrutura/      SQLite, RAG, vetores e logs
  middlewares/          observabilidade e cabeçalhos
  main.py              montagem da aplicação
frontend/               telas, estilos e JavaScript
  parcerias.js           conteúdo demonstrativo, explicitamente fictício
scripts/                criação de administrador e dados de demonstração
docs/                   diário, prompts e privacidade/segurança
exemplos/               PDF de demonstração
data/                   banco, PDFs e índice vetorial (gerados localmente)
.env.example             exemplo de configuração
requirements.txt         dependências Python
```

## Parâmetros do RAG

Os parâmetros ficam em backend/config.py:

| Parâmetro | Padrão | Efeito |
|---|---:|---|
| TAMANHO_TRECHO | 1000 caracteres | Tamanho aproximado de cada trecho |
| SOBREPOSICAO | 200 caracteres | Contexto repetido entre trechos vizinhos |
| TOP_K | 5 | Número de trechos recuperados para responder |

Resumo, flashcards e simulados usam o texto extraído do PDF, limitado a 200.000 caracteres. O chat usa recuperação de trechos por similaridade de cosseno.

## Limitações conhecidas

- A área de parcerias contém universidades, notas MEC e datas de vestibular fictícias, apenas para demonstrar a interface; não há integração com universidades nem consulta a dados oficiais.
- PDFs escaneados sem camada de texto não são processados; o sistema não tem OCR.
- Os resultados de simulados enviados ao histórico não são uma avaliação segura: o cliente informa a pontuação. Use-os como acompanhamento informal, não como nota oficial.
- Resumo, flashcards e simulados podem usar apenas o início de documentos acima do limite de texto.
- A disponibilidade, latência, limites e nomes de modelos Gemini podem mudar; chamadas dependem de internet e da cota da conta.
- O aviso de privacidade descreve o comportamento técnico atual. Informações do controlador, canal de contato, retenção e processos de atendimento a titulares precisam ser definidos pelo responsável antes de uso público. Consulte docs/privacidade-e-seguranca.md.
- Não há testes automatizados versionados no repositório no momento. O diário descreve verificações manuais realizadas durante o desenvolvimento.

## Documentação de apoio

- docs/diario-desenvolvimento.md: decisões, problemas encontrados e verificações.
- docs/prompts.md: prompts usados e justificativas.
- docs/privacidade-e-seguranca.md: controles existentes e providências operacionais de privacidade.
