"""Suporte ao usuário: chamados abertos por alunos e professores.

Cada usuário vê os próprios chamados; administradores veem todos e respondem.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import db
from .auth import usuario_atual

router = APIRouter(prefix="/api/suporte")

CATEGORIAS = ("Dúvida de uso", "Problema técnico", "Assistente IA", "Conta e acesso", "Sugestão")


class NovoChamado(BaseModel):
    categoria: str
    assunto: str = Field(max_length=150)
    mensagem: str = Field(max_length=5000)


class Resposta(BaseModel):
    resposta: str = Field(max_length=5000)


@router.get("/chamados")
def listar_chamados(usuario: dict = Depends(usuario_atual)):
    sql = """SELECT c.*, u.nome AS autor, u.email AS email_autor
             FROM chamados_suporte c JOIN usuarios u ON u.id = c.usuario_id"""
    if usuario.get("administrador"):
        return db.consultar(sql + " ORDER BY c.resposta IS NOT NULL, c.criado_em DESC LIMIT 200")
    return db.consultar(sql + " WHERE c.usuario_id = ? ORDER BY c.criado_em DESC", (usuario["id"],))


@router.post("/chamados")
def abrir_chamado(dados: NovoChamado, usuario: dict = Depends(usuario_atual)):
    assunto, mensagem = dados.assunto.strip(), dados.mensagem.strip()
    if dados.categoria not in CATEGORIAS:
        raise HTTPException(400, "Categoria inválida.")
    if not assunto or not mensagem:
        raise HTTPException(400, "Preencha o assunto e a mensagem.")
    chamado_id = db.executar(
        "INSERT INTO chamados_suporte (usuario_id, categoria, assunto, mensagem) VALUES (?, ?, ?, ?)",
        (usuario["id"], dados.categoria, assunto, mensagem),
    )
    return {"id": chamado_id}


@router.put("/chamados/{chamado_id}/resposta")
def responder_chamado(chamado_id: int, dados: Resposta, usuario: dict = Depends(usuario_atual)):
    if not usuario.get("administrador"):
        raise HTTPException(403, "Só administradores respondem chamados.")
    if not dados.resposta.strip():
        raise HTTPException(400, "Escreva a resposta.")
    if not db.consultar_um("SELECT id FROM chamados_suporte WHERE id = ?", (chamado_id,)):
        raise HTTPException(404, "Chamado não encontrado.")
    db.executar(
        "UPDATE chamados_suporte SET resposta = ?, respondido_em = CURRENT_TIMESTAMP WHERE id = ?",
        (dados.resposta.strip(), chamado_id),
    )
    return {"ok": True}


@router.delete("/chamados/{chamado_id}")
def remover_chamado(chamado_id: int, usuario: dict = Depends(usuario_atual)):
    chamado = db.consultar_um("SELECT usuario_id FROM chamados_suporte WHERE id = ?", (chamado_id,))
    if not chamado:
        raise HTTPException(404, "Chamado não encontrado.")
    if chamado["usuario_id"] != usuario["id"] and not usuario.get("administrador"):
        raise HTTPException(403, "Você só pode remover os seus chamados.")
    db.executar("DELETE FROM chamados_suporte WHERE id = ?", (chamado_id,))
    return {"ok": True}
