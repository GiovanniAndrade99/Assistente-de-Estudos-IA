from fastapi import APIRouter, Depends, UploadFile

from ..aplicacao import documentos_service
from .dependencias import participante_da_disciplina, professor_da_disciplina

router = APIRouter()


@router.get("/api/disciplinas/{disciplina_id}/documentos")
def listar_documentos(disciplina_id: int, usuario: dict = Depends(participante_da_disciplina)):
    return documentos_service.listar_documentos(disciplina_id, usuario["id"])


@router.post("/api/disciplinas/{disciplina_id}/documentos")
def enviar_documento(disciplina_id: int, arquivo: UploadFile, professor: dict = Depends(professor_da_disciplina)):
    return documentos_service.enviar_documento(disciplina_id, arquivo, professor["id"])


@router.delete("/api/disciplinas/{disciplina_id}/documentos/{arquivo}")
def remover_documento(disciplina_id: int, arquivo: str, professor: dict = Depends(professor_da_disciplina)):
    documentos_service.remover_documento(disciplina_id, arquivo)
    return {"ok": True}
