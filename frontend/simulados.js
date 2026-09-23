// Tela "Simulados": gera um simulado a partir de um PDF e mostra o histórico de notas.
// Reaproveita renderSimulado() do app.js (a correção já salva a nota no servidor).

TELAS.simulados = {
  async abrir() {
    if (!disciplinaAtual) return;
    $("simulado-area").innerHTML = "";
    const docs = await chamarApi(rotaDisciplina("/documentos"));
    const select = $("simulado-arquivo");
    select.innerHTML = docs.length
      ? docs.map((d) => `<option value="${escaparHtml(d.arquivo)}">${escaparHtml(d.arquivo)}</option>`).join("")
      : `<option value="">Envie um PDF no Assistente IA primeiro</option>`;
    $("form-simulado").querySelector("button").disabled = !docs.length;
    carregarHistoricoSimulados();
  },
};

$("form-simulado").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const arquivo = $("simulado-arquivo").value;
  if (!arquivo) return;
  const botao = evento.target.querySelector("button");
  const area = $("simulado-area");
  botao.disabled = true;
  area.innerHTML = `<div class="bloco carregando">Gerando simulado... (pode levar alguns segundos)</div>`;

  try {
    const r = await postarJson(rotaDisciplina("/simulado"), {
      arquivo, quantidade: Number($("simulado-quantidade").value),
    });
    const caixa = document.createElement("div");
    caixa.className = "bloco rica";
    if (r.aviso) caixa.innerHTML = `<p class="aviso">⚠️ ${escaparHtml(r.aviso)}</p>`;
    renderSimulado(caixa, r);
    caixa.insertAdjacentHTML("beforeend", rodapeModelo(r.modelo));
    area.replaceChildren(caixa);
  } catch (erro) {
    area.innerHTML = `<p class="erro">${escaparHtml(erro.message)}</p>`;
  } finally {
    botao.disabled = false;
  }
});

async function carregarHistoricoSimulados() {
  const historico = $("simulado-historico");
  const linhas = await chamarApi(rotaDisciplina("/simulado/meus"));
  if (!linhas.length) {
    historico.innerHTML = "<p class='dica'>Você ainda não fez simulados nesta disciplina.</p>";
    return;
  }
  const media = Math.round((100 * linhas.reduce((s, l) => s + l.acertos, 0)) / linhas.reduce((s, l) => s + l.total, 0));
  historico.innerHTML = `
    <p class="dica">${linhas.length} simulado(s) · acerto médio de <strong>${media}%</strong></p>
    <table class="tabela"><thead><tr><th>Material</th><th>Nota</th><th>Acerto</th><th>Data</th></tr></thead><tbody>
    ${linhas.map((l) => {
      const pct = Math.round((100 * l.acertos) / l.total);
      return `<tr><td>${escaparHtml(l.arquivo)}</td><td>${l.acertos}/${l.total}</td>
        <td><div class="barra"><div style="width:${pct}%"></div></div> ${pct}%</td>
        <td>${formatarData(l.criado_em)}</td></tr>`;
    }).join("")}
    </tbody></table>`;
}
