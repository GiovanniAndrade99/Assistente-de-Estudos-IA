# Diário de desenvolvimento

Registrem aqui problemas, decisões e aprendizados, com a data. Isso alimenta as
seções "Processo de desenvolvimento" e "Visão crítica" do relatório.

---

## 23/09: estrutura inicial e primeiro teste real

**Feito:** backend FastAPI + pipeline RAG + chat em HTML/JS, com o Claude (Claude Code)
como assistente de programação.

**Problemas encontrados:**

1. **ChromaDB travava no Windows com Python 3.14** (erro nativo "access violation" ao
   inserir vetores). Solução: implementamos um banco vetorial próprio com NumPy
   (`backend/vetores.py`), com similaridade de cosseno feita "na mão".
   *Lição:* bibliotecas com partes nativas (C/Rust) podem não acompanhar versões novas
   do Python. Uma solução mais simples também deixou o funcionamento do RAG mais claro.

2. **Modelo descontinuado:** o `gemini-2.5-flash`, que aparece na maioria dos tutoriais,
   retornou 404 ("no longer available to new users"). O modelo mais novo, `gemini-3.8-flash`,
   retornou 503 (alta demanda). Adotamos o `gemini-3.6-flash`.
   *Lição:* modelos de IA generativa mudam rápido. O nome do modelo fica no `.env` para
   poder ser trocado sem mexer no código.

3. **Limite do nível gratuito (erro 429):** muitas chamadas seguidas estouram a cota por minuto.
   Solução: novas tentativas automáticas com espera exponencial (2s, 4s, 8s...) para os
   erros 429 e 503.

**Primeiro teste (PDF de exemplo com 2 páginas):**
| Pergunta | Resultado |
|---|---|
| "O que é backpropagation?" (está no material) | Resposta correta, citou [1] → pág. 2, similaridade 0.77 |
| "Quem ganhou a Copa de 2002?" (fora do material) | "Não encontrei essa informação no material enviado." ✅ sem alucinação |

---

## 23/09: resumo, flashcards e simulado

**Feito:** `backend/estudo.py` com as 3 funcionalidades (o documento inteiro vai no prompt;
flashcards e simulado usam saída estruturada JSON). Frontend com cartões que giram e quiz com nota.
Criamos o PDF de demonstração `exemplos/exemplo_aulas_ia.pdf` (4 aulas).

**Resumo:** funcionou e ficou com boa qualidade (tópicos por aula, termos em negrito, páginas
citadas, perguntas de revisão), mas levou **136 s** no `gemini-3.6-flash`.

**Instabilidade do nível gratuito:** no mesmo dia, testamos o mesmo pedido de resumo em 4 modelos:

| Modelo | Resultado |
|---|---|
| gemini-3.6-flash | erro após 59,7 s: "Deadline expired" |
| gemini-3.5-flash | erro após 122,1 s: "Deadline expired" |
| gemini-3.1-flash-lite | erro após 37,3 s: "high demand" (503) |
| gemini-flash-latest | erro após 18,4 s: "high demand" (503) |

**Solução:** lista de **modelos reserva** (`gerar_conteudo` em `rag.py`) e **tempo limite** de 60 s
por tentativa. A interface mostra qual modelo gerou cada resposta.
*Lição:* APIs gratuitas de IA generativa não têm garantia de disponibilidade. Uma aplicação real
precisaria de plano pago, de outro provedor como reserva ou de um modelo local.
