"""Request ID e observabilidade de cada requisição HTTP.

Cada requisição recebe um identificador único (o do cabeçalho `X-Request-ID`
enviado pelo cliente, se houver e for válido; senão um UUID4 novo). Esse id:
- volta no cabeçalho `X-Request-ID` da resposta;
- aparece em toda linha de log gerada durante a requisição (via ContextVar,
  lido pelo formatter em infraestrutura/logging_setup.py);
- aparece no corpo de qualquer resposta de erro (backend/excecoes.py).

Isso permite rastrear, a partir de um erro relatado pelo usuário, exatamente
quais logs no servidor correspondem àquela chamada.

Esta mesma middleware também acrescenta cabeçalhos de segurança e grava uma
linha de log de acesso (método, rota, status, duração) por requisição.
"""
import contextvars
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from .. import config

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Aceita apenas ids "razoáveis" recebidos do cliente; qualquer coisa fora
# disso (vazio, caracteres de controle, tamanho absurdo) gera um novo, para
# não deixar um cliente malicioso injetar valores estranhos nos logs.
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

logger_acesso = logging.getLogger("acesso")


class ObservabilidadeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, chamar_proximo):
        recebido = request.headers.get("x-request-id", "")
        request_id = recebido if _ID_VALIDO.fullmatch(recebido) else str(uuid.uuid4())
        # De propósito, sem reset: o handler para `Exception` não previsto (excecoes.py)
        # é instalado pelo Starlette no ServerErrorMiddleware, que fica FORA desta
        # middleware — se um erro não tratado escapar de `chamar_proximo`, ele só é
        # capturado depois que esta função já teria saído. Resetar aqui (num finally,
        # por exemplo) apagaria o request_id antes daquele handler conseguir lê-lo.
        # Cada requisição roda numa Task asyncio própria, então não há risco de um
        # valor "vazar" para a requisição seguinte por nunca ser resetado.
        request_id_var.set(request_id)
        inicio = time.perf_counter()

        try:
            resposta = await chamar_proximo(request)
        except Exception:
            logger_acesso.info(
                "requisicao",
                extra={
                    "request_id": request_id,
                    "metodo": request.method,
                    "rota": request.url.path,
                    "status": 500,
                    "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
                    "usuario_id": getattr(request.state, "usuario_id", None),
                },
            )
            raise

        duracao_ms = round((time.perf_counter() - inicio) * 1000, 1)
        resposta.headers["X-Request-ID"] = request_id
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "same-origin"
        if config.APP_ENV == "production":
            resposta.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        logger_acesso.info(
            "requisicao",
            extra={
                "request_id": request_id,
                "metodo": request.method,
                "rota": request.url.path,
                "status": resposta.status_code,
                "duracao_ms": duracao_ms,
                "usuario_id": getattr(request.state, "usuario_id", None),
            },
        )
        return resposta
