// Aplica o tema salvo antes de desenhar a página (evita "piscar" claro → escuro).
// Fica num arquivo próprio porque a política de conteúdo (CSP) não permite script inline.
try { document.documentElement.dataset.tema = localStorage.getItem("tema") || "claro"; } catch {}
