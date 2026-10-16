// Abre o link do e-mail (#t=...): confirma o e-mail da conta ou conclui uma troca de e-mail.

const resultado = document.getElementById("resultado-email");
const token = new URLSearchParams(location.hash.slice(1)).get("t");
history.replaceState(null, "", location.pathname);  // tira o token da barra de endereço

async function confirmar() {
  if (!token) {
    resultado.textContent = "Link incompleto. Abra de novo o link do e-mail.";
    return;
  }
  try {
    const resposta = await fetch("/api/auth/confirmar-email", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    });
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw new Error(dados.detail || "Não foi possível confirmar.");
    resultado.textContent = dados.resultado === "trocado"
      ? "Pronto: o e-mail da sua conta foi trocado. Use o novo endereço para entrar."
      : "Pronto: seu e-mail está confirmado.";
  } catch (erro) {
    resultado.textContent = erro.message;
  }
}

confirmar();
