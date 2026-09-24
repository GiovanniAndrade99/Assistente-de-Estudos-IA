// Adaptação em CSS/JS puro do OriginButton, sem dependência de React.
const EXCLUIR_ORIGEM = ".botao-icone, .link-perigo, .remover, .dia, .horario, .conta";

function prepararBotaoOrigem(botao) {
  if (botao.classList.contains("botao-origem") || botao.matches(EXCLUIR_ORIGEM) || botao.closest(".menu")) return;
  botao.classList.add("botao-origem");
  const conteudo = document.createElement("span");
  conteudo.className = "conteudo-botao-origem";
  while (botao.firstChild) conteudo.appendChild(botao.firstChild);
  botao.appendChild(conteudo);

  botao.addEventListener("pointermove", (evento) => definirOrigem(botao, evento.clientX, evento.clientY));
  botao.addEventListener("pointerdown", (evento) => {
    if (evento.button !== 0) return;
    definirOrigem(botao, evento.clientX, evento.clientY);
    botao.dataset.pressionado = "true";
  });
  for (const tipo of ["pointerup", "pointercancel", "pointerleave", "blur"]) {
    botao.addEventListener(tipo, () => { delete botao.dataset.pressionado; });
  }
  botao.addEventListener("focus", () => {
    if (!botao.matches(":focus-visible")) return;
    const caixa = botao.getBoundingClientRect();
    definirOrigem(botao, caixa.left + caixa.width / 2, caixa.top + caixa.height / 2);
  });
}

function definirOrigem(botao, x, y) {
  const caixa = botao.getBoundingClientRect();
  const localX = x - caixa.left;
  const localY = y - caixa.top;
  const diametro = 2 * Math.max(
    Math.hypot(localX, localY), Math.hypot(caixa.width - localX, localY),
    Math.hypot(localX, caixa.height - localY), Math.hypot(caixa.width - localX, caixa.height - localY),
  );
  botao.style.setProperty("--origem-x", `${localX}px`);
  botao.style.setProperty("--origem-y", `${localY}px`);
  botao.style.setProperty("--origem-diametro", `${Math.ceil(diametro)}px`);
}

for (const botao of document.querySelectorAll("button")) prepararBotaoOrigem(botao);
new MutationObserver((mutacoes) => {
  for (const mutacao of mutacoes) {
    for (const no of mutacao.addedNodes) {
      if (no.nodeType !== Node.ELEMENT_NODE) continue;
      if (no.matches("button")) prepararBotaoOrigem(no);
      for (const botao of no.querySelectorAll("button")) prepararBotaoOrigem(botao);
    }
  }
}).observe(document.body, { childList: true, subtree: true });
