// Frontend do Assistente de Estudos: conversa com o backend via fetch().

const $ = (id) => document.getElementById(id);
const mensagens = $("mensagens");
const formPergunta = $("form-pergunta");
const inputPergunta = $("input-pergunta");
const inputPdf = $("input-pdf");
const inputAnexos = $("input-anexos");
const botaoAnexar = $("anexar-pdf");
const caixaAnexos = $("anexos-chat");
const menuComandos = $("menu-comandos");
const estadoCompositor = $("compositor-estado");
const botaoEnviarPergunta = $("enviar-pergunta");
const statusUpload = $("status-upload");
const listaDocumentos = $("lista-documentos");
const selectDisciplina = $("select-disciplina");
let arquivosAnexados = [];
let indiceComandoAtivo = 0;
let controladorChat = null;

const COMANDOS_CHAT = [
  { comando: "/explicar", resumo: "Explicar um conceito", modelo: "Explique de forma simples e com um exemplo: " },
  { comando: "/resumir", resumo: "Resumir um assunto", modelo: "Faça um resumo dos principais pontos sobre: " },
  { comando: "/questoes", resumo: "Criar perguntas de revisão", modelo: "Crie 5 perguntas de revisão sobre: " },
  { comando: "/flashcards", resumo: "Criar flashcards de estudo", modelo: "Crie flashcards de pergunta e resposta sobre: " },
];

let usuario = null;      // {id, nome, email, tipo}
let disciplinas = [];    // [{id, nome, criado_por, ...}]
let disciplinaAtual = null;

// Telas do menu. Cada arquivo .js registra a sua: TELAS.nome = { abrir(), sair() }.
// abrir() é chamado ao entrar na tela e ao trocar de disciplina; sair() é opcional.
const TELAS = {};
let telaAtual = "assistente";

// ---------------------------------------------------------- utilidades

async function chamarApi(url, opcoes = {}) {
  const resposta = await fetch(url, opcoes);
  if (resposta.status === 401) {  // sessão expirou ou não fez login
    location.href = "/login.html";
    throw new Error("Faça login para continuar.");
  }
  const texto = await resposta.text();
  let dados = {};
  try {
    dados = texto ? JSON.parse(texto) : {};
  } catch {
    const trecho = texto.replace(/\s+/g, " ").slice(0, 180);
    throw new Error(`Resposta inválida do servidor (HTTP ${resposta.status}). ${trecho || "Confira se o backend está em execução."}`);
  }
  if (!resposta.ok) throw new Error(dados.detail || "Erro no servidor");
  return dados;
}

function postarJson(url, corpo) {
  return chamarApi(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
}

const rotaDisciplina = (caminho = "") => `/api/disciplinas/${disciplinaAtual.id}${caminho}`;

// Escapa também as aspas, para poder usar o texto dentro de atributos: value="..."
const ENTIDADES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function escaparHtml(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ENTIDADES[c]);
}

