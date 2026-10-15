"""Registro central dos exception handlers da API.

Toda resposta de erro JSON tem o formato {"detail": "...", "request_id": "..."}.
O `request_id` deixa o usuário reportar um erro e o desenvolvedor achar, nos
logs, exatamente a linha (ou linhas) daquela requisição.

Regras de privacidade e segurança:
- erro de validação (422) nunca devolve o valor enviado (poderia ser uma senha);
- só `ErroDeUso` (backend/erros.py) chega ao usuário com o texto original; outras
  exceções viram mensagens genéricas, porque podem conter caminhos do servidor.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.genai.errors import APIError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .erros import ErroDeUso
from .middlewares.observabilidade import request_id_var
from .middlewares.seguranca_http import aplicar_cabecalhos

logger = logging.getLogger("erros")

_TRADUCOES_HTTP = {"Not Found": "Não encontrado.", "Method Not Allowed": "Método não permitido."}

_MENSAGENS_VALIDACAO = {
    "missing": "campo obrigatório",
    "string_too_short": "muito curto (mínimo de {min_length} caracteres)",
    "string_too_long": "muito longo (máximo de {max_length} caracteres)",
    "too_short": "itens de menos (mínimo de {min_length})",
    "too_long": "itens demais (máximo de {max_length})",
    "greater_than_equal": "deve ser no mínimo {ge}",
    "less_than_equal": "deve ser no máximo {le}",
    "int_parsing": "deve ser um número inteiro",
    "int_type": "deve ser um número inteiro",
    "float_parsing": "deve ser um número",
    "bool_parsing": "deve ser verdadeiro ou falso",
    "bool_type": "deve ser verdadeiro ou falso",
    "string_type": "deve ser um texto",
    "list_type": "deve ser uma lista",
    "json_invalid": "JSON inválido",
    "model_attributes_type": "formato inválido",
    "dict_type": "formato inválido",
}


def _resposta(status_code: int, detail: str, headers: dict | None = None, extra: dict | None = None,
              caminho: str = "") -> JSONResponse:
    rid = request_id_var.get()
    # A middleware de observabilidade normalmente acrescenta X-Request-ID e os
    # cabeçalhos de segurança, mas um erro não tratado (Exception) é resolvido pelo
    # ServerErrorMiddleware do Starlette, que fica FORA daquela middleware. Por isso
    # os cabeçalhos também são aplicados aqui.
    resposta = JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": rid, **(extra or {})},
        headers={"X-Request-ID": rid, **(headers or {})},
    )
    aplicar_cabecalhos(resposta.headers, caminho, "application/json")
    return resposta


def _erro_de_validacao(erro: dict) -> dict:
    modelo = _MENSAGENS_VALIDACAO.get(erro.get("type", ""))
    try:
        mensagem = modelo.format(**(erro.get("ctx") or {})) if modelo else "valor inválido"
    except (KeyError, IndexError):
        mensagem = "valor inválido"
    partes = [str(p) for p in erro.get("loc", ()) if p not in ("body", "query", "path", "header")]
    return {"campo": ".".join(partes) or "requisição", "mensagem": mensagem}


def registrar_handlers(app: FastAPI) -> None:
    # Cobre as HTTPException do FastAPI (subclasse) e as do próprio Starlette, como o
    # 404 de uma rota inexistente ou de um arquivo estático que não existe.
    @app.exception_handler(StarletteHTTPException)
    def erro_http(request: Request, erro: StarletteHTTPException):
        detalhe = _TRADUCOES_HTTP.get(erro.detail, erro.detail) if isinstance(erro.detail, str) else erro.detail
        return _resposta(erro.status_code, detalhe, getattr(erro, "headers", None), caminho=request.url.path)

    @app.exception_handler(RequestValidationError)
    def erro_de_validacao(request: Request, erro: RequestValidationError):
        erros = [_erro_de_validacao(e) for e in erro.errors()]
        resumo = "; ".join(f"{e['campo']}: {e['mensagem']}" for e in erros)
        return _resposta(422, f"Dados inválidos. {resumo}.", extra={"erros": erros}, caminho=request.url.path)

    @app.exception_handler(ErroDeUso)
    def erro_de_uso(request: Request, erro: ErroDeUso):
        return _resposta(erro.status, erro.mensagem, caminho=request.url.path)

    # ValueError/RuntimeError fora de ErroDeUso: mensagem genérica (o texto original
    # pode ter caminhos do servidor), registrada no log com o request_id.
    @app.exception_handler(ValueError)
    @app.exception_handler(RuntimeError)
    def erro_inesperado_de_uso(request: Request, erro: Exception):
        logger.warning(
            "erro_de_uso_inesperado",
            exc_info=erro,
            extra={"rota": request.url.path, "metodo": request.method},
        )
        return _resposta(400, "Não foi possível concluir a operação com os dados enviados.", caminho=request.url.path)

    @app.exception_handler(APIError)
    def erro_do_gemini(request: Request, erro: APIError):
        logger.warning("erro_api_gemini", extra={"rota": request.url.path, "codigo": erro.code})
        return _resposta(502, "O serviço de IA respondeu com erro. Tente novamente em instantes.",
                         caminho=request.url.path)

    # Qualquer outro erro não previsto: loga o traceback completo (com
    # request_id) e devolve uma mensagem genérica, sem vazar detalhes internos.
    @app.exception_handler(Exception)
    def erro_nao_tratado(request: Request, erro: Exception):
        logger.exception(
            "erro_nao_tratado",
            exc_info=erro,
            extra={"rota": request.url.path, "metodo": request.method},
        )
        return _resposta(500, "Erro interno. Tente novamente mais tarde.", caminho=request.url.path)
