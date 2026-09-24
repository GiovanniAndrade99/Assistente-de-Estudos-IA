// Tela de login/cadastro. Se der certo, o servidor grava o cookie de sessão
// e mandamos o usuário para a página principal.

const formEntrar = document.getElementById("form-entrar");
const formCadastrar = document.getElementById("form-cadastrar");
const abas = document.querySelectorAll(".aba-login");

// Já está logado? Vai direto para o app.
fetch("/api/auth/eu").then((r) => { if (r.ok) location.href = "/"; });

// ---------------------------------------------------------- decoração do lado esquerdo

// Círculos concêntricos que "respiram"
const ondas = document.getElementById("ondas");
for (let i = 0; i < 11; i++) {
  const onda = document.createElement("span");
  onda.className = "onda";
  const tamanho = 100 + i * 70;
  onda.style.cssText = `width:${tamanho}px;height:${tamanho}px;opacity:${0.24 - i * 0.03};animation-delay:${i * 0.06}s`;
  ondas.appendChild(onda);
}

// Logos de linguagens de programação girando em órbitas de raios diferentes.
// Os SVGs vêm do Devicon (projeto de ícones de código aberto) pelo CDN jsDelivr.
const DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons";
// Raios a partir de 235px: com o título + parágrafo atual do painel, órbitas
// menores que isso cruzam o bloco de texto e os ícones ficam por cima das letras.
const ICONES = [  // atraso em segundos numa volta de 20 s: define a posição inicial na órbita
  { nome: "Python", arquivo: "python/python-original", tamanho: 34, raio: 235, atraso: 0 },
  { nome: "JavaScript", arquivo: "javascript/javascript-original", tamanho: 34, raio: 235, atraso: 10 },
  { nome: "Java", arquivo: "java/java-original", tamanho: 38, raio: 262, atraso: 5, reverso: true },
  { nome: "C", arquivo: "c/c-original", tamanho: 38, raio: 262, atraso: 15, reverso: true },
  { nome: "TypeScript", arquivo: "typescript/typescript-original", tamanho: 44, raio: 289, atraso: 2.5 },
  { nome: "C++", arquivo: "cplusplus/cplusplus-original", tamanho: 44, raio: 289, atraso: 9.2 },
  { nome: "Go", arquivo: "go/go-original-wordmark", tamanho: 44, raio: 289, atraso: 15.8 },
  { nome: "C#", arquivo: "csharp/csharp-original", tamanho: 46, raio: 316, atraso: 0.8, reverso: true },
  { nome: "Rust", arquivo: "rust/rust-original", tamanho: 46, raio: 316, atraso: 7.5, reverso: true },
  { nome: "Kotlin", arquivo: "kotlin/kotlin-original", tamanho: 46, raio: 316, atraso: 14.2, reverso: true },
  { nome: "PHP", arquivo: "php/php-original", tamanho: 46, raio: 343, atraso: 6.3 },
  { nome: "Swift", arquivo: "swift/swift-original", tamanho: 46, raio: 343, atraso: 13 },
  { nome: "Ruby", arquivo: "ruby/ruby-original", tamanho: 46, raio: 343, atraso: 19.7 },
];
const orbitas = document.getElementById("orbitas");
for (const raio of new Set(ICONES.map((i) => i.raio))) {
  const trilha = document.createElement("span");
  trilha.className = "trilha";
  trilha.style.cssText = `width:${raio * 2}px;height:${raio * 2}px`;
  orbitas.appendChild(trilha);
}
for (const i of ICONES) {
  const el = document.createElement("span");
  el.className = `icone-orbita${i.reverso ? " reverso" : ""}`;
  el.title = i.nome;
  // --angulo: posição fixa no círculo (fração da volta de 20s já percorrida pelo atraso),
  // usada como retrato estático da órbita quando a animação está desligada (prefers-reduced-motion).
  const angulo = (i.atraso / 20) * 360;
  el.style.cssText = `--tamanho:${i.tamanho}px;--raio:${i.raio};--duracao:20;--atraso:${i.atraso};--angulo:${angulo}deg`;
  const img = document.createElement("img");
  img.src = `${DEVICON}/${i.arquivo}.svg`;
  img.alt = i.nome;
  img.onerror = () => { el.textContent = i.nome; el.classList.add("sem-imagem"); };  // sem internet: mostra o nome
  el.appendChild(img);
  orbitas.appendChild(el);
}

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

// ---------------------------------------------------------- matérias (cadastro de aluno)

let materiasCatalogo = [];
fetch("/api/disciplinas/publico").then((r) => r.ok ? r.json() : []).then((d) => { materiasCatalogo = d; }).catch(() => {});

const campoMaterias = document.getElementById("campo-materias");
const listaMaterias = document.getElementById("lista-materias");
const botaoAddMateria = document.getElementById("botao-add-materia");

function idsEscolhidos(ignorarSelect) {
  return new Set(
    [...listaMaterias.querySelectorAll("select")]
      .filter((s) => s !== ignorarSelect && s.value)
      .map((s) => s.value),
  );
}

function atualizarOpcoes() {
  for (const select of listaMaterias.querySelectorAll("select")) {
    const escolhidos = idsEscolhidos(select);
    const atual = select.value;
    select.textContent = "";
    select.appendChild(new Option("Selecione uma matéria", ""));
    for (const m of materiasCatalogo) {
      if (!escolhidos.has(String(m.id))) select.appendChild(new Option(m.nome, String(m.id)));
    }
    select.value = atual;
  }
  botaoAddMateria.hidden = listaMaterias.children.length >= materiasCatalogo.length;
}

function linhaMateria() {
  const linha = document.createElement("div");
  linha.className = "linha-materia";
  const select = document.createElement("select");
  select.setAttribute("aria-label", "Matéria");
  const remover = document.createElement("button");
  remover.type = "button";
  remover.className = "botao-remover-materia";
  remover.setAttribute("aria-label", "Remover matéria");
  remover.innerHTML = "&times;";
  remover.onclick = () => { linha.remove(); atualizarOpcoes(); };
  select.onchange = atualizarOpcoes;
  linha.append(select, remover);
  return linha;
}

botaoAddMateria.onclick = () => {
  listaMaterias.appendChild(linhaMateria());
  atualizarOpcoes();
};

for (const radio of document.querySelectorAll('input[name="tipo"]')) {
  radio.addEventListener("change", () => {
    campoMaterias.hidden = document.querySelector('input[name="tipo"]:checked').value !== "aluno";
  });
}

function materiasEscolhidas() {
  return [...listaMaterias.querySelectorAll("select")].map((s) => Number(s.value)).filter(Boolean);
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

async function enviar(form, url, extra = {}) {
  limparErros(form);
  if (!validar(form)) return;
  const botao = form.querySelector("button[type=submit]");
  botao.disabled = true;
  try {
    const resposta = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...Object.fromEntries(new FormData(form)), ...extra }),
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
formCadastrar.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(formCadastrar, "/api/auth/cadastro", { disciplinas: materiasEscolhidas() });
});

// login.html#cadastrar abre direto no cadastro
mostrarForm(location.hash === "#cadastrar" ? "criar" : "entrar");
