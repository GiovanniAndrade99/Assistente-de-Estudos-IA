"""Rotas só de administrador."""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..aplicacao import disciplinas_service
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
