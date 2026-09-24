from fastapi import APIRouter, Depends

from ..aplicacao import ia_service
from .dependencias import usuario_atual

router = APIRouter()


@router.get("/api/ia/sobre")
def sobre_a_ia(usuario: dict = Depends(usuario_atual)):
    return ia_service.sobre_a_ia()
