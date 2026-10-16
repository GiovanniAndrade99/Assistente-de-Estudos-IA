from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..aplicacao import chat_service
from .dependencias import participante_da_disciplina

router = APIRouter()


class Pergunta(BaseModel):
    pergunta: str


@router.post("/api/disciplinas/{disciplina_id}/chat")
def chat(disciplina_id: int, dados: Pergunta, usuario: dict = Depends(participante_da_disciplina)):
    return chat_service.chat(disciplina_id, dados.pergunta, usuario["id"])


@router.post("/api/disciplinas/{disciplina_id}/chat/stream")
def chat_stream(disciplina_id: int, dados: Pergunta, usuario: dict = Depends(participante_da_disciplina)):
    eventos = chat_service.chat_stream(disciplina_id, dados.pergunta, usuario["id"])
    return StreamingResponse(eventos, media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
