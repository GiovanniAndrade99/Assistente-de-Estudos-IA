// Tela "Videoaulas": o professor cadastra links; vídeos do YouTube tocam na própria página.

TELAS.videos = {
  abrir() {
    if (disciplinaAtual) carregarVideos();
  },
};

// Aceita youtube.com/watch?v=ID, youtu.be/ID, /embed/ID e /shorts/ID
function idDoYoutube(url) {
  const m = url.match(/(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/);
  return m ? m[1] : null;
}

async function carregarVideos() {
  const lista = $("lista-videos");
  const videos = await chamarApi(rotaDisciplina("/videos"));
  if (!videos.length) {
    lista.innerHTML = `<p class="dica">Nenhuma videoaula cadastrada${usuario.tipo === "professor" ? "" : " pelo professor"} ainda.</p>`;
    return;
  }
  lista.innerHTML = "";
  for (const v of videos) {
    const id = idDoYoutube(v.url);
    const cartao = document.createElement("article");
    cartao.className = "cartao-video";
    cartao.innerHTML = `
      ${id
        ? `<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/${id}" title="${escaparHtml(v.titulo)}"
             loading="lazy" allowfullscreen
             allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe></div>`
        : `<a class="video link-externo" href="${escaparHtml(v.url)}" target="_blank" rel="noopener">▶ Abrir vídeo</a>`}
      <div class="info">
        <div class="item-topo">
          <h3>${escaparHtml(v.titulo)}</h3>
          ${usuario.tipo === "professor" ? `<button type="button" class="remover" title="Remover">✕</button>` : ""}
        </div>
        ${v.descricao ? `<p>${escaparHtml(v.descricao)}</p>` : ""}
        <small class="dica">por ${escaparHtml(v.adicionado_por)} · ${formatarData(v.criado_em)}</small>
      </div>`;
    const remover = cartao.querySelector(".remover");
    if (remover) remover.onclick = async () => {
      if (!confirm(`Remover a videoaula "${v.titulo}"?`)) return;
      await chamarApi(rotaDisciplina(`/videos/${v.id}`), { method: "DELETE" });
      carregarVideos();
    };
    lista.appendChild(cartao);
  }
}

$("form-video").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  try {
    await postarJson(rotaDisciplina("/videos"), dadosDoForm(form));
    form.reset();
    carregarVideos();
  } catch (erro) {
    alert(erro.message);
  }
});
