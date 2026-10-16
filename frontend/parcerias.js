// Tela "Universidades e vestibulares": cursos de TI de universidades conhecidas, nota do MEC
// (CPC) e datas de inscrição. Informativo: os dados e as fontes vêm de
// backend/dados/universidades.json (GET /api/universidades).

let UNIVERSIDADES = [];
let fontesUniversidades = null;

const FILTROS_INGRESSO = ["Todos", "SiSU", "Vestibular próprio"];
let filtroIngresso = "Todos";
let filtroRegiao = "Todas";
let textoBusca = "";

const REGIAO_POR_UF = { MG: "Sudeste", SP: "Sudeste", RJ: "Sudeste", ES: "Sudeste", CE: "Nordeste", RN: "Nordeste",
  PE: "Nordeste", BA: "Nordeste", RS: "Sul", SC: "Sul", PR: "Sul", DF: "Centro-Oeste", GO: "Centro-Oeste", AM: "Norte", PA: "Norte" };
const REGIOES = ["Todas", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"];

function semAcento(t) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function diasAte(iso) {
  const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
  return Math.round((dataLocal(iso) - hoje) / 86400000);
}

function textoDias(n) {
  return n === 0 ? "termina hoje" : n === 1 ? "falta 1 dia" : `faltam ${n} dias`;
}

function dataLocal(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d);
}

