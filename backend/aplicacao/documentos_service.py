"""Regras de negócio de documentos (PDFs) das disciplinas.

O envio só grava o arquivo e responde; a indexação (texto, OCR, embeddings) roda em
segundo plano (aplicacao/indexacao_service.py) e a tela acompanha pelo status.
"""
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .. import config
from ..infraestrutura import db, metricas, rag
from . import indexacao_service, limite_service
from .disciplinas_service import disciplina_ou_404

_TAMANHO_CHUNK = 1024 * 1024  # 1 MiB por leitura


def nome_seguro(arquivo: str) -> str:
    return Path(arquivo).name  # evita caminhos como ../../


def listar_documentos(disciplina_id: int, usuario_id: int) -> list[dict]:
    disciplina_ou_404(disciplina_id)
    return db.consultar(
        """SELECT doc.id, doc.arquivo, doc.trechos, doc.criado_em, u.nome AS enviado_por,
                  doc.status, doc.progresso, doc.erro, doc.alerta_instrucoes,
                  (c.documento_id IS NOT NULL) AS concluida
           FROM documentos doc JOIN usuarios u ON u.id = doc.enviado_por
           LEFT JOIN aulas_concluidas c ON c.documento_id = doc.id AND c.usuario_id = ?
           WHERE doc.disciplina_id = ? ORDER BY doc.arquivo""",
        (usuario_id, disciplina_id),
    )


def caminho_para_leitura(disciplina_id: int, documento_id: int) -> tuple:
    """Arquivo do PDF de uma disciplina, para abrir na página citada."""
    documento = db.consultar_um("SELECT arquivo FROM documentos WHERE id = ? AND disciplina_id = ?",
                                (documento_id, disciplina_id))
    if not documento:
        raise HTTPException(404, "Documento não encontrado.")
    caminho = rag.caminho_do_pdf(disciplina_id, documento["arquivo"])
    if not caminho.exists():
        raise HTTPException(404, "Documento não encontrado.")
    return caminho, documento["arquivo"]


def _ler_com_limite(arquivo: UploadFile, limite_mb: int) -> bytes:
    limite_bytes = limite_mb * 1024 * 1024
    partes, total = [], 0
    while True:
        pedaco = arquivo.file.read(_TAMANHO_CHUNK)
        if not pedaco:
            break
        total += len(pedaco)
        if total > limite_bytes:
            raise HTTPException(400, f"Arquivo maior que o limite de {limite_mb}MB.")
        partes.append(pedaco)
    return b"".join(partes)


def enviar_documento(disciplina_id: int, arquivo: UploadFile, usuario_id: int) -> dict:
    disciplina_ou_404(disciplina_id)
    limite_service.limitar(f"usuario:{usuario_id}", "upload_documento", limite=10, janela_minutos=5)
    nome = nome_seguro(arquivo.filename or "")
    if not nome.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um arquivo .pdf")

    conteudo = _ler_com_limite(arquivo, config.TAMANHO_MAX_UPLOAD_MB)
    rag.contar_paginas(conteudo)  # confere já que é um PDF que abre; o resto vai para segundo plano

    with indexacao_service.TRAVA_DOCUMENTOS:
        existente = db.consultar_um("SELECT status FROM documentos WHERE disciplina_id = ? AND arquivo = ?",
                                    (disciplina_id, nome))
        if existente and existente["status"] == "processando":
            raise HTTPException(409, "Este PDF ainda está sendo processado. Espere terminar para enviar de novo.")
        destino = rag.caminho_do_pdf(disciplina_id, nome)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_name(destino.name + ".enviando")
        temporario.write_bytes(conteudo)
        os.replace(temporario, destino)
        db.executar(
            """INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por, status, progresso)
               VALUES (?, ?, 0, ?, 'processando', 0)
               ON CONFLICT (disciplina_id, arquivo) DO UPDATE
               SET enviado_por = excluded.enviado_por, criado_em = CURRENT_TIMESTAMP, status = 'processando',
                   progresso = 0, erro = NULL, alerta_instrucoes = 0, versao = versao + 1""",
            (disciplina_id, nome, usuario_id),
        )
        # No reenvio o UPSERT atualiza a linha existente e não devolve o id dela
        documento_id = db.consultar_um("SELECT id FROM documentos WHERE disciplina_id = ? AND arquivo = ?",
                                       (disciplina_id, nome))["id"]
    metricas.registrar("upload_pdf")
    indexacao_service.enfileirar(documento_id)
    return {"id": documento_id, "arquivo": nome, "status": "processando"}


def remover_documento(disciplina_id: int, arquivo: str) -> None:
    # Quem pode chamar esta função já foi conferido na rota (dependencias.
    # professor_da_disciplina): só o professor dono da disciplina, ou admin.
    nome = nome_seguro(arquivo)
    # Com a trava, uma indexação em andamento não devolve os trechos ao índice depois
    with indexacao_service.TRAVA_DOCUMENTOS:
        db.executar("DELETE FROM documentos WHERE disciplina_id = ? AND arquivo = ?", (disciplina_id, nome))
        rag.remover_documento(disciplina_id, nome)
        rag.caminho_do_pdf(disciplina_id, nome).unlink(missing_ok=True)
