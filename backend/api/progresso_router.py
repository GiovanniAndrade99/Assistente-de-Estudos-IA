from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..aplicacao import progresso_service
from .dependencias import usuario_atual

router = APIRouter()


class AulaConcluida(BaseModel):
    concluida: bool


@router.get("/api/visao-geral")
def visao_geral(usuario: dict = Depends(usuario_atual)):
    return progresso_service.visao_geral(usuario)


@router.put("/api/aulas/{documento_id}/concluida")
def marcar_aula(documento_id: int, dados: AulaConcluida, usuario: dict = Depends(usuario_atual)):
    progresso_service.marcar_aula(documento_id, usuario["id"], dados.concluida)
    return {"ok": True}


@router.get("/api/lembretes")
def lembretes_do_dia(data: str, usuario: dict = Depends(usuario_atual)):
    return progresso_service.lembretes_do_dia(data, usuario["id"])
