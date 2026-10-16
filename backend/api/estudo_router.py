from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..aplicacao import estudo_service
from ..aplicacao.documentos_service import nome_seguro
from .dependencias import participante_da_disciplina

router = APIRouter()


class PedidoEstudo(BaseModel):
    arquivo: str
    quantidade: int = Field(default=10, ge=1, le=30)


class Respostas(BaseModel):
    # Índice da alternativa marcada (0 a 3) ou null para questão em branco
    respostas: list[int | None] = Field(max_length=30)


@router.post("/api/disciplinas/{disciplina_id}/resumo")
def resumo(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(participante_da_disciplina)):
    return estudo_service.resumir(disciplina_id, nome_seguro(dados.arquivo), usuario["id"])


@router.post("/api/disciplinas/{disciplina_id}/flashcards")
def flashcards(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(participante_da_disciplina)):
    return estudo_service.gerar_flashcards(disciplina_id, nome_seguro(dados.arquivo), usuario["id"], dados.quantidade)


@router.post("/api/disciplinas/{disciplina_id}/simulado")
def simulado(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(participante_da_disciplina)):
    return estudo_service.gerar_simulado(disciplina_id, nome_seguro(dados.arquivo), usuario["id"], dados.quantidade)


@router.post("/api/disciplinas/{disciplina_id}/simulados/{simulado_id}/respostas")
def corrigir_simulado(disciplina_id: int, simulado_id: int, dados: Respostas,
                      usuario: dict = Depends(participante_da_disciplina)):
    return estudo_service.corrigir_simulado(disciplina_id, simulado_id, usuario["id"], dados.respostas)


@router.get("/api/disciplinas/{disciplina_id}/simulado/meus")
def meus_resultados(disciplina_id: int, usuario: dict = Depends(participante_da_disciplina)):
    return estudo_service.meus_resultados_simulado(disciplina_id, usuario["id"])
