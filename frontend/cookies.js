// Aviso transparente: a aplicação usa apenas o cookie essencial da sessão.
(() => {
  const chave = "aviso-cookies-visto-v1";
  function exibirAviso() {
    if (document.querySelector(".aviso-cookies")) return;
    const aviso = document.createElement("aside");
    aviso.className = "aviso-cookies";
    aviso.setAttribute("aria-label", "Aviso sobre cookies");
    aviso.setAttribute("aria-live", "polite");
    aviso.innerHTML = `
      <p><strong>Cookies neste sistema</strong><br>
        Usamos somente o cookie essencial de sessão para manter seu login. Não usamos cookies de publicidade ou analytics.
        <a href="/privacidade.html">Leia o aviso de privacidade</a>.
      </p>
      <div class="aviso-cookies-acoes"><button type="button">Entendi</button></div>`;
    aviso.querySelector("button").addEventListener("click", () => {
      try { localStorage.setItem(chave, "sim"); } catch {}
      aviso.remove();
    });
    document.body.append(aviso);
  }
  window.mostrarAvisoCookies = exibirAviso;
  let jaVisto = false;
  try { jaVisto = localStorage.getItem(chave) === "sim"; } catch {}
  if (!jaVisto) exibirAviso();
})();
