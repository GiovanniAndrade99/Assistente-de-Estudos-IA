"""Dependências do FastAPI usadas por praticamente toda rota autenticada."""
from fastapi import Depends, HTTPException, Request

from ..aplicacao.auth_service import NOME_COOKIE, usuario_da_sessao


def usuario_atual(request: Request) -> dict:
    """Use em rotas que exigem login: `usuario: dict = Depends(usuario_atual)`."""
    usuario = usuario_da_sessao(request.cookies.get(NOME_COOKIE))
    if not usuario:
        raise HTTPException(401, "Faça login para continuar.")
    request.state.usuario_id = usuario["id"]  # lido pelo log de acesso (middlewares/observabilidade.py)
    return usuario


def somente_professor(usuario: dict = Depends(usuario_atual)) -> dict:
    if usuario["tipo"] != "professor":
        raise HTTPException(403, "Área restrita a professores.")
    return usuario