function formatarData(texto) {
  // O SQLite grava em UTC no formato "AAAA-MM-DD HH:MM:SS"
  return new Date(texto.replace(" ", "T") + "Z").toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function adicionarMensagem(tipo, html) {
  const div = document.createElement("div");
  div.className = `mensagem ${tipo}`;
  if (tipo.split(" ").includes("usuario")) {
    div.dataset.avatar = iniciaisDoNome(usuario?.nome || "Você");
    div.style.setProperty("--avatar-cor", corDoAvatarNome(usuario?.nome || "Você"));
    div.setAttribute("role", "group");
    div.setAttribute("aria-label", `Mensagem de ${usuario?.nome || "Você"}`);
  }
  div.innerHTML = html;
  mensagens.appendChild(div);
  mensagens.scrollTop = mensagens.scrollHeight;
  return div;
}

function iniciaisDoNome(nome) {
  return String(nome || "?").trim().split(/\s+/).filter(Boolean).slice(0, 2)
    .map((parte) => [...parte][0].toLocaleUpperCase("pt-BR")).join("") || "?";
}

function corDoAvatarNome(nome) {
  let hash = 0;
  for (const caractere of String(nome || "")) hash = (hash * 31 + caractere.codePointAt(0)) | 0;
  return `hsl(${Math.abs(hash) % 360} 62% 46%)`;
}

function rodapeModelo(modelo) {
  return modelo ? `<div class="modelo">gerado por ${escaparHtml(modelo)}</div>` : "";
}

// Markdown simples: "## título", "- tópico" e **negrito**
function markdownParaHtml(texto) {
  const negrito = (s) => escaparHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  let html = "";
  let emLista = false;
  for (const linha of texto.split("\n")) {
    const l = linha.trim();
    const item = l.match(/^[-*]\s+(.*)/);
    if (item) {
      if (!emLista) { html += "<ul>"; emLista = true; }
      html += `<li>${negrito(item[1])}</li>`;
      continue;
    }
    if (emLista) { html += "</ul>"; emLista = false; }
    if (l.startsWith("#")) html += `<h3>${negrito(l.replace(/^#+\s*/, ""))}</h3>`;
    else if (l) html += `<p>${negrito(l)}</p>`;
  }
  return emLista ? html + "</ul>" : html;
}

function lembrarDisciplina(id) {
  try { localStorage.setItem("disciplina", id); } catch {}
}

function disciplinaLembrada() {
  try { return Number(localStorage.getItem("disciplina")); } catch { return null; }
}

function hojeIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatarDia(iso) {  // "2026-09-23" → "23/09/2026"
  return iso.split("-").reverse().join("/");
}

// Lê os campos de um <form> como objeto: {titulo: "...", data: "..."}
const dadosDoForm = (form) => Object.fromEntries(new FormData(form));

// ---------------------------------------------------------- navegação

function mostrarTela(nome) {
  if (!TELAS[nome] || (nome === "painel" && usuario.tipo !== "professor")) nome = "assistente";
  if (nome !== telaAtual) TELAS[telaAtual]?.sair?.();
  telaAtual = nome;
  try { localStorage.setItem("tela", nome); } catch {}

  for (const b of document.querySelectorAll("button[data-tela]")) {
    b.classList.toggle("ativo", b.dataset.tela === nome);
  }
  fecharLateral();
  for (const tela of document.querySelectorAll(".tela")) tela.hidden = tela.id !== `tela-${nome}`;
  $("secao-materiais").hidden = nome !== "assistente" || !disciplinaAtual;
  TELAS[nome].abrir();
}

for (const botao of document.querySelectorAll("button[data-tela]")) {
  botao.onclick = () => mostrarTela(botao.dataset.tela);
}

// No celular a barra lateral é uma gaveta: abre pelo botão ☰ e fecha ao escolher uma tela
function abrirLateral() {
  $("lateral").classList.add("aberta");
  $("fundo-lateral").hidden = false;
  $("abrir-lateral").setAttribute("aria-expanded", "true");
}

function fecharLateral() {
  $("lateral").classList.remove("aberta");
  $("fundo-lateral").hidden = true;
  $("abrir-lateral").setAttribute("aria-expanded", "false");
}

$("abrir-lateral").onclick = abrirLateral;
$("fundo-lateral").onclick = fecharLateral;
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharLateral(); });

// As áreas que dependem de uma disciplina mostram um aviso quando não há nenhuma
function atualizarAreasDaDisciplina() {
  for (const area of document.querySelectorAll(".precisa-disciplina")) area.hidden = !disciplinaAtual;
  for (const aviso of document.querySelectorAll(".sem-disciplina")) aviso.hidden = Boolean(disciplinaAtual);
}

// ---------------------------------------------------------- usuário

async function iniciar() {
  usuario = await chamarApi("/api/auth/eu");
  mostrarUsuario();
  $("tipo-usuario").classList.add(usuario.tipo);
  for (const el of document.querySelectorAll("[data-so-professor]")) el.hidden = usuario.tipo !== "professor" && !usuario.administrador;
  for (const tela of document.querySelectorAll(".tela")) {
    const area = tela.querySelector(".precisa-disciplina");
    if (area) area.insertAdjacentHTML("beforebegin",
      `<p class="dica sem-disciplina" hidden>Selecione ou crie uma disciplina (botão <strong>+</strong>) para usar esta área.</p>`);
  }
  let telaSalva = null;
  try { telaSalva = localStorage.getItem("tela"); } catch {}
  telaAtual = TELAS[telaSalva] ? telaSalva : "disciplinas";
  await carregarDisciplinas(disciplinaLembrada());
}