function formatarPeriodo(i) {
  const f = (iso) => dataLocal(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  return i.fim && i.fim !== i.inicio ? `${f(i.inicio)} a ${f(i.fim)}` : f(i.inicio);
}

function situacao(i) {
  const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
  const fim = dataLocal(i.fim || i.inicio);
  if (i.previsto && dataLocal(i.inicio) > hoje) return ["Previsto", "laranja"];
  if (fim < hoje) return ["Encerrado", "vermelha"];
  if (dataLocal(i.inicio) <= hoje) return [`Aberto · ${textoDias(diasAte(i.fim || i.inicio))}`, "verde"];
  return [`Em ${diasAte(i.inicio)} dias`, "azul"];
}

function medidorCpc(u) {
  if (u.cpc == null) {
    return `<div class="cpc sem-cpc"><span class="cpc-valor">—</span><span class="cpc-rotulo">Sem CPC divulgado</span></div>`;
  }
  const cor = u.faixa >= 5 ? "verde" : "azul";
  return `
    <div class="cpc">
      <div class="cpc-topo">
        <span class="cpc-valor">${u.cpc.toFixed(2)}</span>
        <span class="etiqueta ${cor}">Faixa ${u.faixa}/5</span>
      </div>
      <div class="cpc-barra" role="img" aria-label="CPC ${u.cpc.toFixed(2)} de 5"><i data-largura="${(u.cpc / 5) * 100}"></i></div>
      <span class="cpc-rotulo">CPC contínuo · nota do curso no MEC</span>
    </div>`;
}

function cartao(u, indice) {
  const linhas = u.inscricoes.map((i) => {
    const [texto, cor] = situacao(i);
    return `<li><span class="insc-rotulo">${escaparHtml(i.rotulo)}</span>
      <span class="insc-data">${formatarPeriodo(i)}</span>
      <span class="etiqueta ${cor}">${texto}</span></li>`;
  }).join("");
  return `
    <article class="cartao-parceria glare${u.faixa >= 5 ? " destaque-top" : ""}" data-atraso="${indice * 70}ms">
      ${u.faixa >= 5 ? `<span class="selo-top">🏆 Top MEC</span>` : ""}
      <header class="parceria-topo">
        <span class="sigla-uni">${escaparHtml(u.sigla)}</span>
        <div>
          <h3>${escaparHtml(u.nome)}</h3>
          <p class="local">📍 ${escaparHtml(u.cidade)} · ${escaparHtml(u.uf)} · ${REGIAO_POR_UF[u.uf]}</p>
        </div>
      </header>
      <p class="curso-ti"><span>Curso de TI</span><strong>${escaparHtml(u.curso)}</strong></p>
      ${medidorCpc(u)}
      <div class="bloco-inscricoes">
        <h4>Inscrições <small>· ${escaparHtml(u.ingresso)}</small></h4>
        <ul class="inscricoes">${linhas}</ul>
        <p class="dica">${escaparHtml(u.sobre)}</p>
      </div>
      <a class="link-externo-parceria" href="${escaparHtml(u.site)}" target="_blank" rel="noopener noreferrer">Site oficial ↗</a>
    </article>`;
}

function desenharParcerias() {
  const busca = semAcento(textoBusca.trim());
  const visiveis = UNIVERSIDADES
    .filter((u) => filtroIngresso === "Todos" || u.ingresso.includes(filtroIngresso))
    .filter((u) => filtroRegiao === "Todas" || REGIAO_POR_UF[u.uf] === filtroRegiao)
    .filter((u) => !busca || semAcento(`${u.nome} ${u.sigla} ${u.cidade} ${u.curso}`).includes(busca))
    .sort((a, b) => (b.cpc ?? -1) - (a.cpc ?? -1));
  $("lista-parcerias").innerHTML = visiveis.length
    ? visiveis.map(cartao).join("")
    : `<p class="dica sem-resultado">Nenhuma universidade encontrada com esses filtros.</p>`;
  for (const botao of $("filtros-parcerias").children) {
    botao.classList.toggle("ativo", botao.dataset.filtro === filtroIngresso);
  }
}

// Próxima inscrição: a que está aberta e termina primeiro; se nenhuma, a que abre primeiro.
function desenharDestaque() {
  const todas = UNIVERSIDADES.flatMap((u) => u.inscricoes.filter((i) => !i.previsto && /inscri/i.test(i.rotulo))
    .map((i) => ({ u, i })));
  const abertas = todas.filter(({ i }) => diasAte(i.inicio) <= 0 && diasAte(i.fim || i.inicio) >= 0)
    .sort((a, b) => diasAte(a.i.fim) - diasAte(b.i.fim));
  const proximas = todas.filter(({ i }) => diasAte(i.inicio) > 0).sort((a, b) => diasAte(a.i.inicio) - diasAte(b.i.inicio));
  const alvo = abertas[0] || proximas[0];
  const caixa = $("destaque-inscricao");
  if (!alvo) { caixa.hidden = true; return; }
  const aberta = alvo === abertas[0];
  caixa.hidden = false;
  caixa.classList.toggle("aberta", aberta);
  caixa.innerHTML = `
    <span class="destaque-icone">${aberta ? "🔥" : "⏳"}</span>
    <div>
      <strong>${aberta ? "Inscrição aberta agora" : "Próxima inscrição"}: ${escaparHtml(alvo.u.sigla)} · ${escaparHtml(alvo.i.rotulo)}</strong>
      <span>${formatarPeriodo(alvo.i)}</span>
    </div>
    <span class="destaque-dias">${aberta ? textoDias(diasAte(alvo.i.fim || alvo.i.inicio)) : `em ${diasAte(alvo.i.inicio)} dias`}</span>`;
}

TELAS.parcerias = {
  async abrir() {
    if (!fontesUniversidades) {
      try {
        const dados = await chamarApi("/api/universidades");
        UNIVERSIDADES = dados.universidades;
        fontesUniversidades = dados;
      } catch (erro) {
        $("lista-parcerias").innerHTML = `<p class="erro">${escaparHtml(erro.message)}</p>`;
        return;
      }
      $("fontes-universidades").textContent =
        `Fontes (atualizado em ${new Date(`${fontesUniversidades.atualizado_em}T00:00:00`).toLocaleDateString("pt-BR")}): `
        + fontesUniversidades.fontes.join("; ") + ".";
    }
    if (!$("filtros-parcerias").childElementCount) {
      const comCpc = UNIVERSIDADES.filter((u) => u.cpc != null);
      const melhor = comCpc.reduce((a, b) => (b.cpc > a.cpc ? b : a));
      $("resumo-parcerias").innerHTML = `
        <div class="stat glare"><strong>${UNIVERSIDADES.length}</strong><span>universidades</span></div>
        <div class="stat glare"><strong>${new Set(UNIVERSIDADES.map((u) => u.uf)).size}</strong><span>estados</span></div>
        <div class="stat glare"><strong>${melhor.cpc.toFixed(2)}</strong><span>maior CPC (${escaparHtml(melhor.sigla)})</span></div>`;
      $("filtros-parcerias").innerHTML = FILTROS_INGRESSO
        .map((f) => `<button type="button" class="chip" data-filtro="${f}">${f}</button>`).join("");
      $("filtros-parcerias").onclick = (e) => {
        const botao = e.target.closest("[data-filtro]");
        if (!botao) return;
        filtroIngresso = botao.dataset.filtro;
        desenharParcerias();
      };
    }
    if (!$("regiao-parcerias").childElementCount) {
      $("regiao-parcerias").innerHTML = REGIOES
        .map((r) => `<option value="${r}">${r === "Todas" ? "Todas as regiões" : r}</option>`).join("");
      $("regiao-parcerias").onchange = (e) => { filtroRegiao = e.target.value; desenharParcerias(); };
      $("busca-parcerias").oninput = (e) => { textoBusca = e.target.value; desenharParcerias(); };
    }
    desenharDestaque();
    desenharParcerias();
  },
};
