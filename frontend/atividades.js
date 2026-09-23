// Tela "Atividades": o professor publica e corrige; o aluno entrega a resposta.

const ehProfessor = () => usuario.tipo === "professor";

TELAS.atividades = {
  abrir() {
    if (disciplinaAtual) carregarAtividades();
  },
};

$("form-atividade").prazo.min = hojeIso();

$("form-atividade").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  try {
    await postarJson(rotaDisciplina("/atividades"), dadosDoForm(form));
    form.reset();
    carregarAtividades();
  } catch (erro) {
    alert(erro.message);
  }
});

function situacaoDaAtividade(a) {
  const atrasada = hojeIso() > a.prazo;
  if (ehProfessor()) {
    return atrasada ? `<span class="etiqueta cinza">Encerrada</span>` : `<span class="etiqueta azul">Aberta</span>`;
  }
  if (a.nota !== null) return `<span class="etiqueta verde">Corrigida · nota ${a.nota}</span>`;
  if (a.entregue_em) return `<span class="etiqueta azul">Entregue</span>`;
  return atrasada ? `<span class="etiqueta vermelha">Atrasada</span>` : `<span class="etiqueta laranja">Pendente</span>`;
}

async function carregarAtividades() {
  const lista = $("lista-atividades");
  const atividades = await chamarApi(rotaDisciplina("/atividades"));
  if (!atividades.length) {
    lista.innerHTML = `<p class="dica">${ehProfessor()
      ? "Nenhuma atividade publicada. Use o formulário acima para criar a primeira."
      : "Nenhuma atividade publicada pelo professor ainda."}</p>`;
    return;
  }
  lista.innerHTML = "";
  for (const a of atividades) {
    const item = document.createElement("article");
    item.className = "item-atividade";
    item.innerHTML = `
      <div class="item-topo">
        <h3>${escaparHtml(a.titulo)}</h3>
        ${situacaoDaAtividade(a)}
      </div>
      <p class="dica">Prazo: <strong>${formatarDia(a.prazo)}</strong> · por ${escaparHtml(a.professor)}</p>
      ${a.descricao ? `<div class="enunciado">${escaparHtml(a.descricao)}</div>` : ""}
      <div class="item-acoes"></div>`;
    const acoes = item.querySelector(".item-acoes");
    if (ehProfessor()) montarAcoesProfessor(acoes, a);
    else montarEntregaAluno(acoes, a);
    lista.appendChild(item);
  }
}

// ---------------------------------------------------------- aluno

function montarEntregaAluno(acoes, a) {
  if (a.nota !== null) {
    acoes.innerHTML = `
      <p><strong>Sua resposta:</strong></p><div class="enunciado">${escaparHtml(a.resposta)}</div>
      ${a.comentario ? `<p><strong>Comentário do professor:</strong> ${escaparHtml(a.comentario)}</p>` : ""}`;
    return;
  }
  acoes.innerHTML = `
    <form class="form-entrega">
      <textarea name="resposta" rows="4" required maxlength="10000"
        placeholder="Escreva sua resposta...">${escaparHtml(a.resposta || "")}</textarea>
      <div class="linha-botoes">
        <button type="submit" class="botao-primario">${a.entregue_em ? "Reenviar" : "Entregar"}</button>
        ${a.entregue_em ? `<small class="dica">Entregue em ${formatarData(a.entregue_em)}</small>` : ""}
      </div>
    </form>`;
  acoes.querySelector("form").onsubmit = async (evento) => {
    evento.preventDefault();
    try {
      await postarJson(rotaDisciplina(`/atividades/${a.id}/entrega`), dadosDoForm(evento.target));
      carregarAtividades();
    } catch (erro) {
      alert(erro.message);
    }
  };
}

// ---------------------------------------------------------- professor

function montarAcoesProfessor(acoes, a) {
  acoes.innerHTML = `
    <div class="linha-botoes">
      <button type="button" class="botao-secundario ver">📥 Ver entregas (${a.total_entregas})</button>
      <button type="button" class="link-perigo remover">Remover atividade</button>
    </div>
    <div class="entregas" hidden></div>`;
  const entregas = acoes.querySelector(".entregas");
  acoes.querySelector(".ver").onclick = () => {
    entregas.hidden = !entregas.hidden;
    if (!entregas.hidden) carregarEntregas(entregas, a);
  };
  acoes.querySelector(".remover").onclick = async () => {
    if (!confirm(`Remover a atividade "${a.titulo}" e todas as entregas?`)) return;
    await chamarApi(rotaDisciplina(`/atividades/${a.id}`), { method: "DELETE" });
    carregarAtividades();
  };
}

async function carregarEntregas(caixa, a) {
  caixa.innerHTML = "<p class='dica'>Carregando...</p>";
  const entregas = await chamarApi(rotaDisciplina(`/atividades/${a.id}/entregas`));
  if (!entregas.length) {
    caixa.innerHTML = "<p class='dica'>Nenhum aluno entregou ainda.</p>";
    return;
  }
  caixa.innerHTML = "";
  for (const e of entregas) {
    const bloco = document.createElement("form");
    bloco.className = "entrega";
    bloco.innerHTML = `
      <div class="meta"><strong>${escaparHtml(e.aluno)}</strong> · ${formatarData(e.criado_em)}</div>
      <div class="enunciado">${escaparHtml(e.resposta)}</div>
      <div class="linha-correcao">
        <label>Nota <input type="number" name="nota" min="0" max="10" step="0.1" required value="${e.nota ?? ""}"></label>
        <input type="text" name="comentario" placeholder="Comentário para o aluno (opcional)"
          value="${escaparHtml(e.comentario || "")}" maxlength="2000">
        <button type="submit" class="botao-primario">${e.nota === null ? "Corrigir" : "Atualizar"}</button>
      </div>`;
    bloco.onsubmit = async (evento) => {
      evento.preventDefault();
      const dados = dadosDoForm(bloco);
      try {
        await chamarApi(rotaDisciplina(`/atividades/${a.id}/entregas/${e.id}`), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nota: Number(dados.nota), comentario: dados.comentario }),
        });
        bloco.querySelector("button").textContent = "✔ Salvo";
      } catch (erro) {
        alert(erro.message);
      }
    };
    caixa.appendChild(bloco);
  }
}
