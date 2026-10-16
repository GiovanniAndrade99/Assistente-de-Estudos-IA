"""Rotas da própria conta ligadas à LGPD: ciência do aviso de privacidade e
direitos do titular. Ficam liberadas mesmo antes da ciência (dependencias.py)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..aplicacao import auth_service
from .dependencias import usuario_atual

router = APIRouter(prefix="/api/conta")


class Ciencia(BaseModel):
    aceite_privacidade: bool = False
    declara_maioridade: bool = False


@router.post("/ciencia-privacidade")
def registrar_ciencia(dados: Ciencia, usuario: dict = Depends(usuario_atual)):
    auth_service.exigir_declaracoes(dados.aceite_privacidade, dados.declara_maioridade)
    auth_service.registrar_ciencia(usuario["id"])
    return {"ok": True}