function mostrarUsuario() {
  $("nome-usuario").textContent = usuario.nome;
  $("nome-usuario").title = usuario.email;
  // Iniciais do primeiro e do último nome: "Giovanni Andrade" → "GA"
  const partes = usuario.nome.trim().split(/\s+/);
  $("avatar-usuario").textContent = (partes[0][0] + (partes.length > 1 ? partes.at(-1)[0] : "")).toUpperCase();
  $("tipo-usuario").textContent = usuario.administrador ? "🛡️ Administrador" : usuario.tipo === "professor" ? "👩‍🏫 Professor" : "🎓 Aluno";
}

$("botao-sair").onclick = async () => {
  await postarJson("/api/auth/logout", {});
  location.href = "/login.html";
};

// ---------------------------------------------------------- disciplinas

async function carregarDisciplinas(selecionarId) {
  disciplinas = await chamarApi("/api/disciplinas");
  selectDisciplina.innerHTML = disciplinas.length
    ? disciplinas.map((d) => `<option value="${d.id}">${escaparHtml(d.nome)}</option>`).join("")
    : `<option value="">Nenhuma disciplina</option>`;

  const escolhida = disciplinas.find((d) => d.id === selecionarId) || disciplinas[0] || null;
  if (escolhida) selectDisciplina.value = escolhida.id;
  selecionarDisciplina(escolhida);
}

function selecionarDisciplina(disciplina) {
  disciplinaAtual = disciplina;
  mensagens.innerHTML = "";
  const temDisciplina = Boolean(disciplina);
  $("botao-remover-disciplina").hidden = !temDisciplina || disciplina.criado_por !== usuario.id;
  inputPergunta.disabled = !temDisciplina;
  botaoEnviarPergunta.disabled = !temDisciplina;
  botaoAnexar.disabled = !temDisciplina;
  atualizarAreasDaDisciplina();

  $("assistente-subtitulo").textContent = temDisciplina
    ? `${disciplina.nome} · respostas baseadas nos PDFs, com as fontes citadas.`
    : "Respostas baseadas nos PDFs da disciplina, com as fontes citadas.";

  if (!temDisciplina) {
    adicionarMensagem("bot", `Olá, ${escaparHtml(usuario.nome)}! Crie uma disciplina no botão <strong>+</strong> ao lado para começar.`);
  } else {
    lembrarDisciplina(disciplina.id);
    mostrarBoasVindas(disciplina);
    carregarDocumentos();
  }
  mostrarTela(telaAtual);  // recarrega a tela aberta com os dados da nova disciplina
}

// Cartão inicial do chat, com perguntas prontas para o aluno não começar do zero
const SUGESTOES = [
  "Quais são os principais conceitos deste material?",
  "Explique o conteúdo da primeira aula de forma simples",
  "Crie 3 perguntas para eu revisar a matéria",
];

function mostrarBoasVindas(disciplina) {
  const primeiroNome = usuario.nome.trim().split(/\s+/)[0];
  const cartao = adicionarMensagem("bot boas-vindas", `
    <p class="boas-vindas-titulo">Olá, ${escaparHtml(primeiroNome)}! 👋</p>
    <p>Você está em <strong>${escaparHtml(disciplina.nome)}</strong>. Pergunte qualquer coisa sobre os PDFs da disciplina:
      eu respondo citando o arquivo e a página de onde tirei cada informação.</p>
    <div class="sugestoes">${SUGESTOES.map((s) => `<button type="button" class="sugestao">${escaparHtml(s)}</button>`).join("")}</div>`);
  for (const botao of cartao.querySelectorAll(".sugestao")) {
    botao.onclick = () => {
      inputPergunta.value = botao.textContent;
      formPergunta.requestSubmit();
    };
  }
}

