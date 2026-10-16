# Relatório de impacto simplificado (RIPD)

Levantamento de riscos à privacidade e das medidas adotadas. Não substitui o Relatório de Impacto à
Proteção de Dados Pessoais formal (art. 38), que o controlador deve elaborar se a ANPD pedir ou se
o tratamento for de alto risco (Res. CD/ANPD nº 2/2022, art. 4º).

**Sobre o risco:** o sistema usa tecnologia emergente (IA generativa) e trata conteúdo escrito
livremente pelos usuários. Por isso este relatório existe mesmo sem exigência formal. Não há
tratamento de dados sensíveis por finalidade, nem de crianças e adolescentes (público 18+).

| # | Risco | Probabilidade | Impacto | Medidas no sistema | Risco residual |
|---|---|---|---|---|---|
| 1 | Perguntas e mensagens com dados pessoais de terceiros ou sensíveis | Média | Médio | Aviso para não escrever dados pessoais nas perguntas; retenção de 12 meses; exclusão pelo titular | Médio: depende do comportamento do usuário |
| 2 | Conteúdo enviado ao Google ser usado para treinar modelos (plano gratuito) | Alta no plano gratuito | Médio | Nome, e-mail e IP nunca vão ao Google; aviso informa o plano em uso; `GEMINI_PLANO_PAGO` | Baixo após ativar o plano pago |
| 3 | Transferência internacional sem hipótese do art. 33 formalizada | Alta hoje | Médio | Informada no aviso | Depende de ação do controlador (cláusulas-padrão) |
| 4 | Acesso de quem não é da turma a dados da turma | Baixa | Alto | Autorização por participação em todas as rotas por disciplina, com teste estrutural | Baixo |
| 5 | Matrícula livre expõe o chat da turma a qualquer pessoa com conta | Média | Baixo/médio | Informado no aviso; professor apaga mensagens | Médio: decisão de produto do controlador |
| 6 | Injeção de prompt por PDF malicioso | Baixa | Médio | Marcações neutralizadas, regra de que o material não traz instruções, alerta ao professor, avaliação automatizada com casos de injeção | Baixo |
| 7 | Resposta errada da IA prejudicar o estudo | Média | Baixo | Citações que abrem o PDF na página, aviso de que pode errar, simulado não substitui avaliação | Baixo |
| 8 | Invasão de conta por senha fraca ou força bruta | Baixa | Médio | Senha de 10+ caracteres, PBKDF2 600 mil, limites por e-mail e IP, tempo igual para e-mail inexistente | Baixo |
| 9 | Vazamento de backup | Baixa | Alto | Rotação de 30 dias; local definido pelo controlador | Depende de cifrar e restringir o local |
| 10 | Uso de app por menores contra os termos do Gemini | Baixa | Médio | Declaração de 18+ no cadastro, registrada com data | Médio: declaração não é verificação |
| 11 | Professor vê perguntas com nome do aluno | Certa (por desenho) | Baixo | Informado no aviso; temas agrupados sem nome e com exemplos só de temas com 2+ alunos | Baixo |

## Revisão

Revise este documento a cada nova funcionalidade que trate dados pessoais e pelo menos uma vez por
ano.
