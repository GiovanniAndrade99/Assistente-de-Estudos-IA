from fastapi import APIRouter, Depends, UploadFile

from ..aplicacao import documentos_service
from .dependencias import usuario_atual

router = APIRouter()


@router.get("/api/disciplinas/{disciplina_id}/documentos")
def listar_documentos(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return documentos_service.listar_documentos(disciplina_id, usuario["id"])


@router.post("/api/disciplinas/{disciplina_id}/documentos")
def enviar_documento(disciplina_id: int, arquivo: UploadFile, usuario: dict = Depends(usuario_atual)):
    return documentos_service.enviar_documento(disciplina_id, arquivo, usuario["id"])


@router.delete("/api/disciplinas/{disciplina_id}/documentos/{arquivo}")
def remover_documento(disciplina_id: int, arquivo: str, usuario: dict = Depends(usuario_atual)):
    documentos_service.remover_documento(disciplina_id, arquivo)
    return {"ok": True}