selectDisciplina.onchange = () => {
  selecionarDisciplina(disciplinas.find((d) => d.id === Number(selectDisciplina.value)));
};

$("botao-nova-disciplina").onclick = async () => {
  const nome = prompt("Nome da nova disciplina:");
  if (!nome || !nome.trim()) return;
  try {
    const nova = await postarJson("/api/disciplinas", { nome });
    await carregarDisciplinas(nova.id);
  } catch (erro) {
    alert(erro.message);
  }
};

$("botao-remover-disciplina").onclick = async () => {
  if (!confirm(`Remover a disciplina "${disciplinaAtual.nome}" e todos os seus materiais?`)) return;
  await chamarApi(rotaDisciplina(), { method: "DELETE" });
  await carregarDisciplinas();
};

// ---------------------------------------------------------- documentos

async function carregarDocumentos() {
  const docs = await chamarApi(rotaDisciplina("/documentos"));
  listaDocumentos.innerHTML = docs.length
    ? ""
    : "<li><small>Nenhum material enviado.</small></li>";

  for (const doc of docs) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div class="doc-topo">
        <span class="nome" title="${escaparHtml(doc.arquivo)}">📄 ${escaparHtml(doc.arquivo)}</span>
        <button class="remover" title="Remover">✕</button>
      </div>
      <small>${doc.trechos} trechos · enviado por ${escaparHtml(doc.enviado_por)}</small>
      <label class="marcar-estudada"><input type="checkbox" ${doc.concluida ? "checked" : ""}> Aula estudada</label>
      <div class="acoes">
        <button data-acao="resumo">📝 Resumo</button>
        <button data-acao="flashcards">🃏 Flashcards</button>
        <button data-acao="simulado">❓ Simulado</button>
      </div>`;
    if (doc.concluida) li.classList.add("concluida");
    li.querySelector(".marcar-estudada input").onchange = async (e) => {
      li.classList.toggle("concluida", e.target.checked);
      try {
        await chamarApi(`/api/aulas/${doc.id}/concluida`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ concluida: e.target.checked }),
        });
        visaoGeral = [];  // a tela "Minhas disciplinas" recarrega o progresso ao ser aberta
      } catch (erro) {
        e.target.checked = !e.target.checked;
        li.classList.toggle("concluida", e.target.checked);
        alert(erro.message);
      }
    };
    li.querySelector(".remover").onclick = async () => {
      if (!confirm(`Remover ${doc.arquivo}?`)) return;
      await chamarApi(rotaDisciplina(`/documentos/${encodeURIComponent(doc.arquivo)}`), { method: "DELETE" });
      carregarDocumentos();
    };
    for (const botao of li.querySelectorAll(".acoes button")) {
      botao.onclick = () => executarAcao(botao.dataset.acao, doc.arquivo);
    }
    listaDocumentos.appendChild(li);
  }
}

inputPdf.addEventListener("change", async () => {
  for (const arquivo of inputPdf.files) {
    statusUpload.textContent = `Processando ${arquivo.name}...`;
    const dados = new FormData();
    dados.append("arquivo", arquivo);
    try {
      const r = await chamarApi(rotaDisciplina("/documentos"), { method: "POST", body: dados });
      statusUpload.textContent = `✔ ${r.arquivo}: ${r.trechos} trechos indexados`;
    } catch (erro) {
      statusUpload.textContent = `✖ ${arquivo.name}: ${erro.message}`;
    }
  }
  inputPdf.value = "";
  carregarDocumentos();
});

// ---------------------------------------------------------- ferramentas de estudo

const ACOES = {
  resumo:     { titulo: "Resumo",     rota: "/resumo",     corpo: {},                render: renderResumo },
  flashcards: { titulo: "Flashcards", rota: "/flashcards", corpo: { quantidade: 10 }, render: renderFlashcards },
  simulado:   { titulo: "Simulado",   rota: "/simulado",   corpo: { quantidade: 5 },  render: renderSimulado },
};

async function executarAcao(nome, arquivo) {
  const acao = ACOES[nome];
  const botoes = listaDocumentos.querySelectorAll(".acoes button");
  botoes.forEach((b) => (b.disabled = true));
  adicionarMensagem("usuario", `${acao.titulo} de <em>${escaparHtml(arquivo)}</em>`);
  const caixa = adicionarMensagem("bot carregando", `Gerando ${acao.titulo.toLowerCase()}... (pode levar alguns segundos)`);

  try {
    const r = await postarJson(rotaDisciplina(acao.rota), { arquivo, ...acao.corpo });
    caixa.className = "mensagem bot rica";
    caixa.innerHTML = (r.aviso ? `<p class="aviso">⚠️ ${escaparHtml(r.aviso)}</p>` : "");
    acao.render(caixa, r);
    caixa.insertAdjacentHTML("beforeend", rodapeModelo(r.modelo));
  } catch (erro) {
    caixa.className = "mensagem bot";
    caixa.textContent = `Erro: ${erro.message}`;
  } finally {
    botoes.forEach((b) => (b.disabled = false));
  }
}

function renderResumo(caixa, r) {
  caixa.insertAdjacentHTML("beforeend", markdownParaHtml(r.resumo));
}

function renderFlashcards(caixa, r) {
  caixa.insertAdjacentHTML("beforeend",
    `<h3>🃏 ${r.flashcards.length} flashcards</h3><p class="dica">Clique num cartão para ver a resposta.</p>`);
  const grade = document.createElement("div");
  grade.className = "grade-cartoes";
  for (const c of r.flashcards) {
    const cartao = document.createElement("div");
    cartao.className = "cartao";
    cartao.innerHTML = `
      <div class="lado frente">${escaparHtml(c.frente)}</div>
      <div class="lado verso">${escaparHtml(c.verso)}<small>p. ${c.pagina}</small></div>`;
    cartao.onclick = () => cartao.classList.toggle("virado");
    grade.appendChild(cartao);
  }
  caixa.appendChild(grade);
}

let contadorSimulados = 0;

function renderSimulado(caixa, r) {
  const id = ++contadorSimulados;
  const letras = ["A", "B", "C", "D"];
  let html = `<h3>❓ Simulado: ${r.questoes.length} questões</h3>`;
  r.questoes.forEach((q, i) => {
    html += `<div class="questao" data-indice="${i}">
      <p><strong>${i + 1}.</strong> ${escaparHtml(q.pergunta)}</p>
      ${q.alternativas.map((alt, j) => `
        <label class="alternativa">
          <input type="radio" name="sim${id}-q${i}" value="${j}">
          <span>${letras[j]}) ${escaparHtml(alt)}</span>
        </label>`).join("")}
      <p class="explicacao" hidden></p>
    </div>`;
  });
  html += `<button class="corrigir">Corrigir</button><p class="nota"></p>`;
  caixa.insertAdjacentHTML("beforeend", html);

  caixa.querySelector(".corrigir").onclick = (evento) => {
    let acertos = 0;
    r.questoes.forEach((q, i) => {
      const bloco = caixa.querySelector(`.questao[data-indice="${i}"]`);
      const marcada = bloco.querySelector("input:checked");
      const labels = bloco.querySelectorAll(".alternativa");
      labels[q.correta].classList.add("certa");
      if (marcada && Number(marcada.value) === q.correta) acertos++;
      else if (marcada) labels[marcada.value].classList.add("errada");
      bloco.querySelectorAll("input").forEach((inp) => (inp.disabled = true));
      const exp = bloco.querySelector(".explicacao");
      exp.textContent = `${q.explicacao} (p. ${q.pagina})`;
      exp.hidden = false;
    });
    caixa.querySelector(".nota").textContent = `Você acertou ${acertos} de ${r.questoes.length}.`;
    evento.target.remove();
    // Guarda a nota para o painel do professor
    postarJson(rotaDisciplina("/simulado/resultado"), { arquivo: r.arquivo, acertos, total: r.questoes.length })
      .then(() => { if (telaAtual === "simulados") carregarHistoricoSimulados(); })
      .catch(() => {});
  };
}

// ---------------------------------------------------------- chat

function formatarResposta(texto, fontes) {
  // Transforma [1], [2]... em etiquetas com o nome do arquivo/página ao passar o mouse
  let html = escaparHtml(texto)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\[(\d+)\]/g, (original, n) => {
      const f = fontes[n - 1];
      if (!f) return original;
      return `<span class="citacao" title="${escaparHtml(f.arquivo)} — pág. ${f.pagina}">${n}</span>`;
    });

  if (fontes.length) {
    const itens = fontes.map((f, i) => `
      <div class="fonte">
        <strong>[${i + 1}]</strong> ${escaparHtml(f.arquivo)}, pág. ${f.pagina}
        <small>(similaridade ${f.similaridade})</small><br>
        ${escaparHtml(f.texto.slice(0, 300))}${f.texto.length > 300 ? "..." : ""}
      </div>`).join("");
    html += `<details class="fontes"><summary>Ver trechos usados (${fontes.length})</summary>${itens}</details>`;
  }
  return html;
}

function redimensionarCompositor() {
  inputPergunta.style.height = "auto";
  inputPergunta.style.height = `${Math.min(inputPergunta.scrollHeight, 180)}px`;
}

function comandosCorrespondentes() {
  const inicio = inputPergunta.value.match(/^\s*\/[^\s]*/)?.[0];
  if (inicio === undefined) return [];
  const filtro = inicio.trim().toLowerCase();
  return COMANDOS_CHAT.filter((item) => item.comando.startsWith(filtro));
}

function desenharMenuComandos() {
  const resultados = comandosCorrespondentes();
  menuComandos.hidden = !resultados.length;
  if (!resultados.length) return;
  indiceComandoAtivo = Math.min(indiceComandoAtivo, resultados.length - 1);
  menuComandos.innerHTML = resultados.map((item, i) => `
    <button type="button" class="comando-opcao" role="option" aria-selected="${i === indiceComandoAtivo}" data-comando="${item.comando}">
      <strong>${item.comando}</strong><small>${item.resumo}</small>
    </button>`).join("");
  for (const opcao of menuComandos.querySelectorAll(".comando-opcao")) {
    opcao.onpointerdown = (e) => e.preventDefault();
    opcao.onclick = () => aplicarComando(opcao.dataset.comando);
  }
}

function aplicarComando(comando) {
  const item = COMANDOS_CHAT.find((c) => c.comando === comando);
  if (!item) return;
  inputPergunta.value = inputPergunta.value.replace(/^\s*\/[^\s]*/, item.modelo);
  menuComandos.hidden = true;
  redimensionarCompositor();
  inputPergunta.focus();
  inputPergunta.setSelectionRange(inputPergunta.value.length, inputPergunta.value.length);
}

inputPergunta.addEventListener("input", () => {
  indiceComandoAtivo = 0;
  redimensionarCompositor();
  desenharMenuComandos();
});
inputPergunta.addEventListener("keydown", (evento) => {
  if (!menuComandos.hidden) {
    const opcoes = [...menuComandos.querySelectorAll(".comando-opcao")];
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      indiceComandoAtivo = (indiceComandoAtivo + (evento.key === "ArrowDown" ? 1 : -1) + opcoes.length) % opcoes.length;
      desenharMenuComandos();
      return;
    }
    if (evento.key === "Escape") { menuComandos.hidden = true; return; }
    if (evento.key === "Enter" && !evento.shiftKey) {
      evento.preventDefault();
      aplicarComando(opcoes[indiceComandoAtivo].dataset.comando);
      return;
    }
  }
  if (evento.key === "Enter" && !evento.shiftKey) {
    evento.preventDefault();
    formPergunta.requestSubmit();
  }
});

botaoAnexar.onclick = () => { if (disciplinaAtual && !controladorChat) inputAnexos.click(); };
inputAnexos.addEventListener("change", () => {
  const porChave = new Map(arquivosAnexados.map((a) => [`${a.name}:${a.size}:${a.lastModified}`, a]));
  for (const arquivo of inputAnexos.files) {
    if (arquivo.type !== "application/pdf" && !arquivo.name.toLowerCase().endsWith(".pdf")) {
      estadoCompositor.textContent = `${arquivo.name}: somente arquivos PDF podem ser anexados.`;
      continue;
    }
    porChave.set(`${arquivo.name}:${arquivo.size}:${arquivo.lastModified}`, arquivo);
  }
  arquivosAnexados = [...porChave.values()];
  inputAnexos.value = "";
  desenharAnexos();
});

function desenharAnexos() {
  caixaAnexos.hidden = !arquivosAnexados.length;
  caixaAnexos.innerHTML = arquivosAnexados.map((arquivo, i) => `
    <span class="anexo-chat" title="${escaparHtml(arquivo.name)}">
      <svg aria-hidden="true"><use href="#i-clipe"/></svg>
      <span class="anexo-chat-nome">${escaparHtml(arquivo.name)}</span>
      <button type="button" class="anexo-chat-remover" data-indice="${i}" aria-label="Remover ${escaparHtml(arquivo.name)}">×</button>
    </span>`).join("");
  for (const remover of caixaAnexos.querySelectorAll(".anexo-chat-remover")) {
    remover.onclick = () => {
      arquivosAnexados.splice(Number(remover.dataset.indice), 1);
      desenharAnexos();
    };
  }
}

function estadoEnvio(ativo) {
  botaoEnviarPergunta.querySelector(".icone-enviar").hidden = ativo;
  botaoEnviarPergunta.querySelector(".icone-parar").hidden = !ativo;
  botaoEnviarPergunta.querySelector(".label-enviar").textContent = ativo ? "Parar" : "Enviar";
  botaoEnviarPergunta.setAttribute("aria-label", ativo ? "Parar resposta" : "Enviar pergunta");
  botaoEnviarPergunta.classList.toggle("parar", ativo);
  botaoAnexar.disabled = ativo || !disciplinaAtual;
}

formPergunta.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  if (controladorChat) { controladorChat.abort(); return; }
  const perguntaDigitada = inputPergunta.value.trim();
  const anexos = [...arquivosAnexados];
  if ((!perguntaDigitada && !anexos.length) || !disciplinaAtual) return;

  const pergunta = perguntaDigitada || "Analise os PDFs anexados e explique os principais conceitos.";
  const conteudoUsuario = [
    perguntaDigitada ? escaparHtml(perguntaDigitada) : "Analise os PDFs anexados e explique os principais conceitos.",
    anexos.length ? `<div class="arquivos-enviados">${anexos.map((a) => `📎 ${escaparHtml(a.name)}`).join("<br>")}</div>` : "",
  ].filter(Boolean).join("");
  adicionarMensagem("usuario", conteudoUsuario);
  inputPergunta.value = "";
  arquivosAnexados = [];
  desenharAnexos();
  menuComandos.hidden = true;
  redimensionarCompositor();

  const controle = new AbortController();
  controladorChat = controle;
  estadoEnvio(true);
  estadoCompositor.textContent = anexos.length ? "Enviando PDFs para os materiais da disciplina…" : "";
  const carregando = adicionarMensagem("bot carregando", anexos.length ? "Preparando os PDFs..." : "Pensando...");

  try {
    for (const arquivo of anexos) {
      const dados = new FormData();
      dados.append("arquivo", arquivo);
      await chamarApi(rotaDisciplina("/documentos"), { method: "POST", body: dados, signal: controle.signal });
    }
    if (anexos.length) await carregarDocumentos();
    estadoCompositor.textContent = "";
    const r = await chamarApi(rotaDisciplina("/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta }),
      signal: controle.signal,
    });
    carregando.className = "mensagem bot";
    carregando.innerHTML = formatarResposta(r.resposta, r.fontes) + rodapeModelo(r.modelo);
  } catch (erro) {
    carregando.className = "mensagem bot";
    carregando.textContent = erro.name === "AbortError" ? "Solicitação interrompida." : `Erro: ${erro.message}`;
    if (erro.name !== "AbortError") estadoCompositor.textContent = erro.message;
  } finally {
    if (controladorChat === controle) controladorChat = null;
    estadoEnvio(false);
    inputPergunta.focus();
    mensagens.scrollTop = mensagens.scrollHeight;
  }
});

botaoEnviarPergunta.addEventListener("click", (evento) => {
  if (!controladorChat) return;
  evento.preventDefault();
  controladorChat.abort();
});

// ---------------------------------------------------------- painel do professor

TELAS.assistente = { abrir() {} };  // o chat já é preparado em selecionarDisciplina()

let abaPainel = "notas";

TELAS.painel = {
  abrir() {
    $("painel-disciplina").textContent = disciplinaAtual ? disciplinaAtual.nome : "";
    if (disciplinaAtual) carregarPainel();
  },
};

for (const aba of document.querySelectorAll("#tela-painel .aba")) {
  aba.onclick = () => {
    abaPainel = aba.dataset.aba;
    document.querySelectorAll("#tela-painel .aba").forEach((a) => a.classList.toggle("ativa", a === aba));
    carregarPainel();
  };
}

async function carregarPainel() {
  const conteudo = $("painel-conteudo");
  conteudo.innerHTML = "<p class='dica'>Carregando...</p>";
  try {
    const url = `/api/professor/${abaPainel}?disciplina_id=${disciplinaAtual.id}`;
    const linhas = await chamarApi(url);
    conteudo.innerHTML = abaPainel === "notas" ? htmlNotas(linhas) : htmlPerguntas(linhas);
  } catch (erro) {
    conteudo.innerHTML = `<p class="erro">${escaparHtml(erro.message)}</p>`;
  }
}

function htmlNotas(linhas) {
  if (!linhas.length) return "<p class='dica'>Nenhum aluno fez simulados nesta disciplina ainda.</p>";

  // Média de acerto por aluno
  const porAluno = {};
  for (const l of linhas) {
    porAluno[l.aluno] ??= { acertos: 0, total: 0, simulados: 0 };
    porAluno[l.aluno].acertos += l.acertos;
    porAluno[l.aluno].total += l.total;
    porAluno[l.aluno].simulados++;
  }
  const resumo = Object.entries(porAluno)
    .sort((a, b) => a[1].acertos / a[1].total - b[1].acertos / b[1].total)  // piores primeiro
    .map(([aluno, s]) => {
      const pct = Math.round((100 * s.acertos) / s.total);
      return `<tr><td>${escaparHtml(aluno)}</td><td>${s.simulados}</td>
        <td><div class="barra"><div style="width:${pct}%"></div></div> ${pct}%</td></tr>`;
    }).join("");

  const historico = linhas.map((l) => `
    <tr><td>${escaparHtml(l.aluno)}</td><td>${escaparHtml(l.arquivo)}</td>
    <td>${l.acertos}/${l.total}</td><td>${formatarData(l.criado_em)}</td></tr>`).join("");

  return `
    <h3>Desempenho por aluno</h3>
    <table><thead><tr><th>Aluno</th><th>Simulados</th><th>Acerto médio</th></tr></thead><tbody>${resumo}</tbody></table>
    <h3>Histórico</h3>
    <table><thead><tr><th>Aluno</th><th>Material</th><th>Nota</th><th>Data</th></tr></thead><tbody>${historico}</tbody></table>`;
}

function htmlPerguntas(linhas) {
  if (!linhas.length) return "<p class='dica'>Nenhum aluno fez perguntas nesta disciplina ainda.</p>";
  return linhas.map((l) => `
    <div class="pergunta-aluno">
      <div class="meta"><strong>${escaparHtml(l.aluno)}</strong> · ${formatarData(l.criado_em)}</div>
      <p>${escaparHtml(l.pergunta)}</p>
      <details><summary>Ver resposta do assistente</summary><p>${escaparHtml(l.resposta)}</p></details>
    </div>`).join("");
}

// Espera os outros arquivos (simulados.js, calendario.js...) registrarem suas telas
document.addEventListener("DOMContentLoaded", iniciar);
