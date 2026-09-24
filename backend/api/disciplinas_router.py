from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..aplicacao import disciplinas_service
from .dependencias import usuario_atual

router = APIRouter()


class NovaDisciplina(BaseModel):
    nome: str


@router.get("/api/disciplinas")
def listar_disciplinas(usuario: dict = Depends(usuario_atual)):
    return disciplinas_service.listar_disciplinas()


@router.post("/api/disciplinas")
def criar_disciplina(dados: NovaDisciplina, usuario: dict = Depends(usuario_atual)):
    return disciplinas_service.criar_disciplina(dados.nome, usuario["id"])


@router.delete("/api/disciplinas/{disciplina_id}")
def remover_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    disciplinas_service.remover_disciplina(disciplina_id, usuario["id"])
    return {"ok": True}
