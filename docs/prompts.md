# Histórico de prompts

Registrem aqui cada versão dos prompts, o que mudou e por quê. O relatório pede
"prompts utilizados e justificativas técnicas", então esse histórico vira essa seção.

---

## Chat com o material (RAG): v1 (23/09)

**Onde:** `backend/prompts.py` → `SISTEMA_CHAT` e `montar_prompt_chat`
**Modelo:** gemini-3.6-flash, temperatura 0.2

**Instrução de sistema:**
> Você é um assistente de estudos. Responda à pergunta do aluno usando SOMENTE os
> trechos do material fornecidos abaixo. [...] Após cada informação, cite a fonte
> com o número do trecho entre colchetes [...] Se os trechos não contiverem a
> resposta, diga exatamente: "Não encontrei essa informação no material enviado."

**Justificativas:**
- "SOMENTE os trechos": reduz alucinação, porque o modelo não deve usar conhecimento externo.
- Citações numeradas `[n]`: o frontend transforma cada número em etiqueta com arquivo e página, e o aluno pode conferir.
- Frase fixa para "não encontrei": facilita medir nos testes quantas vezes o modelo admite não saber.
- Temperatura baixa (0.2): respostas mais fiéis e menos criativas.

**Resultados dos testes:** _(preencher na semana 6)_

---

## Resumo, flashcards e simulado: v1 (23/09)

**Onde:** `backend/prompts.py` → `SISTEMA_ESTUDO`, `PROMPT_RESUMO`, `PROMPT_FLASHCARDS`, `PROMPT_SIMULADO`
**Técnica:** diferente do chat, aqui **não** usamos RAG. O documento inteiro vai no prompt
(com marcações `[Página N]`), porque um resumo ou prova precisa cobrir todo o conteúdo, e não
só os trechos parecidos com uma pergunta. Isso aproveita a janela de contexto grande do Gemini.
Limite de 200 mil caracteres para não estourar a cota gratuita.

**Instrução de sistema (comum às três):**
> Você é um professor que prepara materiais de revisão para alunos universitários. Use SOMENTE
> o conteúdo do documento fornecido [...] O documento está dividido por marcações [Página N].

**Resumo** (temperatura 0.3): formato fixo em Markdown (`## Visão geral`, um `##` por tópico,
tópicos com `-`, **negrito**, páginas de origem `(p. X)` e `## Para revisar` com perguntas).
*Justificativa:* um formato previsível permite ao frontend renderizar títulos e listas, e as
páginas permitem ao aluno voltar ao material.

**Flashcards e simulado** (temperatura 0.5): **saída estruturada (JSON Schema)**. Passamos
classes Pydantic (`Flashcard`, `Questao`) em `response_schema`, e o Gemini é obrigado a
responder num JSON válido naquele formato.
*Justificativas:*
- Sem schema, o modelo às vezes devolve JSON com texto extra ou campos com outros nomes, e o frontend quebra.
- Temperatura um pouco maior (0.5) dá mais variedade nas perguntas.
- "Alternativas erradas plausíveis" evita questões óbvias demais.
- "Varie a posição da correta": sem isso, LLMs tendem a colocar a resposta certa sempre na mesma letra.
- Validação extra no código: questões sem exatamente 4 alternativas são descartadas.

---

## Modelo para novas versões

## <Nome>: vN (data)
**O que mudou:**
**Por quê (problema observado):**
**Resultado:**
