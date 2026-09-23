// Tela "Calendário": mostra o mês com eventos da turma (professor), lembretes
// pessoais (aluno) e prazos das atividades. Para agendar, o usuário clica em um
// ou mais dias, escolhe o horário na coluna ao lado e salva. Na hora marcada,
// o sistema avisa (em qualquer tela do app e, se permitido, com notificação do navegador).

const MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

// Horários sugeridos: das 06:00 às 23:30, de meia em meia hora
const HORARIOS = Array.from({ length: 36 }, (_, i) => {
  const minutos = 6 * 60 + i * 30;
  return `${String(Math.floor(minutos / 60)).padStart(2, "0")}:${String(minutos % 60).padStart(2, "0")}`;
});

let mesVisivel = new Date();       // qualquer dia do mês exibido
let itensCalendario = [];          // [{id?, titulo, data, hora, descricao, tipo: "turma"|"pessoal"|"prazo"}]
const diasEscolhidos = new Set();  // "AAAA-MM-DD"
let horaEscolhida = null;          // "HH:MM" ou "" (dia todo)

const formEvento = $("form-evento");

TELAS.calendario = {
  abrir() {
    atualizarBotaoNotificacoes();
    if (!disciplinaAtual) return;
    $("salvar-evento").textContent = usuario.tipo === "professor" ? "Salvar para a turma" : "Salvar lembrete";
    if (horaEscolhida === null) horaEscolhida = proximoHorario();
    desenharHorarios();
    carregarCalendario();
  },
};

async function carregarCalendario() {
  const [eventos, atividades] = await Promise.all([
    chamarApi(rotaDisciplina("/eventos")),
    chamarApi(rotaDisciplina("/atividades")),
  ]);
  itensCalendario = [
    ...eventos.map((e) => ({ ...e, tipo: e.publico ? "turma" : "pessoal" })),
    ...atividades.map((a) => ({ titulo: `Prazo: ${a.titulo}`, data: a.prazo, hora: null, descricao: a.descricao, tipo: "prazo" })),
  ].sort((a, b) => a.data.localeCompare(b.data) || (a.hora || "").localeCompare(b.hora || ""));
  desenharMes();
  desenharLista();
}

// ---------------------------------------------------------- datas

