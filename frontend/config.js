// Tela "Configurações": perfil, senha, tema e sessões.

const formPerfil = $("form-perfil");
const formSenha = $("form-senha");

TELAS.config = {
  abrir() {
    formPerfil.nome.value = usuario.nome;
    formPerfil.email.value = usuario.email;
    formPerfil.tipo.value = usuario.administrador ? "Administrador" : usuario.tipo === "professor" ? "Professor" : "Aluno";
    const tema = document.documentElement.dataset.tema || "claro";
    for (const radio of document.querySelectorAll("input[name=tema]")) radio.checked = radio.value === tema;
    for (const status of document.querySelectorAll("#tela-config .status")) status.textContent = "";
    if (usuario.administrador) carregarSemProfessor();
    $("situacao-email").textContent = `E-mail atual: ${usuario.email}${usuario.email_verificado ? " (confirmado)" : ", ainda não confirmado"}. A troca só vale depois de confirmada no endereço novo.`;
    $("reenviar-verificacao").hidden = Boolean(usuario.email_verificado);
  },
};

formPerfil.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const status = formPerfil.querySelector(".status");
  try {
    usuario = await chamarApi("/api/auth/perfil", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: formPerfil.nome.value }),
    });
    mostrarUsuario();
    status.textContent = "✔ Perfil atualizado.";
  } catch (erro) {
    status.textContent = `✖ ${erro.message}`;
  }
});

formSenha.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const status = formSenha.querySelector(".status");
  const { senha_atual, nova_senha, confirmar } = dadosDoForm(formSenha);
  if (nova_senha !== confirmar) {
    status.textContent = "✖ A confirmação não confere com a nova senha.";
    return;
  }
  try {
    await postarJson("/api/auth/senha", { senha_atual, nova_senha });
    formSenha.reset();
    status.textContent = "✔ Senha alterada. Suas outras sessões foram encerradas.";
  } catch (erro) {
    status.textContent = `✖ ${erro.message}`;
  }
});

for (const radio of document.querySelectorAll("input[name=tema]")) {
  radio.onchange = () => {
    document.documentElement.dataset.tema = radio.value;
    try { localStorage.setItem("tema", radio.value); } catch {}
  };
}

$("botao-encerrar-sessoes").onclick = async () => {
  try {
    await postarJson("/api/auth/encerrar-outras-sessoes", {});
    $("status-sessoes").textContent = "✔ Outras sessões encerradas.";
  } catch (erro) {
    $("status-sessoes").textContent = `✖ ${erro.message}`;
  }
};

$("abrir-aviso-cookies").onclick = () => window.mostrarAvisoCookies?.();

// ---------------------------------------------------------- seus dados (LGPD)

$("form-excluir-conta").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const { senha, confirmacao } = dadosDoForm(form);
  try {
    await excluirConta(senha, confirmacao);
  } catch (erro) {
    form.querySelector(".status").textContent = `✖ ${erro.message}`;
  }
});

// ---------------------------------------------------------- admin: disciplinas sem professor

async function carregarSemProfessor() {
  const lista = $("lista-sem-professor");
  const disciplinas = await chamarApi("/api/admin/disciplinas-sem-professor");
  if (!disciplinas.length) {
    lista.innerHTML = `<li class="dica">Nenhuma no momento.</li>`;
    return;
  }
  lista.innerHTML = "";
  for (const d of disciplinas) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span><strong>${escaparHtml(d.nome)}</strong> · ${d.alunos} aluno(s)</span>
      <form class="linha-transferir">
        <input type="email" name="email_professor" placeholder="e-mail do novo professor" required maxlength="254">
        <button type="submit" class="botao-secundario">Transferir</button>
      </form>`;
    item.querySelector("form").onsubmit = async (evento) => {
      evento.preventDefault();
      try {
        const r = await chamarApi(`/api/admin/disciplinas/${d.id}/professor`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dadosDoForm(evento.target)),
        });
        $("status-sem-professor").textContent = `✔ ${d.nome} agora é de ${r.professor}.`;
        carregarSemProfessor();
      } catch (erro) {
        $("status-sem-professor").textContent = `✖ ${erro.message}`;
      }
    };
    lista.appendChild(item);
  }
}

$("form-trocar-email").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const status = form.querySelector(".status");
  try {
    const r = await chamarApi("/api/conta/email", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dadosDoForm(form)),
    });
    form.reset();
    status.textContent = `✔ ${r.mensagem}`;
  } catch (erro) {
    status.textContent = `✖ ${erro.message}`;
  }
});

$("reenviar-verificacao").onclick = async () => {
  const status = $("form-trocar-email").querySelector(".status");
  try {
    await postarJson("/api/auth/reenviar-verificacao", {});
    status.textContent = "✔ Enviamos um novo link de confirmação para o seu e-mail.";
  } catch (erro) {
    status.textContent = `✖ ${erro.message}`;
  }
};
