"""Regras de negócio do suporte: chamados abertos por alunos e professores.

Cada usuário vê os próprios chamados; administradores veem todos e respondem.
"""
import logging

from fastapi import HTTPException

from ..infraestrutura import db

logger = logging.getLogger("suporte")

CATEGORIAS = ("Dúvida de uso", "Problema técnico", "Assistente IA", "Conta e acesso", "Sugestão")


def listar_chamados(usuario: dict) -> list[dict]:
    sql = """SELECT c.*, u.nome AS autor, u.email AS email_autor
             FROM chamados_suporte c JOIN usuarios u ON u.id = c.usuario_id"""
    if usuario.get("administrador"):
        # Os ainda sem resposta primeiro
        return db.consultar(sql + " ORDER BY c.resposta IS NOT NULL, c.criado_em DESC LIMIT 200")
    return db.consultar(sql + " WHERE c.usuario_id = ? ORDER BY c.criado_em DESC", (usuario["id"],))


def abrir_chamado(usuario: dict, categoria: str, assunto: str, mensagem: str) -> int:
    assunto, mensagem = assunto.strip(), mensagem.strip()
    if categoria not in CATEGORIAS:
        raise HTTPException(400, "Categoria inválida.")
    if not assunto or not mensagem:
        raise HTTPException(400, "Preencha o assunto e a mensagem.")
    chamado_id = db.executar(
        "INSERT INTO chamados_suporte (usuario_id, categoria, assunto, mensagem) VALUES (?, ?, ?, ?)",
        (usuario["id"], categoria, assunto, mensagem),
    )
    logger.info("chamado_aberto", extra={"usuario_id": usuario["id"], "chamado_id": chamado_id})
    return chamado_id


def responder_chamado(usuario: dict, chamado_id: int, resposta: str) -> None:
    if not usuario.get("administrador"):
        raise HTTPException(403, "Só administradores respondem chamados.")
    if not resposta.strip():
        raise HTTPException(400, "Escreva a resposta.")
    if not db.consultar_um("SELECT id FROM chamados_suporte WHERE id = ?", (chamado_id,)):
        raise HTTPException(404, "Chamado não encontrado.")
    db.executar(
        "UPDATE chamados_suporte SET resposta = ?, respondido_em = CURRENT_TIMESTAMP WHERE id = ?",
        (resposta.strip(), chamado_id),
    )


def remover_chamado(usuario: dict, chamado_id: int) -> None:
    chamado = db.consultar_um("SELECT usuario_id FROM chamados_suporte WHERE id = ?", (chamado_id,))
    if not chamado:
        raise HTTPException(404, "Chamado não encontrado.")
    if chamado["usuario_id"] != usuario["id"] and not usuario.get("administrador"):
        raise HTTPException(403, "Você só pode remover os seus chamados.")
    db.executar("DELETE FROM chamados_suporte WHERE id = ?", (chamado_id,))
