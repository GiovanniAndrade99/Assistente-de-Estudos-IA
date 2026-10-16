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
  return lerRespostaJson(await fetch(url, opcoes));
}

async function lerRespostaJson(resposta) {
  if (resposta.status === 401) {  // sessão expirou ou não fez login
    location.href = "/login.html";
    throw new Error("Faça login para continuar.");
  }
  // O aviso de privacidade mudou durante a sessão: recarrega para pedir a confirmação
  if (resposta.status === 403 && resposta.headers.get("X-Acao-Necessaria") === "ciencia-privacidade") {
    location.reload();
    throw new Error("Confirme o aviso de privacidade para continuar.");
  }
  const texto = await resposta.text();
  let dados = {};
  try {
    dados = texto ? JSON.parse(texto) : {};
  } catch {
    const trecho = texto.replace(/\s+/g, " ").slice(0, 180);
    throw new Error(`Resposta inválida do servidor (HTTP ${resposta.status}). ${trecho || "Confira se o backend está em execução."}`);
  }
  if (!resposta.ok) {
    const detalhe = Array.isArray(dados.detail)
      ? dados.detail.map((item) => item.msg).filter(Boolean).join(" ")
      : dados.detail;
    throw new Error(detalhe || "Erro no servidor");
  }
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

// A política de conteúdo (CSP) não aceita o atributo style no HTML. Larguras e atrasos
// calculados vêm em data-largura / data-atraso e são aplicados aqui via CSSOM, que a
// CSP permite, para qualquer elemento inserido na página.
function aplicarEstilosDinamicos(raiz) {
  for (const el of [raiz, ...raiz.querySelectorAll("[data-largura], [data-atraso]")]) {
    if (el.dataset.largura !== undefined) el.style.width = `${el.dataset.largura}%`;
    if (el.dataset.atraso !== undefined) el.style.setProperty("--atraso", el.dataset.atraso);
  }
}
new MutationObserver((mudancas) => {
  for (const m of mudancas) for (const no of m.addedNodes) if (no.nodeType === 1) aplicarEstilosDinamicos(no);
}).observe(document.documentElement, { childList: true, subtree: true });

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
  if (!TELAS[nome] || (nome === "painel" && usuario.tipo !== "professor")
      || (nome === "metricas" && !usuario.administrador)) nome = "assistente";
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

async function excluirConta(senha, confirmacao) {
  await chamarApi("/api/conta", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ senha, confirmacao }),
  });
  location.href = "/login.html#conta-excluida";
}

// Contas antigas (ou aviso de privacidade atualizado): pede a ciência do aviso e a
// declaração de idade mínima antes de carregar qualquer dado das disciplinas.
function pedirCiencia() {
  const modal = $("modal-ciencia");
  const form = $("form-ciencia");
  const status = form.querySelector(".status");
  $("botao-menor-18").onclick = () => { $("texto-menor-18").hidden = false; };
  $("botao-excluir-menor").onclick = () => { $("excluir-menor").hidden = false; $("senha-excluir-menor").focus(); };
  $("confirmar-excluir-menor").onclick = async () => {
    const status = $("excluir-menor").querySelector(".status");
    try {
      await excluirConta($("senha-excluir-menor").value, "EXCLUIR");
    } catch (erro) {
      status.textContent = `✖ ${erro.message}`;
    }
  };
  $("botao-sair-menor").onclick = async () => {
    await postarJson("/api/auth/logout", {});
    location.href = "/login.html";
  };
  modal.addEventListener("cancel", (e) => e.preventDefault());  // Esc não fecha: a confirmação é obrigatória
  modal.showModal();
  return new Promise((resolver) => {
    form.onsubmit = async (evento) => {
      evento.preventDefault();
      status.textContent = "";
      try {
        await postarJson("/api/conta/ciencia-privacidade", {
          aceite_privacidade: form.aceite_privacidade.checked,
          declara_maioridade: form.declara_maioridade.checked,
        });
        modal.close();
        resolver();
      } catch (erro) {
        status.textContent = `✖ ${erro.message}`;
      }
    };
  });
}

