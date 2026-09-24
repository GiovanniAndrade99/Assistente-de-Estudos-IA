from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..aplicacao import disciplinas_service
from .dependencias import usuario_atual

router = APIRouter()


class NovaDisciplina(BaseModel):
    nome: str


class Matricula(BaseModel):
    disciplina_ids: list[int]


@router.get("/api/disciplinas/publico")
def listar_disciplinas_publico():
    return disciplinas_service.listar_disciplinas_publico()


@router.get("/api/disciplinas")
def listar_disciplinas(usuario: dict = Depends(usuario_atual)):
    return disciplinas_service.listar_disciplinas(usuario)


@router.post("/api/disciplinas")
def criar_disciplina(dados: NovaDisciplina, usuario: dict = Depends(usuario_atual)):
    return disciplinas_service.criar_disciplina(dados.nome, usuario)


@router.post("/api/disciplinas/matricular")
def matricular(dados: Matricula, usuario: dict = Depends(usuario_atual)):
    disciplinas_service.matricular(usuario["id"], dados.disciplina_ids)
    return {"ok": True}


@router.delete("/api/disciplinas/{disciplina_id}")
def remover_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    disciplinas_service.remover_disciplina(disciplina_id, usuario["id"])
    return {"ok": True}
