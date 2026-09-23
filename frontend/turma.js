// Tela "Chat da turma": conversa entre alunos (e professor) da disciplina.
// Não usamos WebSocket: enquanto a tela está aberta, buscamos mensagens novas a cada 4 segundos.

const INTERVALO_CHAT_MS = 4000;
const caixaTurma = $("mensagens-turma");
let ultimaMensagemId = 0;
let temporizadorChat = null;

TELAS.turma = {
  abrir() {
    pararChat();
    $("turma-disciplina").textContent = disciplinaAtual ? `· ${disciplinaAtual.nome}` : "";
    if (!disciplinaAtual) return;
    caixaTurma.innerHTML = "";
    ultimaMensagemId = 0;
    buscarMensagens();
    temporizadorChat = setInterval(buscarMensagens, INTERVALO_CHAT_MS);
    $("input-turma").focus();
  },
  sair: pararChat,
};

function pararChat() {
  clearInterval(temporizadorChat);
  temporizadorChat = null;
}

async function buscarMensagens() {
  const disciplinaDaBusca = disciplinaAtual.id;
  let novas;
  try {
    novas = await chamarApi(rotaDisciplina(`/mensagens?depois=${ultimaMensagemId}`));
  } catch {
    return;  // falha passageira de rede: tenta de novo no próximo ciclo
  }
  // Ignora respostas que chegaram depois de trocar de disciplina ou de tela
  if (!temporizadorChat || disciplinaDaBusca !== disciplinaAtual.id) return;
  novas = novas.filter((m) => m.id > ultimaMensagemId);  // evita duplicar se duas buscas se cruzarem
  if (!novas.length) {
    if (!ultimaMensagemId && !caixaTurma.children.length) {
      caixaTurma.innerHTML = `<p class="dica vazio-turma">Nenhuma mensagem ainda. Diga olá para a turma! 👋</p>`;
    }
    return;
  }
  caixaTurma.querySelector(".vazio-turma")?.remove();
  const estavaNoFim = caixaTurma.scrollHeight - caixaTurma.scrollTop - caixaTurma.clientHeight < 60;
  for (const m of novas) caixaTurma.appendChild(elementoMensagem(m));
  ultimaMensagemId = novas[novas.length - 1].id;
  if (estavaNoFim || novas.some((m) => m.usuario_id === usuario.id)) caixaTurma.scrollTop = caixaTurma.scrollHeight;
}

function elementoMensagem(m) {
  const minha = m.usuario_id === usuario.id;
  const div = document.createElement("div");
  div.className = `msg-turma ${minha ? "minha" : ""}`;
  div.innerHTML = `
    ${minha ? "" : `<div class="autor">${escaparHtml(m.autor)}${m.tipo === "professor" ? ` <span class="selo professor">Professor</span>` : ""}</div>`}
    <div class="texto">${escaparHtml(m.texto)}</div>
    <div class="hora">${formatarData(m.criado_em)}</div>`;
  return div;
}

$("form-turma").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const input = $("input-turma");
  const texto = input.value.trim();
  if (!texto) return;
  input.value = "";
  try {
    await postarJson(rotaDisciplina("/mensagens"), { texto });
    buscarMensagens();
  } catch (erro) {
    input.value = texto;
    alert(erro.message);
  }
});
