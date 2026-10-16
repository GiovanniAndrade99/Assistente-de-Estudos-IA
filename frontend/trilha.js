// Tela "Trilha até a prova": plano semanal até a data-alvo e revisão espaçada do baralho.
// O plano vem pronto do servidor (regras fixas, sem IA) e é recalculado a cada visita.

let dadosTrilha = null;
let filaRevisao = [];

TELAS.trilha = {
  abrir() {
    if (disciplinaAtual) carregarTrilha();
  },
};

async function carregarTrilha() {
  $("trilha-revisao").hidden = true;
  try {
    dadosTrilha = await chamarApi(rotaDisciplina("/trilha"));
  } catch (erro) {
    $("trilha-resumo").innerHTML = `<p class="erro">${escaparHtml(erro.message)}</p>`;
    return;
  }
  desenharTrilha();
}

function dataCurta(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function desenharTrilha() {
  const { trilha, plano, objetivos, baralho } = dadosTrilha;
  const cartoes = baralho.para_hoje
    ? `<button type="button" class="botao-primario" id="revisar-cartoes">Revisar ${baralho.para_hoje} cartão(ões) de hoje</button>`
    : `<span class="dica">${baralho.total ? "Nenhum cartão para revisar hoje." : "Seu baralho está vazio: salve flashcards no Assistente IA."}</span>`;

  if (!trilha) {
    $("trilha-resumo").innerHTML = `
      <div class="bloco"><p>Você ainda não tem uma trilha nesta disciplina. Escolha o objetivo e a data, e o plano
        distribui as aulas que faltam pelas semanas até lá.</p>
        <div class="linha-botoes">${cartoes}</div></div>`;
    $("trilha-plano").innerHTML = "";
    abrirFormTrilha(false);
  } else {
    const dias = plano.dias_restantes;
    $("trilha-resumo").innerHTML = `
      <div class="bloco resumo-trilha">
        <div class="contagem"><strong>${dias}</strong><span>${dias === 1 ? "dia" : "dias"} até ${escaparHtml(objetivos[trilha.objetivo])}
          (${new Date(`${trilha.data_alvo}T00:00:00`).toLocaleDateString("pt-BR")})</span></div>
        <div class="contagem"><strong>${plano.aulas_total - plano.aulas_pendentes}/${plano.aulas_total}</strong><span>aulas estudadas</span></div>
        <div class="contagem"><strong>${baralho.total}</strong><span>cartões no baralho</span></div>
        <div class="linha-botoes">${cartoes}
          <button type="button" class="botao-secundario" id="editar-trilha">Editar trilha</button>
          <button type="button" class="botao-secundario" id="apagar-trilha">Apagar trilha</button>
        </div>
      </div>`;
    $("form-trilha").hidden = true;
    desenharPlano(plano);
    $("editar-trilha").onclick = () => abrirFormTrilha(true);
    $("apagar-trilha").onclick = apagarTrilha;
  }
  const botaoRevisar = $("revisar-cartoes");
  if (botaoRevisar) botaoRevisar.onclick = iniciarRevisao;
}

function desenharPlano(plano) {
  $("trilha-plano").innerHTML = plano.semanas.map((s, i) => `
    <article class="semana-trilha${i === 0 ? " atual" : ""}${s.revisao_final ? " final" : ""}">
      <header>
        <h3>${i === 0 ? "Esta semana" : `Semana ${s.numero}`}${s.revisao_final ? " · revisão final" : ""}</h3>
        <span class="dica">${dataCurta(s.inicio)} a ${dataCurta(s.fim)} · ${s.horas} h</span>
      </header>
      <ul>${s.tarefas.map((t) => `<li class="tarefa-${t.tipo}">${escaparHtml(t.texto)}</li>`).join("")}</ul>
    </article>`).join("");
}

function abrirFormTrilha(editando) {
  const form = $("form-trilha");
  const { objetivos, trilha, datas_da_turma: datas } = dadosTrilha;
  $("trilha-objetivo").replaceChildren(...Object.entries(objetivos).map(([valor, rotulo]) => new Option(rotulo, valor)));
  const hoje = new Date();
  const minimo = new Date(hoje.getTime() - hoje.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  $("trilha-data").min = minimo;
  if (trilha) {
    $("trilha-objetivo").value = trilha.objetivo;
    $("trilha-data").value = trilha.data_alvo;
    $("trilha-horas").value = trilha.horas_semana;
  }
  $("titulo-form-trilha").textContent = editando ? "Editar trilha" : "Montar minha trilha";
  $("cancelar-trilha").hidden = !editando;
  $("trilha-sugestoes").innerHTML = datas.length
    ? `<span class="dica">Datas da turma:</span>` + datas.map((d) =>
      `<button type="button" class="chip" data-data="${escaparHtml(d.data)}">${escaparHtml(d.titulo)} · ${dataCurta(d.data)}</button>`).join("")
    : "";
  form.querySelector(".status").textContent = "";
  form.hidden = false;
}

$("trilha-sugestoes").addEventListener("click", (evento) => {
  const botao = evento.target.closest("[data-data]");
  if (!botao) return;
  $("trilha-data").value = botao.dataset.data;
  if (/prova/i.test(botao.textContent)) $("trilha-objetivo").value = "prova";
});

$("cancelar-trilha").onclick = () => { $("form-trilha").hidden = true; };

$("form-trilha").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  try {
    dadosTrilha = await chamarApi(rotaDisciplina("/trilha"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        objetivo: $("trilha-objetivo").value,
        data_alvo: $("trilha-data").value,
        horas_semana: Number($("trilha-horas").value),
      }),
    });
    desenharTrilha();
  } catch (erro) {
    form.querySelector(".status").textContent = `✖ ${erro.message}`;
  }
});

