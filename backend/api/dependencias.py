"""Dependências do FastAPI usadas por praticamente toda rota autenticada."""
from fastapi import Depends, HTTPException, Request

from ..aplicacao import auth_service, participacao_service
from ..aplicacao.auth_service import NOME_COOKIE, usuario_da_sessao
from ..infraestrutura import db

# Liberadas antes de a pessoa confirmar o aviso de privacidade e a idade mínima:
# a própria conta (inclusive baixar e excluir os dados) e o suporte.
_LIBERADAS_SEM_CIENCIA = ("/api/auth/", "/api/conta/", "/api/suporte/")


def usuario_atual(request: Request) -> dict:
    """Use em rotas que exigem login: `usuario: dict = Depends(usuario_atual)`."""
    usuario = usuario_da_sessao(request.cookies.get(NOME_COOKIE))
    if not usuario:
        raise HTTPException(401, "Faça login para continuar.")
    request.state.usuario_id = usuario["id"]  # lido pelo log de acesso (middlewares/observabilidade.py)
    auth_service.registrar_acesso(usuario)
    if auth_service.ciencia_pendente(usuario) and not request.url.path.startswith(_LIBERADAS_SEM_CIENCIA):
        raise HTTPException(
            403, "Confirme o aviso de privacidade e a idade mínima para continuar.",
            headers={"X-Acao-Necessaria": "ciencia-privacidade"},
        )
    return usuario


def somente_professor(usuario: dict = Depends(usuario_atual)) -> dict:
    if usuario["tipo"] != "professor" and not usuario.get("administrador"):
        raise HTTPException(403, "Área restrita a professores.")
    return usuario


def professor_da_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)) -> dict:
    """Como `somente_professor`, mas só libera quem criou ESSA disciplina (ou
    administrador). Sem isso, qualquer professor poderia gerenciar notas,
    atividades e vídeos de disciplinas de outros professores — o equivalente,
    nesta arquitetura sem RLS de banco, a uma política "dono da linha".
    """
    if usuario["tipo"] != "professor" and not usuario.get("administrador"):
        raise HTTPException(403, "Área restrita a professores.")
    disciplina = db.consultar_um("SELECT criado_por FROM disciplinas WHERE id = ?", (disciplina_id,))
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    if not usuario.get("administrador") and disciplina["criado_por"] != usuario["id"]:
        raise HTTPException(403, "Você só pode gerenciar disciplinas que você criou.")
    return usuario


def participante_da_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)) -> dict:
    """Admin, professor dono ou aluno matriculado (aplicacao/participacao_service.py).

    Sem isso, qualquer conta logada lia o chat da turma (nomes e mensagens),
    eventos e materiais de qualquer disciplina e usava a IA sobre eles.
    """
    disciplina = db.consultar_um("SELECT id, criado_por FROM disciplinas WHERE id = ?", (disciplina_id,))
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    if not participacao_service.participa(usuario, disciplina):
        raise HTTPException(403, "Você não participa desta disciplina.")
    return usuario
