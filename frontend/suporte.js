// Tela "Suporte": perguntas frequentes e chamados (administradores respondem).

const formChamado = $("form-chamado");
const listaChamados = $("lista-chamados");

const PERGUNTAS_FREQUENTES = [
  ["Como começo a estudar uma disciplina?",
    "Escolha a disciplina na barra lateral (ou crie uma no botão +). Depois abra o Assistente IA e envie os PDFs das aulas em \"Materiais\". Quando o envio terminar, já dá para fazer perguntas."],
  ["Por que o assistente disse que não encontrou a informação?",
    "Ele só responde com base nos PDFs da disciplina selecionada. Confira se o material certo foi enviado e se a disciplina escolhida é a correta. Reformular a pergunta com os termos usados na aula também ajuda."],
  ["O assistente pode errar?",
    "Sim. É um modelo de IA e pode interpretar mal um trecho. Clique no número da citação ([1], [2]...) para abrir o PDF na página usada, ou em \"Ver trechos usados\" abaixo da resposta, e confira no material. Veja mais na aba \"Sobre o assistente IA\"."],
  ["Meu PDF foi enviado, mas o assistente não usa o conteúdo.",
    "Depois do envio, o PDF é processado em segundo plano: acompanhe a barra na lista de materiais. PDFs escaneados passam por leitura de texto (OCR), que é mais lenta e pode errar em imagens ruins. Se aparecer erro, abra um chamado na categoria \"Problema técnico\"."],
  ["Apareceu um erro de limite ou de modelo sobrecarregado.",
    "Cada pessoa tem um limite de pedidos à IA em 24 horas (perguntas repetidas na mesma disciplina não contam, porque a resposta já guardada é reaproveitada). Além disso, a API do Gemini limita as requisições por minuto: o sistema já tenta de novo e troca para modelos reserva; se o erro continuar, espere um minuto e tente outra vez."],
  ["Como gero resumos, flashcards e simulados?",
    "Resumo e flashcards ficam nos botões de cada PDF, em \"Materiais\" (tela do Assistente IA). Simulados têm uma tela própria no menu: escolha o material e a quantidade de questões."],
  ["Como entrego uma atividade?",
    "Abra \"Atividades\" no menu, escreva a resposta na atividade e clique em entregar. A nota e o comentário aparecem ali depois que o professor corrigir."],
  ["O professor vê as minhas perguntas ao assistente?",
    "Sim. O Painel da turma mostra as perguntas dos alunos para o professor acompanhar as dúvidas da turma. Não escreva dados pessoais nas perguntas."],
  ["Como troco minha senha ou o tema?",
    "Clique no seu nome no canto inferior da barra lateral para abrir as Configurações. Lá dá para mudar nome, senha, tema claro/escuro e encerrar sessões em outros dispositivos."],
  ["Como baixo ou apago meus dados?",
    "Em Configurações › Seus dados você baixa tudo o que o sistema guarda sobre você (arquivo JSON) e pode excluir a conta. Para outros pedidos sobre seus dados, abra um chamado na categoria \"Privacidade e dados pessoais (LGPD)\": a resposta vem em até 15 dias."],
];

$("faq").innerHTML = PERGUNTAS_FREQUENTES.map(([pergunta, resposta]) => `
  <details class="item-faq">
    <summary>${escaparHtml(pergunta)}</summary>
    <p>${escaparHtml(resposta)}</p>
  </details>`).join("");

$("busca-faq").addEventListener("input", (evento) => {
  const termo = normalizarTexto(evento.target.value);
  let visiveis = 0;
  for (const item of document.querySelectorAll(".item-faq")) {
    item.hidden = !normalizarTexto(item.textContent).includes(termo);
    if (!item.hidden) visiveis++;
  }
  $("faq-vazio").hidden = visiveis > 0;
});

// Ignora maiúsculas e acentos na busca: "memoria" encontra "Memória"
function normalizarTexto(texto) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

TELAS.suporte = {
  abrir() {
    const admin = Boolean(usuario.administrador);
    $("titulo-chamados").textContent = admin ? "Chamados dos usuários" : "Meus chamados";
    formChamado.querySelector(".status").textContent = "";
    carregarCategorias();
    carregarChamados();
  },
};

