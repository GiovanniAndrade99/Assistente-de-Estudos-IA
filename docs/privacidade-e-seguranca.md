# Privacidade e segurança

Este documento descreve os controles técnicos presentes no projeto e os itens operacionais que o responsável pelo tratamento precisa definir antes de abrir o serviço a usuários reais. A publicação do aviso no frontend não representa, por si só, uma declaração de conformidade legal.

## Controles implementados

- Senhas são derivadas com PBKDF2-HMAC-SHA256, sal aleatório individual e 600.000 iterações, conforme o parâmetro recomendado pela [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Hashes antigos válidos são elevados gradualmente após login.
- Sessões usam token aleatório; somente o hash SHA-256 é armazenado no banco. O cookie é HttpOnly, SameSite=Lax, tem duração limitada e recebe Secure quando `APP_ENV=production`.
- Login limita tentativas por endereço de e-mail. A aplicação registra falhas sem incluir o e-mail nos logs.
- Respostas de API recebem `Cache-Control: no-store`; HTTPS em produção ativa HSTS.
- Não há cookie de analytics ou publicidade. A preferência de tema usa `localStorage`.

A transparência sobre cookies segue o princípio da ANPD de informar a finalidade e distinguir cookies estritamente necessários; o guia pode ser consultado [no portal da ANPD](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_cookies_e_protecao_de_dados_pessoais).

## Dados e serviços

O SQLite guarda identificadores e perfil de conta, sessões, perguntas e respostas, progresso, notas, mensagens, atividades, entregas e chamados de suporte. PDFs e índice vetorial ficam em `data/`. Solicitações de IA e trechos recuperados podem ser enviados ao Google Gemini conforme a configuração do backend. A interface carrega fontes do Google Fonts e incorpora vídeos via `youtube-nocookie.com`.

## Ações do responsável antes de produção

1. Identificar controlador, finalidade e hipótese legal para cada tratamento, incluindo conta, conteúdo escolar, logs, IA e serviços externos.
2. Definir e publicar contato do encarregado/canal de privacidade, retenção por categoria e procedimento para atender direitos dos titulares e responsáveis legais.
3. Revisar contratos, retenção e transferências internacionais com Google e demais fornecedores; informar isso aos usuários.
4. Definir salvaguardas para uso por crianças e adolescentes e obter orientação específica sobre o melhor interesse e participação dos responsáveis.
5. Configurar `APP_ENV=production`, HTTPS, backups protegidos, permissões mínimas para `data/`, atualização de dependências e plano de resposta a incidentes.
6. Definir processo de exclusão de contas e dados associados. A remoção direta de usuários ainda não é oferecida pela interface porque registros relacionados têm regras de retenção e vínculos que precisam ser definidos pelo controlador.

O aviso visível em `frontend/privacidade.html` também precisa ser revisado pelo responsável e atualizado com o canal de contato real antes de disponibilizar o sistema publicamente.
