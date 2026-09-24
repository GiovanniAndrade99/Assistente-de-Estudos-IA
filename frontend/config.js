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
