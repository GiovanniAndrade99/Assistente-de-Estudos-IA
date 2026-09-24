// Brilho especular nos cartões da tela "Suporte": adaptação em JS puro do SpecularButton
// (React Bits). O original desenha com WebGL (um canvas por botão); aqui um conic-gradient
// na borda (::before, ver style.css) faz o mesmo papel, sem limite de contextos WebGL.
// A luz aponta para o ponteiro e acende conforme ele se aproxima do cartão.

const ALVOS_ESPECULAR = "#tela-suporte :is(.item-faq, #form-chamado, .chamado)";
const PROXIMIDADE = 250;   // px: a partir dessa distância o brilho some
const ABERTURA_BRILHO = 50; // graus do centro do brilho até ele sumir (shineSize + shineFade)

(function iniciarBrilhoEspecular() {
  const tela = $("tela-suporte");
  if (!tela || !matchMedia("(hover: hover) and (pointer: fine)").matches) return;

  const estados = new WeakMap();  // cartão → { angulo, forca }
  const ponteiro = { x: 0, y: 0, movido: false };
  let quadro = null;
  let ultimoTempo = 0;

  // Converte a direção da "normal elíptica" (como no shader original: o brilho se espalha
  // igual em lados longos e curtos) para o ângulo real do ponto na borda, no padrão do
  // conic-gradient (0° = para cima, sentido horário).
  function anguloNaBorda(psi, meiaLargura, meiaAltura) {
    const theta = Math.atan2(meiaAltura * Math.sin(psi), meiaLargura * Math.cos(psi));
    return (((90 - (theta * 180) / Math.PI) % 360) + 360) % 360;
  }

  function gradiente(angulo, meiaLargura, meiaAltura) {
    const abertura = (ABERTURA_BRILHO * Math.PI) / 180;
    // Dois brilhos opostos (o lado voltado para a luz e o oposto), em ordem horária
    const marcos = [angulo + abertura, angulo, angulo - abertura,
      angulo + Math.PI + abertura, angulo + Math.PI, angulo + Math.PI - abertura]
      .map((psi) => anguloNaBorda(psi, meiaLargura, meiaAltura));
    const inicio = marcos[0];
    const [, pico1, fim1, inicio2, pico2, fim2] = marcos.map((a) => ((a - inicio) % 360 + 360) % 360);
    return `conic-gradient(from ${inicio.toFixed(1)}deg, transparent 0deg, var(--luz-cor) ${pico1.toFixed(1)}deg,
      transparent ${fim1.toFixed(1)}deg, transparent ${inicio2.toFixed(1)}deg, var(--luz-cor) ${pico2.toFixed(1)}deg,
      transparent ${fim2.toFixed(1)}deg)`;
  }

  // Para onde a luz deve apontar e com que força, conforme a posição do ponteiro
  function destino(r) {
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const dx = Math.max(r.left - ponteiro.x, 0, ponteiro.x - r.right);
    const dy = Math.max(r.top - ponteiro.y, 0, ponteiro.y - r.bottom);
    const distancia = Math.hypot(dx, dy);
    let angulo;
    if (distancia === 0) {
      // Sobre o cartão: a luz fica na diagonal e balança um pouco com o ponteiro
      const nx = (ponteiro.x - cx) / (r.width / 2);
      const ny = (cy - ponteiro.y) / (r.height / 2);
      angulo = Math.atan2(2 / r.height, -2 / r.width) + nx * 0.3 + ny * 0.15;
    } else {
      angulo = Math.atan2(cy - ponteiro.y, ponteiro.x - cx);
    }
    const t = Math.max(0, 1 - distancia / PROXIMIDADE);
    return { angulo, forca: t * t * (3 - 2 * t) };
  }

  function animar(agora) {
    const dt = Math.min((agora - ultimoTempo) / 1000, 0.05);
    ultimoTempo = agora;
    if (tela.hidden) {
      quadro = null;
      return;
    }
    let mexendo = false;
    for (const cartao of tela.querySelectorAll(ALVOS_ESPECULAR)) {
      const r = cartao.getBoundingClientRect();
      if (!r.width || !r.height) continue;  // escondido pela busca do FAQ
      const estado = estados.get(cartao) || { angulo: 2.4, forca: 0 };
      const alvo = ponteiro.movido ? destino(r) : { angulo: estado.angulo, forca: 0 };
      const diferenca = ((alvo.angulo - estado.angulo + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
      estado.angulo += diferenca * (1 - Math.exp(-dt * 7));
      estado.forca += (alvo.forca - estado.forca) * (1 - Math.exp(-dt * 8));
      estados.set(cartao, estado);
      if (Math.abs(diferenca) > 0.002 || Math.abs(alvo.forca - estado.forca) > 0.002) mexendo = true;

      cartao.style.setProperty("--luz-forca", estado.forca.toFixed(3));
      if (estado.forca > 0.005) cartao.style.setProperty("--luz", gradiente(estado.angulo, r.width / 2, r.height / 2));
    }
    // Para o laço quando tudo assentou; o próximo movimento do ponteiro religa
    quadro = mexendo ? requestAnimationFrame(animar) : null;
  }

  function religar() {
    if (quadro || tela.hidden) return;
    ultimoTempo = performance.now();
    quadro = requestAnimationFrame(animar);
  }

  addEventListener("pointermove", (e) => {
    ponteiro.x = e.clientX;
    ponteiro.y = e.clientY;
    ponteiro.movido = true;
    religar();
  }, { passive: true });
  // Rolar (a tela ou as listas dentro dela) ou abrir uma pergunta do FAQ muda a posição
  // dos cartões sem mover o ponteiro. "scroll" não sobe pela árvore, por isso a captura.
  tela.addEventListener("scroll", religar, { passive: true, capture: true });
  tela.addEventListener("toggle", religar, true);
})();
