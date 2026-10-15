"""Cabeçalhos de segurança e checagem de origem, usados pela middleware de
observabilidade e pelos handlers de erro (respostas 500 não passam por ela).
"""
from urllib.parse import urlsplit

from .. import config

# Sem 'unsafe-inline': scripts e estilos só de arquivos do próprio app. Fontes e
# ícones também são servidos localmente; o único conteúdo externo são vídeos
# incorporados pelo youtube-nocookie.
CSP = "; ".join((
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "font-src 'self'",
    "img-src 'self' data:",
    "frame-src https://www.youtube-nocookie.com",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))

# Só recursos que o app não usa. O player do YouTube precisa de fullscreen,
# picture-in-picture, encrypted-media etc., então esses ficam liberados.
PERMISSOES = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()"

METODOS_QUE_ALTERAM = {"POST", "PUT", "PATCH", "DELETE"}


def aplicar_cabecalhos(headers, caminho: str, tipo_conteudo: str | None) -> None:
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Referrer-Policy"] = "same-origin"
    headers["Permissions-Policy"] = PERMISSOES
    headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # A CSP vale para páginas HTML. A documentação automática (/docs, /redoc, só fora
    # de produção) usa scripts de CDN e script inline, então fica de fora.
    if (tipo_conteudo or "").startswith("text/html") and not caminho.startswith(("/docs", "/redoc")):
        headers["Content-Security-Policy"] = CSP
    if caminho.startswith("/api/"):
        headers["Cache-Control"] = "no-store"
    if config.APP_ENV == "production":
        headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"


def origem_permitida(request) -> bool:
    """Bloqueia requisições que alteram dados vindas de outro site (CSRF).

    O cookie SameSite=Lax já impede que outro site envie o cookie de sessão num
    POST, mas login, cadastro e upload multipart não dependem dele. Compara só o
    host (atrás de proxy com TLS o esquema muda) e aceita a ausência de Origin,
    que é o caso de clientes fora do navegador.
    """
    if request.headers.get("sec-fetch-site") == "cross-site":
        return False
    origem = request.headers.get("origin")
    if origem is None:
        return True
    if origem == "null":
        return False
    if origem.rstrip("/") in config.ORIGENS_PERMITIDAS:
        return True
    return urlsplit(origem).netloc.lower() == request.headers.get("host", "").lower()
