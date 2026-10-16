// "Esqueci minha senha": sem token na URL, pede o e-mail; com #t=..., pede a senha nova.
// O token fica no fragmento (#) da URL, que o navegador não envia ao servidor ao abrir a página.

const token = new URLSearchParams(location.hash.slice(1)).get("t");
const formPedir = document.getElementById("form-pedir");
const formNova = document.getElementById("form-nova-senha");

async function postar(url, corpo) {
  const resposta = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo),
  });
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(dados.detail || `Falha no servidor (HTTP ${resposta.status}).`);
  return dados;
}

function mensagens(form, erro = "", ok = "") {
  form.querySelector(".erro-geral").textContent = erro;
  form.querySelector(".ok-geral").textContent = ok;
}

if (token) {
  formPedir.hidden = true;
  formNova.hidden = false;
  history.replaceState(null, "", location.pathname);  // tira o token da barra de endereço
}
// Link aberto com esta página já aberta na mesma aba: só o # muda, então recarrega
window.addEventListener("hashchange", () => location.reload());

formPedir.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const email = formPedir.email.value.trim();
  if (!/^\S+@\S+\.\S+$/.test(email)) return mensagens(formPedir, "Informe um e-mail válido.");
  const botao = formPedir.querySelector("button");
  botao.disabled = true;
  try {
    const r = await postar("/api/auth/esqueci-senha", { email });
    mensagens(formPedir, "", r.mensagem);
  } catch (erro) {
    mensagens(formPedir, erro.message);
  } finally {
    botao.disabled = false;
  }
});

formNova.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const nova = formNova.nova_senha.value;
  if (nova.length < 10 || nova.length > 128) return mensagens(formNova, "A senha precisa ter entre 10 e 128 caracteres.");
  if (nova !== formNova.confirmar.value) return mensagens(formNova, "As duas senhas não são iguais.");
  try {
    await postar("/api/auth/redefinir-senha", { token, nova_senha: nova });
    formNova.querySelector("button").hidden = true;
    mensagens(formNova, "", "Senha alterada. Entre com a senha nova.");
    setTimeout(() => { location.href = "/login.html"; }, 1800);
  } catch (erro) {
    mensagens(formNova, erro.message);
  }
});
