"""Health check: usado por monitoramento externo (uptime) e para diagnosticar
rapidamente se o processo está de pé e o banco está acessível. Não depende do
Gemini de propósito — é uma API externa, paga e com limite de requisições, sem
motivo para estar no caminho crítico de um health check.
"""
from fastapi import APIRouter

from ..infraestrutura import db

router = APIRouter()


@router.get("/api/health")
def saude():
    db.consultar_um("SELECT 1")
    return {"status": "ok"}
