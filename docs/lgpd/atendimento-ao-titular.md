# Atendimento ao titular (LGPD, arts. 18 e 19)

Procedimento para responder pedidos de quem tem dados no sistema. Prazo: resposta completa em
**até 15 dias** a partir do pedido (art. 19, II). Confirmação simples de existência e acesso em
formato simplificado podem ser imediatos (art. 19, I).

## Canais

1. **Autoatendimento** (resolve a maior parte dos pedidos na hora): *Configurações › Seus dados*.
   - Baixar todos os dados (JSON): `GET /api/conta/meus-dados`. Cobre acesso e portabilidade
     (art. 18, II e V). Não inclui hash de senha nem tokens (segredos de segurança).
   - Corrigir nome (Configurações) e e-mail (confirmado por link no endereço novo): correção (III).
   - Excluir a conta (senha + digitar EXCLUIR): eliminação (VI).
2. **Suporte**, categoria *Privacidade e dados pessoais (LGPD)*. O chamado mostra ao administrador
   a data-limite de resposta (15 dias) e fica em vermelho quando vence.
3. **E-mail do encarregado** (`ENCARREGADO_EMAIL`), publicado no aviso de privacidade.

## Conferência de identidade

- Pedido feito logado (autoatendimento ou Suporte): a sessão já identifica a pessoa.
- Pedido por e-mail: responda apenas para o e-mail cadastrado na conta. Nunca envie dados para outro
  endereço sem confirmar por um canal já conhecido. Não peça documentos além do necessário.

## Como atender cada direito

| Direito (art. 18) | Como atender |
|---|---|
| I. Confirmação da existência de tratamento | Responder pelo Suporte; o aviso de privacidade descreve o tratamento |
| II. Acesso | Orientar o autoatendimento ou gerar o JSON: `python -c "from backend.aplicacao import conta_service as c; import json; print(json.dumps(c.exportar(ID), ensure_ascii=False, indent=2))"` |
| III. Correção | Autoatendimento; o admin corrige outros campos no banco se preciso |
| IV. Anonimização, bloqueio ou eliminação de dados desnecessários | Avaliar caso a caso; a retenção automática já apaga o que passou do prazo |
| V. Portabilidade | O JSON exportado é estruturado e legível por máquina |
| VI. Eliminação | Autoatendimento ou, se a pessoa não consegue entrar, `conta_service.excluir_conta` por um admin após confirmar identidade. Disciplinas e materiais de professor vão para a conta "Professor removido" (dados da turma, não da pessoa) |
| VII. Informação sobre compartilhamento | Aviso de privacidade, seção "Compartilhamento" |
| VIII/IX. Consentimento | O sistema não usa consentimento como base legal hoje |
| Art. 18, § 2º: oposição | Avaliar pedidos contra tratamentos por legítimo interesse (logs, controle de abuso); ver `avaliacao-legitimo-interesse.md` |
| Art. 20: revisão de decisão automatizada | Nenhuma decisão automatizada muda a situação acadêmica; correção de simulado contestada vai ao professor |

## Depois de excluir

A exclusão fica registrada em `PASTA_DADOS/exclusoes.jsonl` (só id e data). Ao restaurar um backup,
`scripts/restaurar_backup.py` refaz as exclusões. Os backups vencem em `RETENCAO_BACKUP_DIAS`.

## Registro

Mantenha o chamado do Suporte como registro do pedido e da resposta (fica 12 meses após a
resposta). Para pedidos por e-mail, abra você mesmo um chamado LGPD com o resumo.
