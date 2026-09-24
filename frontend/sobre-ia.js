// Tela "Sobre o assistente IA": identifica a IA e mostra os modelos e parâmetros em uso.

let sobreIa = null;  // carregado uma vez: só muda se o servidor for reiniciado com outro .env

// Revelação ao rolar: cada bloco surge (fade + leve subida) quando entra na tela.
// Os que entram juntos aparecem em sequência, 90 ms um depois do outro.
const telaSobreIa = $("tela-sobre-ia");
const BLOCOS_REVELAR = [
  ".cabecalho-pagina", ".identificacao-ia", ".titulo-secao", ".passos-ia > li", ".passos-ia + .dica",
  ".tabela-rolavel thead tr", ".tabela-rolavel tbody tr", ".colunas-ia > .cartao-form",
].map((s) => `#tela-sobre-ia ${s}`).join(", ");
const revelarAoRolar = !matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window;

let blocosRevelar = [];  // em ordem de cima para baixo

const observadorRevelar = revelarAoRolar && new IntersectionObserver((entradas) => {
  const chegando = new Set(entradas.filter((e) => e.isIntersecting).map((e) => e.target));
  if (!chegando.size) return;
  // Também revela os blocos anteriores ainda escondidos: quem pula direto para o fim
  // (tecla End, arrastar a barra) não deixa buracos invisíveis no meio da página
  const ultimo = Math.max(...[...chegando].map((b) => blocosRevelar.indexOf(b)));
  let ordem = 0;
  blocosRevelar.slice(0, ultimo + 1).forEach((bloco) => {
    if (bloco.classList.contains("revelado")) return;
    bloco.style.setProperty("--atraso-revelar", chegando.has(bloco) ? `${ordem++ * 90}ms` : "0ms");
    bloco.classList.add("revelado");
    observadorRevelar.unobserve(bloco);
  });
}, { root: telaSobreIa, threshold: 0.15, rootMargin: "0px 0px -8% 0px" });

// Chamado a cada abertura da aba: esconde tudo de novo e volta ao topo, para a página
// "carregar aos poucos" sempre que for aberta
function prepararRevelacao() {
  if (!observadorRevelar) return;
  telaSobreIa.scrollTop = 0;
  blocosRevelar = [...document.querySelectorAll(BLOCOS_REVELAR)];
  for (const bloco of blocosRevelar) {
    bloco.classList.add("revelar");
    bloco.classList.remove("revelado");
    observadorRevelar.observe(bloco);
  }
}

TELAS["sobre-ia"] = {
  async abrir() {
    prepararRevelacao();
    if (sobreIa) return;
    try {
      sobreIa = await chamarApi("/api/ia/sobre");
    } catch (erro) {
      $("ficha-ia").innerHTML = `<div><dt>Modelo</dt><dd class="erro">${escaparHtml(erro.message)}</dd></div>`;
      return;
    }
    const itens = [
      ["Provedor", sobreIa.provedor],
      ["Modelo principal", sobreIa.modelo],
      ["Modelos reserva", sobreIa.modelos_reserva.join(", ") || "nenhum"],
      ["Modelo de embeddings", sobreIa.modelo_embeddings],
      ["Tamanho do trecho", `${sobreIa.tamanho_trecho} caracteres (${sobreIa.sobreposicao} de sobreposição)`],
      ["Trechos por pergunta", sobreIa.top_k],
    ];
    $("ficha-ia").innerHTML = itens
      .map(([rotulo, valor]) => `<div class="glare"><dt>${rotulo}</dt><dd>${escaparHtml(valor)}</dd></div>`)
      .join("");
    for (const el of document.querySelectorAll("#tela-sobre-ia [data-ia]")) {
      el.textContent = sobreIa[el.dataset.ia];
    }
  },
};
