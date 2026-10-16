# Pendências do controlador antes de uso com pessoas reais

O código cobre o que depende de software. Estes itens dependem de quem responde pelo serviço.

## Configuração (`.env`)

- [ ] `CONTROLADOR_NOME` e `CONTROLADOR_CONTATO` (obrigatórios em produção: o servidor não sobe sem eles).
- [ ] `ENCARREGADO_NOME` e `ENCARREGADO_EMAIL` (ou registrar a dispensa como agente de pequeno porte).
- [ ] `SEGREDO_APP` aleatório e guardado fora do repositório (obrigatório em produção).
- [ ] SMTP (`SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `SMTP_REMETENTE`, `SMTP_PROVEDOR_NOME`) e
      `APP_URL_BASE` com o endereço público em HTTPS. Sem SMTP, recuperação de senha e confirmação de
      e-mail ficam indisponíveis em produção.
- [ ] `CODIGO_PROFESSOR` forte, combinado só com professores.
- [ ] `ALERTA_TOKENS_DIA` / `TETO_TOKENS_DIA` e cotas por pessoa conforme o orçamento.

## Provedor de IA

- [ ] Ativar o faturamento no projeto do Gemini (serviços pagos + Data Processing Addendum) e então
      `GEMINI_PLANO_PAGO=true`.
- [ ] Definir a hipótese de transferência internacional (art. 33; Res. CD/ANPD nº 19/2024).

## Jurídico

- [ ] Validar bases legais, aviso de privacidade, avaliação de legítimo interesse e RIPD.
- [ ] Termos de uso do serviço.
- [ ] Contrato com operadores (hospedagem, SMTP).

## Operação

- [ ] HTTPS na frente do app (proxy reverso) e `APP_ENV=production`.
- [ ] Backup agendado (`python -m scripts.backup`) para local com acesso restrito e cifrado.
- [ ] Quem atende o Suporte LGPD e quem decide em incidentes (ver `resposta-a-incidentes.md`).
- [ ] Destino das disciplinas transferidas para "Professor removido" (tela de admin).
- [ ] Revisar mensalmente: chamados LGPD vencidos, alertas de tokens, documentos com alerta de instruções.

## Produto (decisões em aberto)

- [ ] Matrícula livre nas disciplinas: manter ou exigir convite/código da turma.
- [ ] Idade mínima: só pode baixar de 18 se trocar de provedor de IA.
