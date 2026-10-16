# Avaliação de legítimo interesse (LGPD, arts. 7º, IX, e 10)

Teste em três etapas para os tratamentos que usam legítimo interesse como base legal. Precisa
ser revisado pelo controlador com apoio jurídico; o Guia Orientativo da ANPD sobre legítimo
interesse (2024) traz o modelo completo.

## A. Controle de abuso (limites de tentativas)

1. **Finalidade legítima:** impedir força bruta em senhas, cadastro em massa por robôs e abuso da
   recuperação de senha. Protege os próprios titulares (art. 46).
2. **Necessidade:** guarda-se só o HMAC-SHA256 do IP e do e-mail digitado, com segredo do servidor
   (`SEGREDO_APP`), sem o valor original. O e-mail digitado de uma conta inexistente também vira
   pseudônimo. Prazo curto: 15 minutos (login) e 1 dia (contadores).
3. **Balanceamento:** impacto baixo (pseudônimo não reversível sem o segredo, vida curta, sem uso
   para outra finalidade). Expectativa razoável: usuários esperam proteção contra invasão de conta.
   **Salvaguardas:** transparência no aviso, limpeza automática, exclusão das chaves da pessoa ao
   excluir a conta, nada disso aparece no log.

**Conclusão:** legítimo interesse adequado.

## B. Registros técnicos (log de acesso)

1. **Finalidade:** investigar falhas e incidentes de segurança.
2. **Necessidade:** o log registra id da conta, id da requisição, método, rota, status e duração. Não
   registra IP, query string, corpo da requisição nem e-mail. O log de acesso do uvicorn está
   desligado.
3. **Balanceamento:** impacto baixo; rotação de log limita o tempo de guarda.
   **Salvaguardas:** acesso ao log só para quem administra o servidor.

**Conclusão:** legítimo interesse adequado.

## C. Backup

1. **Finalidade:** recuperar o serviço após falha ou incidente.
2. **Necessidade:** cópia integral é inerente ao backup; prazo de 30 dias com rotação.
3. **Balanceamento:** a exclusão de conta é refeita se um backup for restaurado
   (`exclusoes.jsonl`); o aviso informa que os dados permanecem nos backups até vencerem.
   **Salvaguardas:** guardar os backups em local com acesso restrito e, de preferência, cifrado.

**Conclusão:** legítimo interesse adequado, condicionado à proteção do local dos backups.

## Direito de oposição

Pedidos de oposição a esses tratamentos (art. 18, § 2º) chegam pelo Suporte. Como os três são
necessários à segurança do próprio serviço, a resposta normalmente explica a necessidade e as
salvaguardas; avalie casos excepcionais.
