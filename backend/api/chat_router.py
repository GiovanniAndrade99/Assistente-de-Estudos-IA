from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..aplicacao import chat_service
from .dependencias import acesso_disciplina

router = APIRouter()


class Pergunta(BaseModel):
    pergunta: str


@router.post("/api/disciplinas/{disciplina_id}/chat")
def chat(disciplina_id: int, dados: Pergunta, usuario: dict = Depends(acesso_disciplina)):
    return chat_service.chat(disciplina_id, dados.pergunta, usuario["id"])
