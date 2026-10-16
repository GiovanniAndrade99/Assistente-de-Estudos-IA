from urllib.parse import quote

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from ..aplicacao import documentos_service
from .dependencias import participante_da_disciplina, professor_da_disciplina

router = APIRouter()


@router.get("/api/disciplinas/{disciplina_id}/documentos")
def listar_documentos(disciplina_id: int, usuario: dict = Depends(participante_da_disciplina)):
    return documentos_service.listar_documentos(disciplina_id, usuario["id"])


@router.post("/api/disciplinas/{disciplina_id}/documentos", status_code=202)
def enviar_documento(disciplina_id: int, arquivo: UploadFile, professor: dict = Depends(professor_da_disciplina)):
    return documentos_service.enviar_documento(disciplina_id, arquivo, professor["id"])


@router.delete("/api/disciplinas/{disciplina_id}/documentos/{arquivo}")
def remover_documento(disciplina_id: int, arquivo: str, professor: dict = Depends(professor_da_disciplina)):
    documentos_service.remover_documento(disciplina_id, arquivo)
    return {"ok": True}


@router.get("/api/disciplinas/{disciplina_id}/documentos/{documento_id}/arquivo")
def abrir_documento(disciplina_id: int, documento_id: int, usuario: dict = Depends(participante_da_disciplina)):
    """O PDF em si, para a citação abrir na página (#page=N) no leitor do navegador."""
    caminho, nome = documentos_service.caminho_para_leitura(disciplina_id, documento_id)
    return FileResponse(caminho, media_type="application/pdf",
                        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(nome)}"})
