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

---

## 24/09: refactor para Clean Architecture, request ID, logs estruturados e segurança

**Feito:** o backend inteiro (antes um conjunto de módulos "script": rotas com SQL direto) foi
reorganizado em camadas — `core/` (funções puras de segurança), `infraestrutura/` (SQLite, banco
vetorial, Gemini), `aplicacao/` (regra de negócio, um módulo por área) e `api/` (rotas FastAPI,
finas). `main.py` virou só a "montagem" da aplicação. Nenhuma rota, método ou formato de
JSON mudou — o frontend não precisou de nenhuma alteração.

**Decisão consciente de não superengenheirar:** sem entidades de domínio separadas de
dict/Pydantic, sem interfaces de repositório (só existe SQLite e vai continuar existindo),
sem container de DI (o `Depends()` do FastAPI já resolve) e sem Prometheus/métricas — logs
estruturados + request ID + `/api/health` já dão a rastreabilidade pedida, sem a complexidade
de um exporter de métricas para um projeto deste porte. Também consideramos `structlog` para
o logging e optamos por `logging` da stdlib + um formatter JSON próprio (~40 linhas), para não
adicionar dependência nova.

**Bug real encontrado ao testar o rate limit de login:** a primeira versão comparava
`datetime.now(timezone.utc).isoformat()` (formato `2026-09-24T03:10:00+00:00`) com a coluna
`criado_em`, preenchida pelo `CURRENT_TIMESTAMP` do próprio SQLite (formato
`2026-09-24 03:10:00`, sem "T" nem fuso). Como SQLite compara TEXT lexicograficamente, e "T"
(0x54) vem depois do espaço (0x20) na tabela ASCII, a comparação dava sempre o resultado
errado: o rate limit nunca disparava (6 tentativas erradas seguidas continuavam voltando 401
em vez de 429) e a "limpeza" de tentativas antigas apagava tudo a cada tentativa nova.
*Lição:* nunca misturar timestamps formatados em Python com colunas preenchidas por
`CURRENT_TIMESTAMP` do SQLite nas mesmas comparações — ou tudo em Python, ou (mais simples
aqui) tudo com as funções de data do próprio SQLite (`datetime('now', '-15 minutes')`).
Só foi pego porque testamos o fluxo de verdade (6 logins errados seguidos) em vez de só
ler o código.

**Outro detalhe sutil (Starlette):** um handler registrado para `Exception` (usado aqui como
"pega-tudo" para erros não previstos) é instalado pelo Starlette no `ServerErrorMiddleware`,
que fica **fora** de qualquer middleware customizada (`add_middleware`) — não dentro dela.
A primeira versão da middleware de request-id fazia `contextvars.ContextVar.reset()` num
`finally`, o que apagava o id **antes** desse handler rodar, e o erro 500 saía com
`request_id: "-"`. Corrigido não resetando o ContextVar (cada requisição roda na sua própria
Task do asyncio, então não há risco de vazar entre requisições) e também gravando o
`X-Request-ID` diretamente na resposta desse handler específico.

**Verificação:** suíte de smoke tests com `TestClient` cobrindo login/cadastro, rate limit
(6 tentativas → 429), limite de tamanho de upload, disciplinas/documentos, chat, turma
(eventos/atividades/vídeos/mensagens), painel do professor, visão geral/lembretes e o
handler de erro não tratado — todas passando antes de considerar o refactor concluído.

---

## 16/10: evolução Fase 1 + LGPD + Fase 2

**Feito (branch `evolucao-fase1-lgpd-fase2`, um commit por pacote):** fábrica da aplicação e base de
testes; CI, lint e Docker; CSP sem `unsafe-inline` e checagem de origem; autorização por participação
na disciplina; pseudonimização (HMAC), retenção e backup; aviso de privacidade com ciência e
declaração de 18+; exportação e exclusão de conta; recuperação de senha e confirmação de e-mail;
simulado corrigido no servidor; métricas sem dado pessoal; indexação em segundo plano com OCR;
chat em streaming com citação que abre o PDF; defesa contra injeção de prompt e avaliação da IA;
cache e cotas de uso da IA; trilha até a prova com revisão espaçada; painel do professor v2;
documentação LGPD.

**Decisões:**
- **Público 18+:** os termos da API Gemini (vigentes desde 23/03/2026) exigem 18 anos e proíbem apps
  de acesso provável por menores. A trilha foi reorientada para universitários (prova, ENADE,
  transferência, segunda graduação) e a aba de universidades virou informativa.
- **Matrícula livre**, informada no aviso (colegas veem nome e mensagens no chat da turma).
- **Exclusão de professor:** disciplinas e materiais vão para a conta de sistema "Professor removido".

**Problemas encontrados:**
1. **Teste estrutural vazio:** no FastAPI 0.141 os routers incluídos viram `_IncludedRouter`, e o teste
   que deveria conferir a autorização de todas as rotas não via nenhuma (passava sem testar nada).
   Corrigido percorrendo a tupla `ROUTERS`. *Lição:* teste estrutural precisa conferir que verificou
   alguma coisa (`assert verificadas > 0`).
2. **Gemini 503 em todos os modelos ao mesmo tempo** durante a avaliação: a troca de modelo não basta
   quando o serviço todo está sobrecarregado. O script de avaliação espera e tenta de novo, e conta a
   indisponibilidade à parte (não é erro de qualidade).
3. **Pergunta mal formulada na avaliação:** "por que contadores precisam ser inicializados?" — o
   material só diz *quando*. O modelo respondeu "não encontrei", que é o comportamento certo; a
   pergunta foi corrigida. *Lição:* conjunto de avaliação também tem bug.
4. **SDK do Gemini registrava aviso de function calling a cada chamada:** desligado na configuração
   (o app não usa ferramentas).

**Verificação:** testes automatizados verdes (contagem no README), `ruff` limpo, imagem Docker
construída, navegação E2E no Chrome (Playwright) por todas as telas sem erro de CSP, fluxo real de
upload com barra de progresso e pergunta em streaming com o Gemini (o texto chegou em 4 etapas na
tela e as 8 citações abriram o PDF na página).