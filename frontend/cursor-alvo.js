// Cursor de mira na tela "Minhas disciplinas": adaptação em JS puro do TargetCursor
// (React Bits), sem React nem GSAP. Fora da tela, e em telas de toque, o cursor é o normal.
// Os cantos giram em volta do ponteiro e, sobre um alvo, se abrem para enquadrá-lo.

const ALVOS_CURSOR = [
  ".cartao-disciplina .botao-icone", ".linha-atividade", ".lista-aulas label", ".lista-aulas summary",
  ".filtro", ".campo-busca", ".estatistica", ".cartao-disciplina",
].join(", ");
const BORDA_CANTO = 3;
const TAMANHO_CANTO = 12;
const VOLTA_SEGUNDOS = 2;
// Posição de descanso de cada canto (sup. esq., sup. dir., inf. dir., inf. esq.) em volta do ponteiro
const CANTOS_DESCANSO = [[-18, -18], [6, -18], [6, 6], [-18, 6]];

(function iniciarCursorAlvo() {
  const tela = $("tela-disciplinas");
  const semMouse = !matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (!tela || semMouse) return;
  const semMovimento = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const cursor = document.createElement("div");
  cursor.className = "cursor-alvo";
  cursor.setAttribute("aria-hidden", "true");
  cursor.innerHTML = `<div class="cursor-alvo-ponto"></div>${'<div class="cursor-alvo-canto"></div>'.repeat(4)}`;
  document.body.appendChild(cursor);
  const ponto = cursor.querySelector(".cursor-alvo-ponto");
  const cantos = [...cursor.querySelectorAll(".cursor-alvo-canto")];

  const mouse = { x: innerWidth / 2, y: innerHeight / 2 };
  const pos = { ...mouse };
  const posCantos = CANTOS_DESCANSO.map(([x, y]) => ({ x, y }));
  let rotacao = 0;
  let alvo = null;
  let dentro = false;
  let quadro = null;
  let ultimoTempo = 0;

  function ativar() {
    dentro = true;
    tela.classList.add("com-cursor-alvo");
    cursor.classList.add("visivel");
    if (!quadro) {
      ultimoTempo = performance.now();
      quadro = requestAnimationFrame(animar);
    }
  }

  function desativar() {
    dentro = false;
    alvo = null;
    tela.classList.remove("com-cursor-alvo");
    cursor.classList.remove("visivel");
  }

  function escolherAlvo(elemento) {
    const novo = elemento?.closest(ALVOS_CURSOR);
    alvo = novo && tela.contains(novo) ? novo : null;
    cursor.classList.toggle("no-alvo", Boolean(alvo));
  }

  // Aproxima "atual" de "destino" de forma suave e independente da taxa de quadros
  const suavizar = (atual, destino, velocidade, dt) => atual + (destino - atual) * (1 - Math.exp(-velocidade * dt));

  function animar(agora) {
    const dt = Math.min((agora - ultimoTempo) / 1000, 0.1);
    ultimoTempo = agora;
    if (!dentro || tela.hidden) {  // a tela pode ser trocada sem o ponteiro sair dela
      if (dentro) desativar();
      quadro = null;
      return;
    }
    if (alvo && !alvo.isConnected) escolherAlvo(null);  // a grade é redesenhada ao buscar/filtrar

    pos.x = suavizar(pos.x, mouse.x, 30, dt);
    pos.y = suavizar(pos.y, mouse.y, 30, dt);

    let destinos = CANTOS_DESCANSO.map(([x, y]) => ({ x, y }));
    if (alvo) {
      rotacao = 0;
      const r = alvo.getBoundingClientRect();  // lido a cada quadro: acompanha rolagem e animações
      const esq = r.left - BORDA_CANTO - pos.x;
      const dir = r.right + BORDA_CANTO - TAMANHO_CANTO - pos.x;
      const cima = r.top - BORDA_CANTO - pos.y;
      const baixo = r.bottom + BORDA_CANTO - TAMANHO_CANTO - pos.y;
      destinos = [{ x: esq, y: cima }, { x: dir, y: cima }, { x: dir, y: baixo }, { x: esq, y: baixo }];
    } else if (!semMovimento) {
      rotacao = (rotacao + (360 / VOLTA_SEGUNDOS) * dt) % 360;
    }

    cursor.style.transform = `translate(${pos.x}px, ${pos.y}px) rotate(${rotacao}deg)`;
    cantos.forEach((canto, i) => {
      posCantos[i].x = suavizar(posCantos[i].x, destinos[i].x, alvo ? 22 : 14, dt);
      posCantos[i].y = suavizar(posCantos[i].y, destinos[i].y, alvo ? 22 : 14, dt);
      canto.style.transform = `translate(${posCantos[i].x}px, ${posCantos[i].y}px)`;
    });
    quadro = requestAnimationFrame(animar);
  }

  tela.addEventListener("pointerenter", (e) => {
    mouse.x = pos.x = e.clientX;
    mouse.y = pos.y = e.clientY;
    ativar();
  });
  tela.addEventListener("pointerleave", desativar);
  tela.addEventListener("pointermove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    if (!dentro) ativar();
    escolherAlvo(e.target);
  });
  // Ao rolar, o ponteiro fica parado mas o conteúdo embaixo dele muda
  tela.addEventListener("scroll", () => {
    if (dentro) escolherAlvo(document.elementFromPoint(mouse.x, mouse.y));
  }, { passive: true });
  addEventListener("pointerdown", () => cursor.classList.add("pressionado"));
  addEventListener("pointerup", () => cursor.classList.remove("pressionado"));
})();
