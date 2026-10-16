"""Rotas só de administrador."""
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from .. import config
from ..aplicacao import disciplinas_service
from ..infraestrutura import metricas
from .dependencias import somente_admin

router = APIRouter(prefix="/api/admin")
logger = logging.getLogger("admin")


class Transferencia(BaseModel):
    email_professor: str = Field(max_length=254)


@router.get("/disciplinas-sem-professor")
def disciplinas_sem_professor(admin: dict = Depends(somente_admin)):
    return disciplinas_service.listar_sem_professor()


@router.put("/disciplinas/{disciplina_id}/professor")
def transferir_disciplina(disciplina_id: int, dados: Transferencia, admin: dict = Depends(somente_admin)):
    resultado = disciplinas_service.transferir(disciplina_id, dados.email_professor)
    logger.info("disciplina_transferida", extra={"usuario_id": admin["id"], "disciplina_id": disciplina_id})
    return resultado


@router.get("/metricas")
def metricas_de_uso(dias: int = Query(30, ge=1, le=365), admin: dict = Depends(somente_admin)):
    return {**metricas.resumo(dias), "ia_hoje": {
        "tokens": metricas.tokens_hoje(), "alerta": config.ALERTA_TOKENS_DIA, "teto": config.TETO_TOKENS_DIA,
        "cota_aluno": config.COTA_IA_DIA_ALUNO, "cota_professor": config.COTA_IA_DIA_PROFESSOR,
    }}