// As categorias vêm do servidor (a lista do HTML é só o valor inicial)
async function carregarCategorias() {
  try {
    const { categorias } = await chamarApi("/api/suporte/categorias");
    const select = $("categoria-chamado");
    const atual = select.value;
    select.replaceChildren(...categorias.map((c) => new Option(c, c, false, c === atual)));
  } catch {
    // mantém as opções do HTML
  }
}

async function carregarChamados() {
  try {
    const chamados = await chamarApi("/api/suporte/chamados");
    listaChamados.innerHTML = chamados.length
      ? chamados.map(htmlChamado).join("")
      : `<p class="dica">Nenhum chamado ${usuario.administrador ? "aberto" : "enviado"} ainda.</p>`;
  } catch (erro) {
    listaChamados.innerHTML = `<p class="erro">${escaparHtml(erro.message)}</p>`;
  }
}

function htmlChamado(c) {
  const admin = Boolean(usuario.administrador);
  let situacao = c.resposta
    ? `<span class="etiqueta verde">Respondido</span>`
    : `<span class="etiqueta laranja">Aguardando resposta</span>`;
  // Pedido de titular (LGPD): prazo legal de resposta
  if (c.prazo_resposta && !c.resposta) {
    const prazo = new Date(`${c.prazo_resposta}T00:00:00`).toLocaleDateString("pt-BR");
    situacao += c.prazo_vencido
      ? ` <span class="etiqueta vermelha">Prazo LGPD vencido (${prazo})</span>`
      : ` <span class="etiqueta azul">Responder até ${prazo}</span>`;
  }
  const autor = admin ? `${escaparHtml(c.autor)} (${escaparHtml(c.email_autor)}) · ` : "";
  const resposta = c.resposta
    ? `<div class="resposta-suporte"><strong>Resposta do suporte</strong> · ${formatarData(c.respondido_em)}
         <p>${escaparHtml(c.resposta)}</p></div>`
    : "";
  const formResposta = admin
    ? `<form class="form-resposta-suporte" data-id="${c.id}">
         <textarea name="resposta" rows="2" required maxlength="5000" placeholder="Escreva a resposta...">${c.resposta ? escaparHtml(c.resposta) : ""}</textarea>
         <button type="submit" class="botao-secundario">${c.resposta ? "Atualizar resposta" : "Responder"}</button>
       </form>`
    : "";
  return `
    <article class="item-atividade chamado">
      <div class="item-topo">
        <h3>${escaparHtml(c.assunto)}</h3>
        <div class="linha-botoes">${situacao}
          <button type="button" class="remover" data-remover-chamado="${c.id}" title="Remover chamado" aria-label="Remover chamado">✕</button>
        </div>
      </div>
      <p class="dica">${autor}${escaparHtml(c.categoria)} · aberto em ${formatarData(c.criado_em)}</p>
      <p class="enunciado">${escaparHtml(c.mensagem)}</p>
      ${resposta}${formResposta}
    </article>`;
}

formChamado.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const status = formChamado.querySelector(".status");
  const botao = formChamado.querySelector("button[type=submit]");
  botao.disabled = true;
  try {
    await postarJson("/api/suporte/chamados", dadosDoForm(formChamado));
    formChamado.reset();
    status.textContent = "✔ Chamado enviado. A resposta aparece na lista abaixo.";
    carregarChamados();
  } catch (erro) {
    status.textContent = `✖ ${erro.message}`;
  } finally {
    botao.disabled = false;
  }
});

listaChamados.addEventListener("submit", async (evento) => {
  const form = evento.target.closest(".form-resposta-suporte");
  if (!form) return;
  evento.preventDefault();
  try {
    await chamarApi(`/api/suporte/chamados/${form.dataset.id}/resposta`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dadosDoForm(form)),
    });
    carregarChamados();
  } catch (erro) {
    alert(erro.message);
  }
});

listaChamados.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("[data-remover-chamado]");
  if (!botao || !confirm("Remover este chamado?")) return;
  try {
    await chamarApi(`/api/suporte/chamados/${botao.dataset.removerChamado}`, { method: "DELETE" });
    carregarChamados();
  } catch (erro) {
    alert(erro.message);
  }
});