function isoDe(ano, mes, dia) {
  return `${ano}-${String(mes + 1).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
}

function dataDeIso(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d);
}

function somarDias(iso, dias) {
  const d = dataDeIso(iso);
  d.setDate(d.getDate() + dias);
  return isoDe(d.getFullYear(), d.getMonth(), d.getDate());
}

function diaPorExtenso(iso) {  // "qua., 1 de outubro"
  return dataDeIso(iso).toLocaleDateString("pt-BR", { weekday: "short", day: "numeric", month: "long" });
}

function agoraHHMM() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function proximoHorario() {
  return HORARIOS.find((h) => h > agoraHHMM()) || "09:00";
}

// ---------------------------------------------------------- mês

function desenharMes() {
  const ano = mesVisivel.getFullYear();
  const mes = mesVisivel.getMonth();
  $("mes-titulo").textContent = `${MESES[mes]} de ${ano}`;

  const primeiroDiaSemana = new Date(ano, mes, 1).getDay();
  const diasNoMes = new Date(ano, mes + 1, 0).getDate();
  const hoje = hojeIso();

  let html = DIAS_SEMANA.map((d) => `<div class="dia-semana">${d}</div>`).join("");
  html += `<div class="dia vazio"></div>`.repeat(primeiroDiaSemana);
  for (let dia = 1; dia <= diasNoMes; dia++) {
    const iso = isoDe(ano, mes, dia);
    const doDia = itensCalendario.filter((i) => i.data === iso);
    const passado = iso < hoje;
    const classes = ["dia", iso === hoje && "hoje", passado && "passado", diasEscolhidos.has(iso) && "escolhido"]
      .filter(Boolean).join(" ");
    html += `<button type="button" class="${classes}" data-dia="${iso}" ${passado ? "disabled" : ""}
        aria-pressed="${diasEscolhidos.has(iso)}" aria-label="${diaPorExtenso(iso)}">
      <span class="numero">${dia}</span>
      ${doDia.slice(0, 3).map((i) => {
        const texto = `${i.hora ? i.hora + " " : ""}${i.titulo}`;
        return `<span class="marca ${i.tipo}" title="${escaparHtml(texto)}">${escaparHtml(texto)}</span>`;
      }).join("")}
      ${doDia.length > 3 ? `<span class="mais">+${doDia.length - 3}</span>` : ""}
    </button>`;
  }
  const grade = $("grade-calendario");
  grade.innerHTML = html;
  for (const botao of grade.querySelectorAll("button.dia")) {
    botao.onclick = () => {
      const iso = botao.dataset.dia;
      if (diasEscolhidos.has(iso)) diasEscolhidos.delete(iso);
      else diasEscolhidos.add(iso);
      desenharMes();
      desenharLista();
      atualizarResumo();
    };
  }
}

function mudarMes(delta) {
  mesVisivel = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth() + delta, 1);
  desenharMes();
}

$("mes-anterior").onclick = () => mudarMes(-1);
$("mes-seguinte").onclick = () => mudarMes(1);
$("mes-hoje").onclick = () => {
  mesVisivel = new Date();
  desenharMes();
};

// ---------------------------------------------------------- horários

function desenharHorarios() {
  const coluna = $("lista-horarios");
  const personalizado = horaEscolhida && !HORARIOS.includes(horaEscolhida) ? horaEscolhida : "";
  coluna.innerHTML = `
    <label class="hora-personalizada">Outro horário
      <input type="time" id="input-hora" value="${personalizado}">
    </label>
    <button type="button" class="horario ${horaEscolhida === "" ? "ativo" : ""}" data-hora="" role="option"
      aria-selected="${horaEscolhida === ""}">Dia todo</button>
    ${HORARIOS.map((h) => `<button type="button" class="horario ${h === horaEscolhida ? "ativo" : ""}"
      data-hora="${h}" role="option" aria-selected="${h === horaEscolhida}">${h}</button>`).join("")}`;

  for (const botao of coluna.querySelectorAll(".horario")) {
    botao.onclick = () => escolherHora(botao.dataset.hora);
  }
  $("input-hora").onchange = (e) => { if (e.target.value) escolherHora(e.target.value); };

  // Rola só a coluna (não a página) até o horário escolhido
  const ativo = coluna.querySelector(".horario.ativo");
  if (ativo) coluna.scrollTop = ativo.offsetTop - coluna.clientHeight / 2;
  atualizarResumo();
}

function escolherHora(hora) {
  horaEscolhida = hora;
  const coluna = $("lista-horarios");
  for (const botao of coluna.querySelectorAll(".horario")) {
    const ativo = botao.dataset.hora === hora;
    botao.classList.toggle("ativo", ativo);
    botao.setAttribute("aria-selected", ativo);
  }
  if (HORARIOS.includes(hora) || hora === "") $("input-hora").value = "";
  atualizarResumo();
}

// ---------------------------------------------------------- resumo e envio

// Dias escolhidos + repetições semanais, sem duplicatas e em ordem
function datasParaSalvar() {
  const semanas = Number(formEvento.repetir.value);
  const datas = new Set();
  for (const dia of diasEscolhidos) {
    for (let s = 0; s < semanas; s++) datas.add(somarDias(dia, 7 * s));
  }
  return [...datas].sort();
}

function atualizarResumo() {
  const resumo = $("resumo-agenda");
  const dias = [...diasEscolhidos].sort();
  const datas = datasParaSalvar();
  $("limpar-dias").hidden = !dias.length;
  $("salvar-evento").disabled = !dias.length || datas.length > 100;

  if (!dias.length) {
    resumo.textContent = "Escolha um ou mais dias no calendário.";
    return;
  }
  const quando = horaEscolhida ? `às <strong>${horaEscolhida}</strong>` : "<strong>o dia todo</strong>";
  const nomes = dias.length <= 3
    ? dias.map((d) => `<strong>${diaPorExtenso(d)}</strong>`).join(", ")
    : `<strong>${dias.length} dias</strong> (de ${formatarDia(dias[0])} a ${formatarDia(dias.at(-1))})`;
  let texto = `Lembrete em ${nomes}, ${quando}.`;
  if (datas.length > dias.length) texto += ` Com a repetição, serão <strong>${datas.length}</strong> lembretes.`;
  if (datas.length > 100) texto += ` <span class="erro">O máximo é 100 de uma vez.</span>`;
  resumo.innerHTML = texto;
}

formEvento.repetir.onchange = atualizarResumo;

$("limpar-dias").onclick = () => {
  diasEscolhidos.clear();
  desenharMes();
  desenharLista();
  atualizarResumo();
};

formEvento.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const botao = $("salvar-evento");
  botao.disabled = true;
  try {
    const r = await postarJson(rotaDisciplina("/eventos"), {
      titulo: formEvento.titulo.value,
      descricao: formEvento.descricao.value,
      datas: datasParaSalvar(),
      hora: horaEscolhida || null,
    });
    formEvento.titulo.value = "";
    formEvento.descricao.value = "";
    formEvento.repetir.value = "1";
    diasEscolhidos.clear();
    lembretesDoDia.data = null;  // força buscar de novo os avisos de hoje
    mostrarAviso({ titulo: "✔ Salvo", texto: `${r.criados} lembrete(s) no calendário.` }, 4000);
    await carregarCalendario();
    atualizarResumo();
  } catch (erro) {
    alert(erro.message);
    botao.disabled = false;
  }
});

// ---------------------------------------------------------- lista abaixo do calendário

function desenharLista() {
  const hoje = hojeIso();
  const dias = [...diasEscolhidos];
  const itens = dias.length
    ? itensCalendario.filter((i) => diasEscolhidos.has(i.data))
    : itensCalendario.filter((i) => i.data >= hoje).slice(0, 15);
  $("dia-titulo").textContent = dias.length ? "Nos dias escolhidos" : "Próximos eventos";

  const lista = $("lista-eventos");
  if (!itens.length) {
    lista.innerHTML = `<p class="dica">${dias.length ? "Nada marcado nesses dias ainda." : "Nenhum evento futuro."}</p>`;
    return;
  }
  const nomes = { turma: "Turma", pessoal: "Pessoal", prazo: "Atividade" };
  lista.innerHTML = "";
  for (const i of itens) {
    const div = document.createElement("div");
    div.className = `evento ${i.tipo}`;
    div.innerHTML = `
      <div class="item-topo">
        <strong>${escaparHtml(i.titulo)}</strong>
        ${i.usuario_id === usuario.id ? `<button type="button" class="remover" title="Remover">✕</button>` : ""}
      </div>
      <small class="dica">${diaPorExtenso(i.data)} · ${i.hora ? `⏰ ${i.hora}` : "dia todo"} · ${nomes[i.tipo]}${
        i.autor && i.tipo === "turma" ? ` · ${escaparHtml(i.autor)}` : ""}</small>
      ${i.descricao ? `<p>${escaparHtml(i.descricao)}</p>` : ""}`;
    const remover = div.querySelector(".remover");
    if (remover) remover.onclick = async () => {
      if (!confirm(`Remover "${i.titulo}" de ${formatarDia(i.data)}?`)) return;
      await chamarApi(rotaDisciplina(`/eventos/${i.id}`), { method: "DELETE" });
      lembretesDoDia.data = null;
      carregarCalendario();
    };
    lista.appendChild(div);
  }
}

// ---------------------------------------------------------- avisos na hora marcada

const lembretesDoDia = { data: null, buscadoEm: 0, itens: [] };
const JANELA_AVISO_MIN = 15;  // avisa se o app estiver aberto até 15 min depois do horário

function mostrarAviso({ titulo, texto }, duracaoMs = 0) {
  const aviso = document.createElement("div");
  aviso.className = "aviso-lembrete";
  aviso.innerHTML = `<div><strong>${escaparHtml(titulo)}</strong><p>${escaparHtml(texto)}</p></div>
    <button type="button" class="remover" aria-label="Fechar">✕</button>`;
  aviso.querySelector("button").onclick = () => aviso.remove();
  $("avisos").appendChild(aviso);
  if (duracaoMs) setTimeout(() => aviso.remove(), duracaoMs);
}

function avisadosDe(data) {
  try { return new Set(JSON.parse(localStorage.getItem(`avisados-${data}`)) || []); } catch { return new Set(); }
}

function marcarAvisado(data, id) {
  const ids = avisadosDe(data);
  ids.add(id);
  try { localStorage.setItem(`avisados-${data}`, JSON.stringify([...ids])); } catch {}
}

function minutosDesde(hora) {
  const [h, m] = hora.split(":").map(Number);
  const agora = new Date();
  return agora.getHours() * 60 + agora.getMinutes() - (h * 60 + m);
}

async function verificarLembretes() {
  if (!usuario) return;  // ainda carregando o app
  const hoje = hojeIso();
  // Busca os lembretes de hoje a cada 5 minutos (ou quando o dia muda / algo foi salvo)
  if (lembretesDoDia.data !== hoje || Date.now() - lembretesDoDia.buscadoEm > 5 * 60 * 1000) {
    try {
      lembretesDoDia.itens = await chamarApi(`/api/lembretes?data=${hoje}`);
      lembretesDoDia.data = hoje;
      lembretesDoDia.buscadoEm = Date.now();
    } catch {
      return;
    }
  }
  const avisados = avisadosDe(hoje);
  for (const l of lembretesDoDia.itens) {
    const passou = minutosDesde(l.hora);
    if (passou < 0 || passou > JANELA_AVISO_MIN || avisados.has(l.id)) continue;
    marcarAvisado(hoje, l.id);
    const texto = `${l.hora} · ${l.disciplina}${l.descricao ? ` · ${l.descricao}` : ""}`;
    mostrarAviso({ titulo: `⏰ ${l.titulo}`, texto });
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(`⏰ ${l.titulo}`, { body: texto });
    }
  }
}

setInterval(verificarLembretes, 30 * 1000);
setTimeout(verificarLembretes, 3000);

// Notificações do navegador (funcionam mesmo com a aba em segundo plano)
function atualizarBotaoNotificacoes() {
  const botao = $("botao-notificacoes");
  if (!("Notification" in window)) return;
  botao.hidden = false;
  const ativadas = Notification.permission === "granted";
  botao.disabled = ativadas || Notification.permission === "denied";
  botao.textContent = ativadas ? "🔔 Notificações ativadas"
    : Notification.permission === "denied" ? "🔕 Notificações bloqueadas no navegador" : "🔔 Ativar notificações";
}

$("botao-notificacoes").onclick = async () => {
  await Notification.requestPermission();
  atualizarBotaoNotificacoes();
};
