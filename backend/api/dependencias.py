"""Dependências do FastAPI usadas por praticamente toda rota autenticada."""
from fastapi import Depends, HTTPException, Request

from ..aplicacao import disciplinas_service
from ..aplicacao.auth_service import NOME_COOKIE, usuario_da_sessao
from ..infraestrutura import db


def usuario_atual(request: Request) -> dict:
    """Use em rotas que exigem login: `usuario: dict = Depends(usuario_atual)`."""
    usuario = usuario_da_sessao(request.cookies.get(NOME_COOKIE))
    if not usuario:
        raise HTTPException(401, "Faça login para continuar.")
    request.state.usuario_id = usuario["id"]  # lido pelo log de acesso (middlewares/observabilidade.py)
    return usuario


def somente_professor(usuario: dict = Depends(usuario_atual)) -> dict:
    if usuario["tipo"] != "professor" and not usuario.get("administrador"):
        raise HTTPException(403, "Área restrita a professores.")
    return usuario


def acesso_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)) -> dict:
    """Rotas de uma disciplina: ela precisa existir e, para professor, ser uma das que ele administra."""
    disciplinas_service.conferir_acesso(usuario, disciplina_id)
    return usuario


def professor_da_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)) -> dict:
    """Como `somente_professor`, mas só libera quem administra ESSA disciplina (matéria escolhida
    no cadastro, ou que o próprio professor criou) ou o administrador. Sem isso, qualquer professor
    poderia gerenciar notas, atividades e vídeos de disciplinas de outros professores.
    """
    if usuario["tipo"] != "professor" and not usuario.get("administrador"):
        raise HTTPException(403, "Área restrita a professores.")
    disciplinas_service.conferir_acesso(usuario, disciplina_id)
    return usuario
