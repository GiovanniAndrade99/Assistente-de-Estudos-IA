# Resposta a incidentes de segurança com dados pessoais

Base: LGPD, art. 48, e Resolução CD/ANPD nº 15/2024 (Regulamento de Comunicação de Incidente de
Segurança). Confira sempre o texto vigente em gov.br/anpd.

**Prazo:** se o incidente puder trazer risco ou dano relevante aos titulares, o controlador comunica
a **ANPD** e os **titulares afetados em até 3 dias úteis**, contados do conhecimento de que o
incidente afetou dados pessoais. Informações que faltarem podem ser complementadas depois, de
forma fundamentada. Todo incidente, comunicado ou não, entra no **registro de incidentes**, que deve
ser guardado por pelo menos 5 anos.

## 1. Detectar e registrar (hora zero)

Sinais neste sistema: picos de `429`/`403` no log, erros 500 em sequência, `alerta_tokens_dia` no
log ou na tela de Métricas (possível uso indevido da chave do Gemini), backup acessado por quem
não devia, chave ou `.env` publicada por engano.

Anote: quem percebeu, quando, o que foi visto e os `request_id` envolvidos.

## 2. Conter (primeiras horas)

| Situação | Ação |
|---|---|
| Sessões possivelmente roubadas | `DELETE FROM sessoes;` (todos entram de novo) |
| Senha de uma conta comprometida | Pedir recuperação de senha (derruba as sessões da conta) |
| `GEMINI_API_KEY` exposta | Revogar no Google AI Studio, gerar outra, atualizar `.env`, reiniciar |
| `SEGREDO_APP` exposto | Gerar outro (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), reiniciar. Os pseudônimos antigos deixam de valer, sem efeito para os usuários |
| Senha do SMTP exposta | Trocar no provedor e no `.env` |
| Servidor invadido | Tirar do ar, preservar uma cópia do disco para análise, subir de backup limpo |
| Backup vazado | Avaliar quais dados estavam nele (data do backup) |

## 3. Avaliar o risco

Considere: tipo de dado (senhas estão em hash forte; perguntas e mensagens podem ter conteúdo
pessoal), quantidade de pessoas, se os dados estavam legíveis, se há como reverter e as possíveis
consequências (constrangimento, fraude, discriminação). Registre a conclusão e o motivo.

## 4. Comunicar (até 3 dias úteis, se houver risco ou dano relevante)

**À ANPD:** pelo formulário de comunicação de incidente no site da ANPD (gov.br/anpd).
**Aos titulares:** e-mail para cada pessoa afetada (e aviso no sistema), em linguagem simples, com:
o que aconteceu e quando; quais dados; riscos; o que já foi feito; o que a pessoa pode fazer (trocar
senha, desconfiar de e-mails); contato do encarregado.

Modelo curto:

> Assunto: Aviso sobre a segurança dos seus dados no Assistente de Estudos
>
> Em [data], identificamos [o que aconteceu]. Os dados envolvidos foram [quais]. Já [medidas
> tomadas]. Recomendamos que você [ações]. Dúvidas: [ENCARREGADO_EMAIL].

## 5. Corrigir e aprender

Corrija a causa, acrescente um teste que pegaria o problema, atualize este documento e registre no
`docs/diario-desenvolvimento.md` (sem dados pessoais).

## Registro de incidentes (modelo)

| Data do conhecimento | Descrição | Dados e titulares afetados | Risco avaliado | Comunicado à ANPD? Quando | Comunicado aos titulares? Quando | Medidas |
|---|---|---|---|---|---|---|
| | | | | | | |
