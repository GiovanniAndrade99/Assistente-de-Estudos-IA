"""Rota pública com os dados do aviso de privacidade (LGPD, arts. 9º e 41)."""
from fastapi import APIRouter

from ..aplicacao import privacidade_service

router = APIRouter()


@router.get("/api/privacidade")
def aviso_de_privacidade():
    return privacidade_service.dados_publicos()
