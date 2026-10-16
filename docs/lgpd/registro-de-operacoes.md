# Registro das operações de tratamento (LGPD, art. 37)

Registro mantido pelo controlador. Descreve o que o sistema faz hoje (versão do aviso de
privacidade `2026-10-16`). Quando uma funcionalidade mudar o tratamento de dados, atualize
esta tabela, o aviso (`frontend/privacidade.html`) e a versão `POLITICA_PRIVACIDADE_VERSAO`.

- **Controlador:** definido em `CONTROLADOR_NOME` / `CONTROLADOR_CONTATO` (`.env`).
- **Encarregado (art. 41):** `ENCARREGADO_NOME` / `ENCARREGADO_EMAIL`. Agente de pequeno porte pode
  dispensar a indicação (Res. CD/ANPD nº 2/2022, art. 11), mas precisa manter canal de comunicação
  com o titular (o Suporte, categoria LGPD, cumpre esse papel).
- **Titulares:** estudantes universitários e professores, todos com 18 anos ou mais (declaração no
  cadastro; exigência dos termos da API Gemini).
- **Operadores:** Google (API Gemini: geração de texto e embeddings); provedor SMTP configurado em
  `SMTP_HOST` (e-mails de conta); hospedagem escolhida pelo controlador.

## Operações

| # | Operação | Dados | Finalidade | Base legal (art. 7º) | Compartilhamento | Retenção | Onde no código |
|---|---|---|---|---|---|---|---|
| 1 | Conta e acesso | nome, e-mail, hash da senha, tipo, aceite do aviso e da idade (datas), último acesso, e-mail verificado em | Criar e manter a conta | Execução de contrato (V) | — | Enquanto a conta existir | `auth_service`, `usuarios` |
| 2 | Sessão | hash do token, validade | Manter a pessoa conectada | Execução de contrato (V) | — | 7 dias ou até sair | `sessoes` |
| 3 | Controle de abuso | HMAC do IP e do e-mail digitado (com `SEGREDO_APP`) | Limitar tentativas de login, cadastro e recuperação de senha | Legítimo interesse (IX) e segurança (art. 46) | — | 15 min (login) e 1 dia (contadores) | `limite_service`, `pseudonimo` |
| 4 | Chat com o material | pergunta, resposta, PDFs usados como fonte | Responder com base no material; acompanhamento pelo professor | Execução de contrato (V) | Google: pergunta e trechos do material, **sem** nome, e-mail ou IP | `RETENCAO_HISTORICO_MESES` (12) | `chat_service`, `perguntas` |
| 5 | Cache de respostas | hash da pergunta, resposta, trechos | Evitar custo repetido | Execução de contrato (V) | — | `CACHE_RESPOSTAS_DIAS` (7) ou até o material mudar | `custo_service`, `cache_respostas` |
| 6 | Resumo, flashcards, simulado | texto do PDF, questões, respostas e nota | Ferramentas de estudo | Execução de contrato (V) | Google: texto do PDF | 12 meses (simulados e notas); simulado não respondido 7 dias | `estudo_service` |
| 7 | Trilha e baralho | objetivo, data-alvo, horas/semana, cartões e agenda de revisão | Planejar estudo e revisão espaçada | Execução de contrato (V) | — | Trilha: 12 meses após a data-alvo; cartões: até apagar | `trilha_service` |
| 8 | Turma | mensagens do chat da turma, eventos, entregas e notas de atividades | Comunicação e atividades da disciplina | Execução de contrato (V) | Colegas da turma veem nome e mensagens | 12 meses (mensagens, eventos) | `turma_service` |
| 9 | Materiais | PDFs do professor e texto extraído (com OCR) | Base do assistente | Execução de contrato (V) | Google: texto (embeddings e geração) | Enquanto a disciplina tiver o material | `documentos_service`, `indexacao_service` |
| 10 | Suporte | assunto, mensagem, resposta | Atender dúvidas e pedidos de titulares | Execução de contrato (V); obrigação legal (II) nos pedidos LGPD | Administradores | Respondidos: 12 meses | `suporte_service` |
| 11 | E-mails de conta | e-mail, token de uso único (só o hash fica no banco) | Confirmar e-mail, recuperar senha, trocar e-mail | Execução de contrato (V) | Provedor SMTP | Link: até 48 h; registro apagado 1 dia após uso ou validade | `links_conta_service`, `tokens_conta` |
| 12 | Registros técnicos (log) | id da conta, id da requisição, rota, status, duração (sem IP, sem query string, sem corpo) | Segurança e diagnóstico | Legítimo interesse (IX) | Hospedagem | Rotação do log da hospedagem (compose: 5 × 10 MB) | `logging_setup`, `observabilidade` |
| 13 | Métricas de uso | contagens diárias por evento, sem usuário | Entender uso e custo | Não é dado pessoal | — | 24 meses | `metricas` |
| 14 | Exportação e exclusão de conta | dados acima; registro da exclusão (id e data) | Direitos do titular (arts. 18 e 19) | Obrigação legal (II) | — | Registro de exclusão: enquanto houver backup que possa ser restaurado | `conta_service` |
| 15 | Backup | cópia do banco, PDFs e índice | Continuidade e recuperação | Legítimo interesse (IX) e segurança (art. 46) | Local definido pelo controlador | `RETENCAO_BACKUP_DIAS` (30) | `scripts/backup.py` |

## Transferência internacional (art. 33)

Os servidores do Google podem ficar fora do Brasil. A hipótese aplicável deve ser escolhida
pelo controlador com apoio jurídico (por exemplo, cláusulas-padrão contratuais da Res. CD/ANPD
nº 19/2024 ou outra prevista no art. 33). No plano **gratuito** da API Gemini o Google pode usar o
conteúdo enviado para melhorar produtos, com revisão humana; no plano **pago** vale o Data
Processing Addendum e o conteúdo não é usado para isso. Antes de uso com alunos reais: ativar o
faturamento e marcar `GEMINI_PLANO_PAGO=true` (o aviso de privacidade muda sozinho).

## Medidas de segurança (art. 46)

Ver `docs/privacidade-e-seguranca.md`. Resumo: PBKDF2 com 600 mil iterações, sessões e links
guardados só como hash, autorização por participação na disciplina, CSP sem scripts de terceiros,
checagem de origem em requisições que alteram dados, pseudonimização HMAC, retenção automática,
backup com rotação, contêiner sem privilégios e somente leitura.
