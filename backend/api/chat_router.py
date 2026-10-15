from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..aplicacao import chat_service
from .dependencias import participante_da_disciplina

router = APIRouter()


class Pergunta(BaseModel):
    pergunta: str


@router.post("/api/disciplinas/{disciplina_id}/chat")
def chat(disciplina_id: int, dados: Pergunta, usuario: dict = Depends(participante_da_disciplina)):
    return chat_service.chat(disciplina_id, dados.pergunta, usuario["id"])
