"""Rotas dos recursos da turma em cada disciplina: calendário, atividades,
videoaulas e chat. Regras de negócio ficam em aplicacao/turma_service.py.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..aplicacao import turma_service
from .dependencias import somente_professor, usuario_atual

# Toda rota deste arquivo recebe {disciplina_id} e já confere se ela existe
router = APIRouter(
    prefix="/api/disciplinas/{disciplina_id}",
    dependencies=[Depends(turma_service.conferir_disciplina)],
)


# ---------------------------------------------------------------- calendário

class NovoEvento(BaseModel):
    titulo: str = Field(max_length=120)
    datas: list[str] = Field(min_length=1, max_length=100)  # um evento para cada dia escolhido
    hora: str | None = None                                  # "HH:MM"; None = dia todo
    descricao: str = Field(default="", max_length=1000)


@router.get("/eventos")
def listar_eventos(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return turma_service.listar_eventos(disciplina_id, usuario["id"])


@router.post("/eventos")
def criar_evento(disciplina_id: int, dados: NovoEvento, usuario: dict = Depends(usuario_atual)):
    criados = turma_service.criar_evento(disciplina_id, usuario, dados.titulo, dados.datas, dados.hora, dados.descricao)
    return {"criados": criados}


@router.delete("/eventos/{evento_id}")
def remover_evento(disciplina_id: int, evento_id: int, usuario: dict = Depends(usuario_atual)):
    turma_service.remover_evento(disciplina_id, evento_id, usuario["id"])
    return {"ok": True}


# ---------------------------------------------------------------- atividades

class NovaAtividade(BaseModel):
    titulo: str = Field(max_length=150)
    descricao: str = Field(default="", max_length=5000)
    prazo: str


class Entrega(BaseModel):
    resposta: str = Field(max_length=10000)


class Correcao(BaseModel):
    nota: float = Field(ge=0, le=10)
    comentario: str = Field(default="", max_length=2000)


@router.get("/atividades")
def listar_atividades(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return turma_service.listar_atividades(disciplina_id, usuario["id"])


@router.post("/atividades")
def criar_atividade(disciplina_id: int, dados: NovaAtividade, professor: dict = Depends(somente_professor)):
    novo_id = turma_service.criar_atividade(disciplina_id, professor["id"], dados.titulo, dados.descricao, dados.prazo)
    return {"id": novo_id}


@router.delete("/atividades/{atividade_id}")
def remover_atividade(disciplina_id: int, atividade_id: int, professor: dict = Depends(somente_professor)):
    turma_service.remover_atividade(disciplina_id, atividade_id)
    return {"ok": True}


@router.post("/atividades/{atividade_id}/entrega")
def entregar_atividade(disciplina_id: int, atividade_id: int, dados: Entrega,
                       usuario: dict = Depends(usuario_atual)):
    turma_service.entregar_atividade(disciplina_id, atividade_id, usuario, dados.resposta)
    return {"ok": True}


@router.get("/atividades/{atividade_id}/entregas")
def listar_entregas(disciplina_id: int, atividade_id: int, professor: dict = Depends(somente_professor)):
    return turma_service.listar_entregas(disciplina_id, atividade_id)


@router.put("/atividades/{atividade_id}/entregas/{entrega_id}")
def corrigir_entrega(disciplina_id: int, atividade_id: int, entrega_id: int, dados: Correcao,
                     professor: dict = Depends(somente_professor)):
    turma_service.corrigir_entrega(disciplina_id, atividade_id, entrega_id, dados.nota, dados.comentario)
    return {"ok": True}


# ---------------------------------------------------------------- videoaulas

class NovoVideo(BaseModel):
    titulo: str = Field(max_length=150)
    url: str = Field(max_length=500)
    descricao: str = Field(default="", max_length=1000)


@router.get("/videos")
def listar_videos(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return turma_service.listar_videos(disciplina_id)


@router.post("/videos")
def adicionar_video(disciplina_id: int, dados: NovoVideo, professor: dict = Depends(somente_professor)):
    novo_id = turma_service.adicionar_video(disciplina_id, professor["id"], dados.titulo, dados.url, dados.descricao)
    return {"id": novo_id}


@router.delete("/videos/{video_id}")
def remover_video(disciplina_id: int, video_id: int, professor: dict = Depends(somente_professor)):
    turma_service.remover_video(disciplina_id, video_id)
    return {"ok": True}


# ---------------------------------------------------------------- chat da turma

class NovaMensagem(BaseModel):
    texto: str = Field(max_length=1000)


@router.get("/mensagens")
def listar_mensagens(disciplina_id: int, depois: int = 0, usuario: dict = Depends(usuario_atual)):
    return turma_service.listar_mensagens(disciplina_id, depois)


@router.post("/mensagens")
def enviar_mensagem(disciplina_id: int, dados: NovaMensagem, usuario: dict = Depends(usuario_atual)):
    novo_id = turma_service.enviar_mensagem(disciplina_id, usuario["id"], dados.texto)
    return {"id": novo_id}