async function iniciar() {
  usuario = await chamarApi("/api/auth/eu");
  if (usuario.ciencia_pendente) {
    await pedirCiencia();
    usuario = await chamarApi("/api/auth/eu");
  }
  mostrarUsuario();
  $("tipo-usuario").classList.add(usuario.tipo);
  for (const el of document.querySelectorAll("[data-so-professor]")) el.hidden = usuario.tipo !== "professor" && !usuario.administrador;
  for (const el of document.querySelectorAll("[data-so-admin]")) el.hidden = !usuario.administrador;
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
  const gerencia = temDisciplina && podeGerenciar(disciplina);
  $("botao-remover-disciplina").hidden = !gerencia;
  inputPergunta.disabled = !temDisciplina;
  botaoEnviarPergunta.disabled = !temDisciplina;
  botaoAnexar.disabled = !temDisciplina;
  // Enviar, anexar e remover PDFs: só quem gerencia a disciplina (o servidor também confere)
  botaoAnexar.hidden = !gerencia;
  for (const el of document.querySelectorAll(".botao-upload, .aviso-upload")) el.hidden = !gerencia;
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

function podeGerenciar(disciplina) {
  return Boolean(usuario.administrador) || disciplina.criado_por === usuario.id;
}

// Enquanto houver PDF sendo processado, a lista se atualiza sozinha
let temporizadorDocumentos = null;

function situacaoDoDocumento(doc) {
  if (doc.status === "processando") {
    return `<div class="progresso-doc" role="progressbar" aria-valuenow="${doc.progresso}" aria-valuemin="0"
      aria-valuemax="100" aria-label="Processando o PDF"><div data-largura="${doc.progresso}"></div></div>
      <small>Processando… ${doc.progresso}%</small>`;
  }
  if (doc.status === "erro") return `<small class="erro">✖ ${escaparHtml(doc.erro || "Falha ao processar.")}</small>`;
  const alerta = doc.alerta_instrucoes && podeGerenciar(disciplinaAtual)
    ? `<small class="alerta-doc" title="Trechos do PDF parecem instruções para a IA. Ela foi orientada a ignorá-las, mas confira o arquivo.">⚠ Contém frases que parecem comandos para a IA</small>`
    : "";
  return `<small>${doc.trechos} trechos · enviado por ${escaparHtml(doc.enviado_por)}</small>${alerta}`;
}

async function carregarDocumentos() {
  clearTimeout(temporizadorDocumentos);
  const disciplinaDaBusca = disciplinaAtual.id;
  const docs = await chamarApi(rotaDisciplina("/documentos"));
  if (!disciplinaAtual || disciplinaAtual.id !== disciplinaDaBusca) return;
  listaDocumentos.innerHTML = docs.length
    ? ""
    : "<li><small>Nenhum material enviado.</small></li>";
  const gerencia = podeGerenciar(disciplinaAtual);

  for (const doc of docs) {
    const li = document.createElement("li");
    const pronto = doc.status === "pronto";
    li.innerHTML = `
      <div class="doc-topo">
        <span class="nome" title="${escaparHtml(doc.arquivo)}">📄 ${escaparHtml(doc.arquivo)}</span>
        ${gerencia ? `<button class="remover" title="Remover">✕</button>` : ""}
      </div>
      ${situacaoDoDocumento(doc)}
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
    const remover = li.querySelector(".remover");
    if (remover) remover.onclick = async () => {
      if (!confirm(`Remover ${doc.arquivo}?`)) return;
      await chamarApi(rotaDisciplina(`/documentos/${encodeURIComponent(doc.arquivo)}`), { method: "DELETE" });
      carregarDocumentos();
    };
    for (const botao of li.querySelectorAll(".acoes button")) {
      botao.disabled = !pronto;
      botao.onclick = () => executarAcao(botao.dataset.acao, doc.arquivo);
    }
    listaDocumentos.appendChild(li);
  }
  if (docs.some((d) => d.status === "processando")) {
    temporizadorDocumentos = setTimeout(() => carregarDocumentos().catch(() => {}), 2000);
  }
  return docs;
}

// Espera os PDFs enviados terminarem de processar (usado pelos anexos do chat)
async function esperarDocumentosProntos(nomes, aoAtualizar) {
  for (let tentativa = 0; tentativa < 300; tentativa++) {
    const docs = await chamarApi(rotaDisciplina("/documentos"));
    const meus = docs.filter((d) => nomes.includes(d.arquivo));
    const processando = meus.filter((d) => d.status === "processando");
    const comErro = meus.filter((d) => d.status === "erro");
    if (comErro.length) throw new Error(`${comErro[0].arquivo}: ${comErro[0].erro}`);
    if (meus.length === nomes.length && !processando.length) return;
    if (aoAtualizar && processando.length) aoAtualizar(Math.min(...processando.map((d) => d.progresso)));
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("O processamento do PDF está demorando. Pergunte de novo daqui a pouco.");
}

inputPdf.addEventListener("change", async () => {
  for (const arquivo of inputPdf.files) {
    statusUpload.textContent = `Enviando ${arquivo.name}...`;
    const dados = new FormData();
    dados.append("arquivo", arquivo);
    try {
      const r = await chamarApi(rotaDisciplina("/documentos"), { method: "POST", body: dados });
      statusUpload.textContent = `✔ ${r.arquivo} enviado; o processamento aparece na lista abaixo.`;
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
  // Baralho pessoal com revisão espaçada (trilha.js)
  const salvar = document.createElement("button");
  salvar.type = "button";
  salvar.className = "botao-secundario";
  salvar.textContent = "Salvar no meu baralho";
  salvar.onclick = () => salvarNoBaralho(r.arquivo, r.flashcards, salvar);
  caixa.appendChild(salvar);
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

  // A correção é feita pelo servidor: o navegador não recebe o gabarito antes
  caixa.querySelector(".corrigir").onclick = async (evento) => {
    const botao = evento.target;
    const respostas = r.questoes.map((_, i) => {
      const marcada = caixa.querySelector(`.questao[data-indice="${i}"] input:checked`);
      return marcada ? Number(marcada.value) : null;
    });
    botao.disabled = true;
    let resultado;
    try {
      resultado = await postarJson(rotaDisciplina(`/simulados/${r.simulado_id}/respostas`), { respostas });
    } catch (erro) {
      caixa.querySelector(".nota").textContent = `Erro: ${erro.message}`;
      botao.disabled = false;
      return;
    }
    resultado.correcao.forEach((c, i) => {
      const bloco = caixa.querySelector(`.questao[data-indice="${i}"]`);
      const labels = bloco.querySelectorAll(".alternativa");
      labels[c.correta].classList.add("certa");
      if (c.marcada !== null && !c.acertou) labels[c.marcada].classList.add("errada");
      bloco.querySelectorAll("input").forEach((inp) => (inp.disabled = true));
      const exp = bloco.querySelector(".explicacao");
      exp.textContent = `${c.explicacao} (p. ${c.pagina})`;
      exp.hidden = false;
    });
    caixa.querySelector(".nota").textContent = `Você acertou ${resultado.acertos} de ${resultado.total}.`;
    botao.remove();
    if (telaAtual === "simulados") carregarHistoricoSimulados();
  };
}

// ---------------------------------------------------------- chat

// PDF da fonte aberto na página citada (leitor de PDF do navegador, em outra aba)
function linkDaFonte(f) {
  return f.documento_id ? rotaDisciplina(`/documentos/${f.documento_id}/arquivo#page=${Number(f.pagina) || 1}`) : "";
}

function formatarTexto(texto, fontes) {
  // Transforma [1], [2]... em etiquetas com arquivo/página que abrem o PDF na página
  return escaparHtml(texto)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\[(\d+)\]/g, (original, n) => {
      const f = fontes[n - 1];
      if (!f) return original;
      const titulo = `${escaparHtml(f.arquivo)} — pág. ${f.pagina}`;
      const link = linkDaFonte(f);
      return link
        ? `<a class="citacao" href="${escaparHtml(link)}" target="_blank" rel="noopener" title="Abrir ${titulo}">${n}</a>`
        : `<span class="citacao" title="${titulo}">${n}</span>`;
    });
}

function formatarResposta(texto, fontes) {
  let html = formatarTexto(texto, fontes);
  if (fontes.length) {
    const itens = fontes.map((f, i) => {
      const link = linkDaFonte(f);
      const origem = `${escaparHtml(f.arquivo)}, pág. ${f.pagina}`;
      return `
      <div class="fonte">
        <strong>[${i + 1}]</strong> ${link ? `<a href="${escaparHtml(link)}" target="_blank" rel="noopener">${origem}</a>` : origem}
        <small>(similaridade ${f.similaridade})</small><br>
        ${escaparHtml(f.texto.slice(0, 300))}${f.texto.length > 300 ? "..." : ""}
      </div>`;
    }).join("");
    html += `<details class="fontes"><summary>Ver trechos usados (${fontes.length})</summary>${itens}</details>`;
  }
  return html;
}

// Pergunta com a resposta em streaming: o texto aparece enquanto o Gemini escreve.
// Eventos do servidor (SSE): fontes, texto (pedaços), fim ou erro.
class SemStream extends Error {}

async function perguntarEmStream(pergunta, balao, signal) {
  if (!window.ReadableStream || !window.TextDecoderStream) throw new SemStream();
  let resposta;
  try {
    resposta = await fetch(rotaDisciplina("/chat/stream"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta }),
      signal,
    });
  } catch (erro) {
    if (erro.name === "AbortError") throw erro;
    throw new SemStream();  // falha de rede/proxy: tenta a rota normal
  }
  const tipo = resposta.headers.get("Content-Type") || "";
  if (!resposta.ok || !tipo.startsWith("text/event-stream")) {
    await lerRespostaJson(resposta);  // 400, 403, 429...: mostra a mensagem do servidor
    throw new SemStream();
  }

  const leitor = resposta.body.pipeThrough(new TextDecoderStream()).getReader();
  let pendente = "", texto = "", fontes = [], fim = null;
  while (!fim) {
    const { value, done } = await leitor.read();
    if (done) break;
    pendente += value;
    let corte;
    while ((corte = pendente.indexOf("\n\n")) >= 0) {
      const bloco = pendente.slice(0, corte);
      pendente = pendente.slice(corte + 2);
      const evento = /^event: (.*)$/m.exec(bloco)?.[1];
      const dados = JSON.parse(/^data: (.*)$/m.exec(bloco)?.[1] ?? "null");
      if (evento === "fontes") fontes = dados;
      else if (evento === "erro") throw new Error(dados);
      else if (evento === "fim") fim = dados;
      else if (evento === "texto") {
        const noFim = mensagens.scrollHeight - mensagens.scrollTop - mensagens.clientHeight < 60;
        texto += dados;
        balao.className = "mensagem bot escrevendo";
        balao.innerHTML = formatarTexto(texto, fontes);
        if (noFim) mensagens.scrollTop = mensagens.scrollHeight;
      }
    }
  }
  if (!fim) throw new Error("A resposta foi interrompida. Tente de novo.");
  return { resposta: fim.resposta, fontes, modelo: fim.modelo };
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
    if (anexos.length) {
      carregarDocumentos();
      await esperarDocumentosProntos(anexos.map((a) => a.name), (pct) => {
        estadoCompositor.textContent = `Processando os PDFs… ${pct}%`;
      });
      carregarDocumentos();
    }
    estadoCompositor.textContent = "";
    let r;
    try {
      r = await perguntarEmStream(pergunta, carregando, controle.signal);
    } catch (erro) {
      if (!(erro instanceof SemStream)) throw erro;
      r = await chamarApi(rotaDisciplina("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pergunta }),
        signal: controle.signal,
      });
    }
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
        <td><div class="barra"><div data-largura="${pct}"></div></div> ${pct}%</td></tr>`;
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
