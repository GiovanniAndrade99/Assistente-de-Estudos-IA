# Privacidade e segurança

Controles técnicos do projeto e onde ficam. O lado jurídico e operacional (registro das operações,
atendimento ao titular, incidentes, legítimo interesse, RIPD e pendências) está em `docs/lgpd/`.
Publicar o aviso de privacidade não é, sozinho, declaração de conformidade com a LGPD: a validação
jurídica é do controlador (`docs/lgpd/pendencias-do-controlador.md`).

## Contas e sessões

- Senha de 10 a 128 caracteres, derivada com PBKDF2-HMAC-SHA256, sal individual e 600.000 iterações
  ([OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)).
  Hashes antigos são atualizados no login.
- Login com e-mail inexistente leva o mesmo tempo (hash fictício), para não revelar quem tem conta.
- Sessão: token aleatório, banco guarda só o SHA-256; cookie `HttpOnly`, `SameSite=Lax`, `Secure` em
  produção, validade de 7 dias. Sessão sem validade é recusada.
- Links por e-mail (recuperar senha 30 min, confirmar e-mail 48 h, trocar e-mail): token só como hash,
  uso único, no fragmento da URL (`#token=`), que não vai para logs nem para o cabeçalho `Referer`.
  Redefinir a senha derruba todas as sessões.
- Limites por pessoa e por pseudônimo de IP/e-mail (HMAC com `SEGREDO_APP`): login, cadastro,
  recuperação de senha, chat, estudo, upload, exportação; cota diária de pedidos à IA.

## Autorização

- Rotas por disciplina exigem participação: professor dono, aluno matriculado ou admin
  (`api/dependencias.py`). Um teste estrutural (`tests/test_autorizacao.py`) falha se uma rota nova
  com `disciplina_id` não tiver a checagem.
- Professores só veem as próprias disciplinas; enviar ou remover PDF, atividades e vídeos só o dono.
- Admin: métricas, chamados, destino de disciplinas sem professor.

## HTTP

- Política de conteúdo (CSP) sem `unsafe-inline`: `default-src 'self'`, sem scripts, estilos ou fontes
  de terceiros; fontes e ícones servidos pelo próprio app. Vídeos só por `youtube-nocookie.com`.
- `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`; HSTS em
  produção; `Cache-Control: no-store` na API.
- Requisições que alteram dados (POST, PUT, PATCH, DELETE) vindas de outra origem recebem 403.
- Erro de validação (422) nunca devolve o valor enviado (poderia ser uma senha); erros internos
  respondem mensagem genérica com `request_id`.
- `/docs`, `/redoc` e `/openapi.json` desligados em produção.

## Logs e métricas

- Log JSON com id da conta e da requisição, rota, status e duração. Sem IP, sem query string, sem
  corpo, sem e-mail. O log de acesso do uvicorn fica desligado.
- Métricas: só contagens diárias por evento, sem coluna de usuário (não são dados pessoais).

## IA (Google Gemini)

- O Google recebe o texto dos PDFs e as perguntas; nunca nome, e-mail ou IP.
- Plano gratuito: o Google pode usar o conteúdo para melhorar produtos, com revisão humana. O aviso
  de privacidade diz qual plano está em uso (`GEMINI_PLANO_PAGO`).
- Injeção de prompt: material e pergunta vão entre marcações neutralizadas, a instrução de sistema diz
  que o material nunca traz ordens, e PDFs com frases de comando ganham alerta para o professor
  (`aplicacao/seguranca_ia.py`). A avaliação automatizada (`scripts/avaliar_ia.py`) inclui casos de
  injeção.
- Cache de respostas sem dado de quem perguntou (a chave é um hash).

## Retenção, exclusão e backup

- Limpeza automática na subida e a cada `INTERVALO_LIMPEZA_HORAS` (`aplicacao/retencao_service.py`),
  ou manual com `python -m scripts.limpeza`. Prazos no `.env` e no aviso de privacidade.
- Exportação completa (`GET /api/conta/meus-dados`) e exclusão de conta pela própria pessoa. Testes
  estruturais garantem que toda tabela ligada a `usuarios` entra na exportação e é tratada na exclusão.
- Backup: `python -m scripts.backup` (API de backup do SQLite + PDFs + índice, rotação de 30 dias).
  Restauração: `python -m scripts.restaurar_backup backups/<pasta> --confirmar` com o servidor parado;
  refaz as exclusões de conta registradas depois do backup.

## Implantação

- Contêiner com usuário sem privilégios, sistema de arquivos somente leitura (só `data/`, `backups/`
  e `/tmp` graváveis), porta publicada só em `127.0.0.1` e rotação de log (`docker-compose.yml`).
  Ponha um proxy com HTTPS na frente.
- Em produção o servidor não sobe sem `SEGREDO_APP`, `CONTROLADOR_NOME` e `CONTROLADOR_CONTATO`, nem com
  `IDADE_MINIMA` abaixo de 18.
- CI (`.github/workflows/ci.yml`): lint, testes em Python 3.12 e 3.14 e build da imagem a cada push.

## Cookies e armazenamento local

Só o cookie essencial `sessao`. No `localStorage`: tema, última tela e disciplina, aviso de cookies
visto e lembretes já mostrados. Sem analytics nem publicidade ([guia de cookies da ANPD](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_cookies_e_protecao_de_dados_pessoais)).
