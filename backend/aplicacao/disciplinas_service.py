"""Regras de negócio de disciplinas."""
import shutil

from fastapi import HTTPException

from .. import config
from ..infraestrutura import db, rag
from . import demo_service


def disciplina_ou_404(disciplina_id: int) -> dict:
    disciplina = db.consultar_um("SELECT * FROM disciplinas WHERE id = ?", (disciplina_id,))
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    return disciplina


def listar_disciplinas() -> list[dict]:
    return db.consultar(
        """SELECT d.id, d.nome, d.criado_por, u.nome AS criador,
                  (SELECT COUNT(*) FROM documentos WHERE disciplina_id = d.id) AS documentos
           FROM disciplinas d JOIN usuarios u ON u.id = d.criado_por
           ORDER BY d.nome"""
    )


def criar_disciplina(nome: str, usuario_id: int) -> dict:
    nome = nome.strip()
    if not nome:
        raise HTTPException(400, "Informe o nome da disciplina.")
    if db.consultar_um("SELECT id FROM disciplinas WHERE nome = ?", (nome,)):
        raise HTTPException(400, "Já existe uma disciplina com esse nome.")
    novo_id = db.executar("INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", (nome, usuario_id))
    demo_service.popular_dados_demo(novo_id)
    return {"id": novo_id, "nome": nome}


def remover_disciplina(disciplina_id: int, usuario_id: int) -> None:
    if disciplina_ou_404(disciplina_id)["criado_por"] != usuario_id:
        raise HTTPException(403, "Só quem criou a disciplina pode removê-la.")
    rag.remover_documento(disciplina_id)
    shutil.rmtree(config.PASTA_UPLOADS / str(disciplina_id), ignore_errors=True)
    db.executar("DELETE FROM disciplinas WHERE id = ?", (disciplina_id,))
