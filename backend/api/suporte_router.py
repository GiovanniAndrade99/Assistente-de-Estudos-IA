"""Rotas dos chamados de suporte. Regras de negócio em aplicacao/suporte_service.py."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..aplicacao import suporte_service
from .dependencias import usuario_atual

router = APIRouter(prefix="/api/suporte")


class NovoChamado(BaseModel):
    categoria: str
    assunto: str = Field(max_length=150)
    mensagem: str = Field(max_length=5000)


class Resposta(BaseModel):
    resposta: str = Field(max_length=5000)


@router.get("/categorias")
def categorias(usuario: dict = Depends(usuario_atual)):
    return {"categorias": list(suporte_service.CATEGORIAS), "categoria_lgpd": suporte_service.CATEGORIA_LGPD,
            "prazo_lgpd_dias": suporte_service.PRAZO_LGPD_DIAS}


@router.get("/chamados")
def listar_chamados(usuario: dict = Depends(usuario_atual)):
    return suporte_service.listar_chamados(usuario)


@router.post("/chamados")
def abrir_chamado(dados: NovoChamado, usuario: dict = Depends(usuario_atual)):
    return {"id": suporte_service.abrir_chamado(usuario, dados.categoria, dados.assunto, dados.mensagem)}


@router.put("/chamados/{chamado_id}/resposta")
def responder_chamado(chamado_id: int, dados: Resposta, usuario: dict = Depends(usuario_atual)):
    suporte_service.responder_chamado(usuario, chamado_id, dados.resposta)
    return {"ok": True}


@router.delete("/chamados/{chamado_id}")
def remover_chamado(chamado_id: int, usuario: dict = Depends(usuario_atual)):
    suporte_service.remover_chamado(usuario, chamado_id)
    return {"ok": True}
