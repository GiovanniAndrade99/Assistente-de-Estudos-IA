// Tela "Minhas disciplinas": busca, filtros e um cartão por disciplina com o
// progresso nas aulas (PDFs marcados como estudados) e as atividades.

let visaoGeral = [];                // [{id, nome, aulas: [{id, arquivo, concluida}], atividades: [...]}]
let filtroDisciplinas = "todas";
const cartoesAbertos = new Set();   // disciplinas com a lista de aulas expandida

TELAS.disciplinas = {
  async abrir() {
    const grade = $("grade-disciplinas");
    if (!visaoGeral.length) grade.innerHTML = `<p class="dica carregando-grade">Carregando disciplinas...</p>`;
    visaoGeral = await chamarApi("/api/visao-geral");
    desenharDisciplinas();
  },
};

// Sem acento e em minúsculas: "Cálculo" e "calculo" batem na busca
const normalizar = (texto) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const nomeDaAula = (arquivo) => arquivo.replace(/\.pdf$/i, "");

function progresso(d) {
  const feitas = d.aulas.filter((a) => a.concluida).length;
  const total = d.aulas.length;
  return { feitas, total, pct: total ? Math.round((100 * feitas) / total) : 0 };
}

// Atividade que o aluno ainda precisa entregar (para o professor, nenhuma conta como pendente)
const pendente = (a) => usuario.tipo === "aluno" && !a.entregue_em;

function passaNoFiltro(d) {
  const { pct, total } = progresso(d);
  if (filtroDisciplinas === "andamento") return pct > 0 && pct < 100;
  if (filtroDisciplinas === "pendencias") return d.atividades.some(pendente);
  if (filtroDisciplinas === "concluidas") return total > 0 && pct === 100;
  return true;
}

// Diz se a disciplina casa com a busca e se o que casou foi uma aula (para abrir a lista)
function casaComBusca(d, termo) {
  if (!termo) return { casa: true, porAula: false };
  if (normalizar(d.nome).includes(termo)) return { casa: true, porAula: false };
  const porAula = d.aulas.some((a) => normalizar(a.arquivo).includes(termo));
  const porAtividade = d.atividades.some((a) => normalizar(a.titulo).includes(termo));
  return { casa: porAula || porAtividade, porAula };
}

function desenharResumo() {
  const aulas = visaoGeral.flatMap((d) => d.aulas);
  const feitas = aulas.filter((a) => a.concluida).length;
  const atividades = visaoGeral.flatMap((d) => d.atividades);
  const quarto = usuario.tipo === "aluno"
    ? { valor: atividades.filter(pendente).length, rotulo: "atividades pendentes" }
    : { valor: atividades.reduce((s, a) => s + a.total_entregas, 0), rotulo: "entregas recebidas" };
  const itens = [
    { valor: visaoGeral.length, rotulo: "disciplinas" },
    { valor: `${feitas}<small>/${aulas.length}</small>`, rotulo: "aulas estudadas" },
    { valor: `${aulas.length ? Math.round((100 * feitas) / aulas.length) : 0}%`, rotulo: "progresso geral" },
    quarto,
  ];
  $("resumo-geral").innerHTML = itens
    .map((i) => `<div class="estatistica"><strong>${i.valor}</strong><span>${i.rotulo}</span></div>`).join("");
}

function desenharDisciplinas() {
  desenharResumo();
  const termo = normalizar($("busca-disciplinas").value.trim());
  const grade = $("grade-disciplinas");
  const visiveis = [];
  for (const d of visaoGeral) {
    const { casa, porAula } = casaComBusca(d, termo);
    if (casa && passaNoFiltro(d)) visiveis.push({ d, abrirAulas: porAula });
  }

  $("contagem-busca").textContent = termo || filtroDisciplinas !== "todas"
    ? `${visiveis.length} de ${visaoGeral.length} disciplinas`
    : "";

  if (!visaoGeral.length) {
    grade.innerHTML = `<p class="dica">Nenhuma disciplina cadastrada ainda. Crie uma no botão <strong>+</strong> da barra lateral.</p>`;
    return;
  }
  if (!visiveis.length) {
    grade.innerHTML = `<p class="dica">Nenhuma disciplina encontrada${termo ? ` para "<strong>${escaparHtml($("busca-disciplinas").value.trim())}</strong>"` : ""}.</p>`;
    return;
  }
  grade.innerHTML = "";
  for (const { d, abrirAulas } of visiveis) grade.appendChild(cartaoDisciplina(d, abrirAulas || cartoesAbertos.has(d.id)));
}

function iniciais(nome) {
  const palavras = nome.split(/\s+/).filter((p) => p.length > 2 || /^[A-Z]/.test(p));
  if (!palavras.length) return nome.slice(0, 2).toUpperCase();
  return (palavras[0][0] + (palavras[1]?.[0] || "")).toUpperCase();
}

