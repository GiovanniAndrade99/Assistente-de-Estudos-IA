from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..aplicacao import estudo_service
from ..aplicacao.documentos_service import nome_seguro
from .dependencias import usuario_atual

router = APIRouter()


class PedidoEstudo(BaseModel):
    arquivo: str
    quantidade: int = Field(default=10, ge=1, le=30)


class ResultadoSimulado(BaseModel):
    arquivo: str
    acertos: int = Field(ge=0)
    total: int = Field(ge=1)


@router.post("/api/disciplinas/{disciplina_id}/resumo")
def resumo(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(usuario_atual)):
    return estudo_service.resumir(disciplina_id, nome_seguro(dados.arquivo))


@router.post("/api/disciplinas/{disciplina_id}/flashcards")
def flashcards(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(usuario_atual)):
    return estudo_service.gerar_flashcards(disciplina_id, nome_seguro(dados.arquivo), dados.quantidade)


@router.post("/api/disciplinas/{disciplina_id}/simulado")
def simulado(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(usuario_atual)):
    return estudo_service.gerar_simulado(disciplina_id, nome_seguro(dados.arquivo), dados.quantidade)


@router.post("/api/disciplinas/{disciplina_id}/simulado/resultado")
def salvar_resultado(disciplina_id: int, dados: ResultadoSimulado, usuario: dict = Depends(usuario_atual)):
    estudo_service.salvar_resultado_simulado(disciplina_id, usuario["id"], dados.arquivo, dados.acertos, dados.total)
    return {"ok": True}


@router.get("/api/disciplinas/{disciplina_id}/simulado/meus")
def meus_resultados(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return estudo_service.meus_resultados_simulado(disciplina_id, usuario["id"])
