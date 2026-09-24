// Tela de login/cadastro. Se der certo, o servidor grava o cookie de sessão
// e mandamos o usuário para a página principal.

const formEntrar = document.getElementById("form-entrar");
const formCadastrar = document.getElementById("form-cadastrar");
const abas = document.querySelectorAll(".aba-login");

// Já está logado? Vai direto para o app.
fetch("/api/auth/eu").then((r) => { if (r.ok) location.href = "/"; });

// ---------------------------------------------------------- alternância de abas

function limparErros(form) {
  form.querySelectorAll(".erro-campo, .erro-geral").forEach((p) => (p.textContent = ""));
}

function mostrarForm(nome) {
  formEntrar.hidden = nome !== "entrar";
  formCadastrar.hidden = nome !== "criar";
  for (const aba of abas) {
    const ativa = aba.dataset.aba === nome;
    aba.classList.toggle("ativa", ativa);
    aba.setAttribute("aria-selected", String(ativa));
  }
  const form = nome === "entrar" ? formEntrar : formCadastrar;
  limparErros(form);
  form.querySelector("input").focus({ preventScroll: true });
}

for (const aba of abas) {
  aba.addEventListener("click", () => mostrarForm(aba.dataset.aba));
}

// ---------------------------------------------------------- mostrar/ocultar senha

const OLHO_ABERTO = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>`;
const OLHO_FECHADO = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/></svg>`;
for (const olho of document.querySelectorAll(".olho")) {
  const input = olho.previousElementSibling;
  olho.innerHTML = OLHO_FECHADO;
  olho.onclick = () => {
    const mostrar = input.type === "password";
    input.type = mostrar ? "text" : "password";
    olho.innerHTML = mostrar ? OLHO_ABERTO : OLHO_FECHADO;
    olho.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
  };
}

// ---------------------------------------------------------- validação e envio

function validar(form) {
  let valido = true;
  for (const input of form.querySelectorAll("input[data-rotulo]")) {
    const valor = input.value.trim();
    let erro = "";
    if (!valor) erro = `${input.dataset.rotulo} é obrigatório.`;
    else if (input.type === "email" && !/^\S+@\S+\.\S+$/.test(valor)) erro = "E-mail inválido.";
    else if (input.name === "senha" && input.value.length < 6) erro = "A senha precisa ter pelo menos 6 caracteres.";
    input.closest(".campo").querySelector(".erro-campo").textContent = erro;
    if (erro && valido) input.focus();
    valido &&= !erro;
  }
  return valido;
}

async function enviar(form, url) {
  limparErros(form);
  if (!validar(form)) return;
  const botao = form.querySelector("button[type=submit]");
  botao.disabled = true;
  try {
    const resposta = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    // Leia como texto primeiro: se o servidor retornar HTML (por exemplo,
    // quando o frontend foi aberto sem o FastAPI) o erro de JSON original
    // era pouco informativo e escondia a resposta recebida.
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
        : dados.detail || dados.message || dados.error;
      throw new Error(detalhe || `Falha no servidor (HTTP ${resposta.status} em ${resposta.url}): ${JSON.stringify(dados)}`);
    }
    location.href = "/";
  } catch (e) {
    form.querySelector(".erro-geral").textContent = e.message;
  } finally {
    botao.disabled = false;
  }
}

formEntrar.addEventListener("submit", (e) => { e.preventDefault(); enviar(formEntrar, "/api/auth/login"); });
formCadastrar.addEventListener("submit", (e) => { e.preventDefault(); enviar(formCadastrar, "/api/auth/cadastro"); });

// login.html#cadastrar abre direto no cadastro
mostrarForm(location.hash === "#cadastrar" ? "criar" : "entrar");
