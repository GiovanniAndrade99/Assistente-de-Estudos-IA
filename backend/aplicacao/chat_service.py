"""Regras de negócio do chat com o material (RAG)."""
from fastapi import HTTPException

from ..infraestrutura import db, rag
from . import limite_service
from .disciplinas_service import disciplina_ou_404


def chat(disciplina_id: int, pergunta: str, usuario_id: int) -> dict:
    disciplina_ou_404(disciplina_id)
    if not pergunta.strip():
        raise HTTPException(400, "Pergunta vazia")
    limite_service.limitar(f"usuario:{usuario_id}", "chat", limite=20, janela_minutos=5)
    resultado = rag.responder(pergunta, disciplina_id)
    db.executar(  # histórico usado no painel do professor
        "INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta) VALUES (?, ?, ?, ?)",
        (usuario_id, disciplina_id, pergunta.strip(), resultado["resposta"]),
    )
    return resultado