function cartaoDisciplina(d, aulasAbertas) {
  const { feitas, total, pct } = progresso(d);
  const pendentes = d.atividades.filter(pendente).length;
  const cartao = document.createElement("article");
  cartao.className = `cartao-disciplina${d.id === disciplinaAtual?.id ? " atual" : ""}`;
  cartao.innerHTML = `
    <header class="disciplina-topo">
      <span class="disciplina-sigla" aria-hidden="true">${escaparHtml(iniciais(d.nome))}</span>
      <div class="disciplina-titulo">
        <h3>${escaparHtml(d.nome)}</h3>
        <p>${total} aula${total === 1 ? "" : "s"} · ${d.atividades.length} atividade${d.atividades.length === 1 ? "" : "s"}${
          pendentes ? ` · <span class="texto-pendente">${pendentes} pendente${pendentes === 1 ? "" : "s"}</span>` : ""}</p>
      </div>
      <button type="button" class="botao-icone abrir-disciplina" title="Abrir no Assistente IA"
        aria-label="Abrir ${escaparHtml(d.nome)}"><svg><use href="#i-seta-dir"/></svg></button>
    </header>

    <div class="progresso" role="group" aria-label="Progresso nas aulas">
      <div class="progresso-topo">
        <span>Progresso nas aulas</span>
        <strong>${pct}%</strong>
      </div>
      <div class="barra-progresso${pct === 100 ? " completa" : ""}" role="progressbar"
        aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div style="width:${pct}%"></div></div>
      <small>${total ? `${feitas} de ${total} aulas estudadas${pct === 100 ? " · concluída 🎉" : ""}` : "Nenhuma aula enviada ainda"}</small>
    </div>

    ${total ? `
    <details class="lista-aulas" ${aulasAbertas ? "open" : ""}>
      <summary>Aulas <span class="dica">(marque as que já estudou)</span></summary>
      <ul>${d.aulas.map((a) => `
        <li><label class="${a.concluida ? "feita" : ""}">
          <input type="checkbox" data-aula="${a.id}" ${a.concluida ? "checked" : ""}>
          <span>${escaparHtml(nomeDaAula(a.arquivo))}</span>
        </label></li>`).join("")}
      </ul>
    </details>` : ""}

    <div class="atividades-disciplina">
      <h4>Atividades</h4>
      ${d.atividades.length ? `<ul>${d.atividades.map((a) => `
        <li><button type="button" class="linha-atividade" data-ir="atividades">
          <span class="linha-atividade-texto">
            <strong>${escaparHtml(a.titulo)}</strong>
            <small>Prazo ${formatarDia(a.prazo)}${usuario.tipo === "professor" ? ` · ${a.total_entregas} entrega(s)` : ""}</small>
          </span>
          ${situacaoDaAtividade(a)}
        </button></li>`).join("")}</ul>`
        : `<p class="dica">Nenhuma atividade publicada.</p>`}
    </div>`;

  // Abrir a disciplina (no Assistente IA) ou ir direto para as atividades dela
  const irPara = (tela) => {
    selectDisciplina.value = d.id;
    selecionarDisciplina(disciplinas.find((x) => x.id === d.id));
    mostrarTela(tela);
  };
  cartao.querySelector(".abrir-disciplina").onclick = () => irPara("assistente");
  for (const botao of cartao.querySelectorAll(".linha-atividade")) botao.onclick = () => irPara("atividades");

  const detalhes = cartao.querySelector(".lista-aulas");
  if (detalhes) detalhes.ontoggle = () => {
    if (detalhes.open) cartoesAbertos.add(d.id);
    else cartoesAbertos.delete(d.id);
  };
  for (const caixa of cartao.querySelectorAll("input[data-aula]")) {
    caixa.onchange = () => marcarAula(d, Number(caixa.dataset.aula), caixa.checked, caixa);
  }
  return cartao;
}

async function marcarAula(d, aulaId, concluida, caixa) {
  const aula = d.aulas.find((a) => a.id === aulaId);
  aula.concluida = concluida;  // atualiza na hora; se o servidor falhar, desfaz
  cartoesAbertos.add(d.id);
  desenharDisciplinas();
  try {
    await chamarApi(`/api/aulas/${aulaId}/concluida`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ concluida }),
    });
    if (d.id === disciplinaAtual?.id) carregarDocumentos();  // mantém a barra lateral em sincronia
  } catch (erro) {
    aula.concluida = !concluida;
    desenharDisciplinas();
    alert(erro.message);
  }
}

// ---------------------------------------------------------- busca e filtros

$("busca-disciplinas").addEventListener("input", desenharDisciplinas);

for (const botao of document.querySelectorAll(".filtro")) {
  botao.onclick = () => {
    filtroDisciplinas = botao.dataset.filtro;
    document.querySelectorAll(".filtro").forEach((b) => b.classList.toggle("ativo", b === botao));
    desenharDisciplinas();
  };
}

// Atalho "/" para buscar (fora de campos de texto); Esc limpa a busca
document.addEventListener("keydown", (e) => {
  const busca = $("busca-disciplinas");
  const digitando = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  if (e.key === "/" && !digitando && telaAtual === "disciplinas") {
    e.preventDefault();
    busca.focus();
  } else if (e.key === "Escape" && document.activeElement === busca && busca.value) {
    busca.value = "";
    desenharDisciplinas();
  }
});