async function apagarTrilha() {
  if (!confirm("Apagar a trilha desta disciplina? Seu baralho de flashcards continua.")) return;
  await chamarApi(rotaDisciplina("/trilha"), { method: "DELETE" });
  carregarTrilha();
}

// ---------------------------------------------------------- revisão espaçada

const NOTAS_REVISAO = [
  { nota: 1, rotulo: "Errei", classe: "vermelha" },
  { nota: 3, rotulo: "Difícil", classe: "laranja" },
  { nota: 4, rotulo: "Bom", classe: "azul" },
  { nota: 5, rotulo: "Fácil", classe: "verde" },
];

async function iniciarRevisao() {
  const { cartoes } = await chamarApi(rotaDisciplina("/baralho/hoje"));
  filaRevisao = cartoes;
  $("trilha-revisao").hidden = false;
  mostrarCartao();
  $("trilha-revisao").scrollIntoView({ behavior: "smooth", block: "start" });
}

function mostrarCartao() {
  const caixa = $("trilha-revisao");
  const cartao = filaRevisao[0];
  if (!cartao) {
    caixa.innerHTML = `<p>✔ Revisão do dia concluída. Os cartões voltam nos dias certos.</p>
      <button type="button" class="botao-secundario" id="fechar-revisao">Fechar</button>`;
    $("fechar-revisao").onclick = carregarTrilha;
    return;
  }
  const origem = cartao.arquivo ? `${escaparHtml(cartao.arquivo)}${cartao.pagina ? `, p. ${cartao.pagina}` : ""}` : "";
  caixa.innerHTML = `
    <p class="dica">Faltam ${filaRevisao.length} · ${origem}</p>
    <div class="cartao-revisao">
      <p class="frente">${escaparHtml(cartao.frente)}</p>
      <p class="verso" hidden>${escaparHtml(cartao.verso)}</p>
    </div>
    <div class="linha-botoes">
      <button type="button" class="botao-primario" id="mostrar-verso">Mostrar resposta</button>
      <span class="botoes-nota" hidden>${NOTAS_REVISAO.map((n) =>
        `<button type="button" class="botao-secundario nota-${n.classe}" data-nota="${n.nota}">${n.rotulo}</button>`).join("")}</span>
      <button type="button" class="link-ia" id="remover-cartao">Remover do baralho</button>
    </div>`;
  $("mostrar-verso").onclick = () => {
    caixa.querySelector(".verso").hidden = false;
    caixa.querySelector(".botoes-nota").hidden = false;
    $("mostrar-verso").hidden = true;
  };
  caixa.querySelector(".botoes-nota").onclick = async (evento) => {
    const botao = evento.target.closest("[data-nota]");
    if (!botao) return;
    await postarJson(`/api/baralho/${cartao.id}/revisao`, { nota: Number(botao.dataset.nota) });
    filaRevisao.shift();
    if (Number(botao.dataset.nota) < 3) filaRevisao.push(cartao);  // errou: volta ainda nesta sessão
    mostrarCartao();
  };
  $("remover-cartao").onclick = async () => {
    if (!confirm("Remover este cartão do seu baralho?")) return;
    await chamarApi(`/api/baralho/${cartao.id}`, { method: "DELETE" });
    filaRevisao.shift();
    mostrarCartao();
  };
}

// Botão "Salvar no meu baralho" dos flashcards gerados (app.js → renderFlashcards)
async function salvarNoBaralho(arquivo, cartoes, botao) {
  botao.disabled = true;
  try {
    const r = await postarJson(rotaDisciplina("/baralho"), {
      arquivo,
      cartoes: cartoes.map((c) => ({ frente: c.frente, verso: c.verso, pagina: c.pagina })),
    });
    botao.textContent = r.salvos
      ? `✔ ${r.salvos} salvo(s) no baralho${r.repetidos ? ` · ${r.repetidos} já estavam lá` : ""}`
      : "Esses cartões já estavam no seu baralho";
  } catch (erro) {
    botao.disabled = false;
    botao.textContent = `✖ ${erro.message}`;
  }
}
