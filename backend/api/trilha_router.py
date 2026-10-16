from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..aplicacao import trilha_service
from .dependencias import participante_da_disciplina, usuario_atual

router = APIRouter()


class Trilha(BaseModel):
    objetivo: Literal["prova", "enade", "transferencia", "segunda_graduacao"]
    data_alvo: date
    horas_semana: int = Field(ge=1, le=60)


class Cartao(BaseModel):
    frente: str = Field(min_length=1, max_length=300)
    verso: str = Field(min_length=1, max_length=1000)
    pagina: int | None = Field(default=None, ge=0, le=100_000)


class NovosCartoes(BaseModel):
    arquivo: str = Field(default="", max_length=255)
    cartoes: list[Cartao] = Field(min_length=1, max_length=50)


class Revisao(BaseModel):
    nota: int = Field(ge=0, le=5)


@router.get("/api/universidades")
def universidades(usuario: dict = Depends(usuario_atual)):
    return trilha_service.universidades()


@router.get("/api/disciplinas/{disciplina_id}/trilha")
def obter_trilha(disciplina_id: int, usuario: dict = Depends(participante_da_disciplina)):
    return trilha_service.obter(usuario["id"], disciplina_id)


@router.put("/api/disciplinas/{disciplina_id}/trilha")
def salvar_trilha(disciplina_id: int, dados: Trilha, usuario: dict = Depends(participante_da_disciplina)):
    return trilha_service.salvar(usuario["id"], disciplina_id, dados.objetivo, dados.data_alvo, dados.horas_semana)


@router.delete("/api/disciplinas/{disciplina_id}/trilha")
def remover_trilha(disciplina_id: int, usuario: dict = Depends(participante_da_disciplina)):
    trilha_service.remover(usuario["id"], disciplina_id)
    return {"ok": True}


@router.post("/api/disciplinas/{disciplina_id}/baralho")
def salvar_cartoes(disciplina_id: int, dados: NovosCartoes, usuario: dict = Depends(participante_da_disciplina)):
    return trilha_service.salvar_cartoes(usuario["id"], disciplina_id, dados.arquivo,
                                         [c.model_dump() for c in dados.cartoes])


@router.get("/api/disciplinas/{disciplina_id}/baralho/hoje")
def cartoes_para_hoje(disciplina_id: int, usuario: dict = Depends(participante_da_disciplina)):
    return trilha_service.cartoes_para_hoje(usuario["id"], disciplina_id)


@router.post("/api/baralho/{cartao_id}/revisao")
def revisar_cartao(cartao_id: int, dados: Revisao, usuario: dict = Depends(usuario_atual)):
    return trilha_service.revisar(usuario["id"], cartao_id, dados.nota)


@router.delete("/api/baralho/{cartao_id}")
def remover_cartao(cartao_id: int, usuario: dict = Depends(usuario_atual)):
    trilha_service.remover_cartao(usuario["id"], cartao_id)
    return {"ok": True}
