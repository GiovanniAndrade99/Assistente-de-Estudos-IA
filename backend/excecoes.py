"""Registro central dos exception handlers da API.

Toda resposta de erro JSON tem o formato {"detail": "...", "request_id": "..."}.
O `request_id` deixa o usuário reportar um erro e o desenvolvedor achar, nos
logs, exatamente a linha (ou linhas) daquela requisição.

`detail` é o único campo que o frontend lê (confirmado em app.js e login.js);
adicionar `request_id` ao lado dele é compatível com o que já existe.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google.genai.errors import APIError

from .middlewares.observabilidade import request_id_var

logger = logging.getLogger("erros")


def _resposta(status_code: int, detail: str, headers: dict | None = None) -> JSONResponse:
    rid = request_id_var.get()
    # A middleware de observabilidade (middlewares/observabilidade.py) normalmente
    # já acrescenta X-Request-ID na resposta, mas um erro não tratado (Exception)
    # é resolvido pelo ServerErrorMiddleware do Starlette, que fica FORA daquela
    # middleware — a resposta dele nunca passa por lá. Por isso o cabeçalho
    # também é acrescentado aqui, para todo caso.
    todos_headers = {"X-Request-ID": rid, **(headers or {})}
    return JSONResponse(status_code=status_code, content={"detail": detail, "request_id": rid}, headers=todos_headers)


def registrar_handlers(app: FastAPI) -> None:
    # A maioria das rotas usa HTTPException (401/403/404/400/429...); o
    # handler padrão do FastAPI devolve só {"detail": ...} — aqui acrescentamos
    # o request_id, preservando status e headers originais (ex.: Retry-After).
    @app.exception_handler(HTTPException)
    def erro_http(request: Request, erro: HTTPException):
        return _resposta(erro.status_code, erro.detail, erro.headers)

    # Erros conhecidos (uso indevido da API) viram mensagens legíveis para o frontend
    @app.exception_handler(ValueError)
    @app.exception_handler(RuntimeError)
    def erro_de_uso(request: Request, erro: Exception):
        return _resposta(400, str(erro))

    @app.exception_handler(APIError)
    def erro_do_gemini(request: Request, erro: APIError):
        return _resposta(502, f"Erro na API do Gemini: {erro.message}")

    # Qualquer outro erro não previsto: loga o traceback completo (com
    # request_id) e devolve uma mensagem genérica, sem vazar detalhes internos.
    @app.exception_handler(Exception)
    def erro_nao_tratado(request: Request, erro: Exception):
        logger.exception(
            "erro_nao_tratado",
            exc_info=erro,
            extra={"rota": request.url.path, "metodo": request.method},
        )
        return _resposta(500, "Erro interno. Tente novamente mais tarde.")
