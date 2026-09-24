// Listas animadas do Suporte (perguntas frequentes e chamados): adaptação em JS puro do
// AnimatedList (React Bits), sem React nem Motion. Cada .lista-animada-rolagem vira uma área
// com rolagem própria em que:
//   - os itens surgem crescendo ao entrar na área visível (e somem ao sair);
//   - o topo e a base esmaecem quando há conteúdo escondido para aquele lado;
//   - o item sob o mouse fica selecionado, e as setas ↑ ↓ mudam a seleção.
// Diferente do original, as setas só agem com o foco dentro da lista e o Tab não é capturado.

const ITENS_LISTA_ANIMADA = ".item-faq, .chamado";

function criarListaAnimada(rolagem) {
  const caixa = rolagem.closest(".lista-animada");

  // Visível = pelo menos metade do item à mostra, ou metade da altura da área
  // (um chamado muito longo nunca mostraria metade de si mesmo)
  const observador = new IntersectionObserver((entradas) => {
    for (const e of entradas) {
      const metadeDaArea = e.rootBounds && e.intersectionRect.height >= e.rootBounds.height / 2;
      e.target.classList.toggle("visivel", e.intersectionRatio >= 0.5 || Boolean(metadeDaArea));
    }
  }, { root: rolagem, threshold: [0, 0.25, 0.5, 0.75, 1] });

  const itens = () => [...rolagem.querySelectorAll(ITENS_LISTA_ANIMADA)].filter((item) => !item.hidden);

  function observarItens() {
    for (const item of rolagem.querySelectorAll(ITENS_LISTA_ANIMADA)) {
      if (item.dataset.animado) continue;
      item.dataset.animado = "1";
      item.classList.add("item-animado");
      observador.observe(item);
    }
    atualizarEsmaecido();
  }

  function atualizarEsmaecido() {
    const { scrollTop, scrollHeight, clientHeight } = rolagem;
    const restante = scrollHeight - (scrollTop + clientHeight);
    caixa.style.setProperty("--esmaecer-topo", Math.min(scrollTop / 50, 1));
    caixa.style.setProperty("--esmaecer-base", scrollHeight <= clientHeight ? 0 : Math.min(restante / 50, 1));
  }

  function selecionar(item) {
    for (const outro of rolagem.querySelectorAll(".item-animado.selecionado")) {
      if (outro !== item) outro.classList.remove("selecionado");
    }
    item?.classList.add("selecionado");
  }

  rolagem.addEventListener("scroll", atualizarEsmaecido, { passive: true });
  rolagem.addEventListener("mouseover", (e) => selecionar(e.target.closest(ITENS_LISTA_ANIMADA)));
  rolagem.addEventListener("focusin", (e) => {
    const item = e.target.closest(ITENS_LISTA_ANIMADA);
    if (item) selecionar(item);
  });

  rolagem.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    if (e.target.matches("input, textarea, select")) return;  // não atrapalha quem está escrevendo
    const lista = itens();
    if (!lista.length) return;
    e.preventDefault();
    const atual = lista.findIndex((item) => item.classList.contains("selecionado"));
    const proximo = e.key === "ArrowDown"
      ? Math.min(atual + 1, lista.length - 1)
      : Math.max(atual - 1, 0);
    const item = lista[proximo];
    // Pergunta do FAQ: foca o <summary> (Enter abre e fecha). Chamado: foca o próprio cartão.
    let foco = item.querySelector("summary");
    if (!foco) {
      item.tabIndex = -1;
      foco = item;
    }
    foco.focus({ preventScroll: true });
    item.scrollIntoView({ block: "nearest", behavior: "smooth" });
    selecionar(item);
  });

  // A busca do FAQ esconde itens e os chamados são redesenhados: observa as mudanças
  new MutationObserver(observarItens).observe(rolagem, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "open"] });
  new ResizeObserver(atualizarEsmaecido).observe(rolagem);
  observarItens();
}

for (const rolagem of document.querySelectorAll(".lista-animada-rolagem")) criarListaAnimada(rolagem);
