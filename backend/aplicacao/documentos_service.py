"""Regras de negócio de documentos (PDFs) das disciplinas."""
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .. import config
from ..infraestrutura import db, rag
from .disciplinas_service import disciplina_ou_404

_TAMANHO_CHUNK = 1024 * 1024  # 1 MiB por leitura


def nome_seguro(arquivo: str) -> str:
    return Path(arquivo).name  # evita caminhos como ../../


def listar_documentos(disciplina_id: int, usuario_id: int) -> list[dict]:
    disciplina_ou_404(disciplina_id)
    return db.consultar(
        """SELECT doc.id, doc.arquivo, doc.trechos, doc.criado_em, u.nome AS enviado_por,
                  (c.documento_id IS NOT NULL) AS concluida
           FROM documentos doc JOIN usuarios u ON u.id = doc.enviado_por
           LEFT JOIN aulas_concluidas c ON c.documento_id = doc.id AND c.usuario_id = ?
           WHERE doc.disciplina_id = ? ORDER BY doc.arquivo""",
        (usuario_id, disciplina_id),
    )


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
    nome = nome_seguro(arquivo.filename or "")
    if not nome.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um arquivo .pdf")

    conteudo = _ler_com_limite(arquivo, config.TAMANHO_MAX_UPLOAD_MB)
    destino = rag.caminho_do_pdf(disciplina_id, nome)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    try:
        trechos = rag.indexar_pdf(disciplina_id, nome)
    except Exception:
        destino.unlink(missing_ok=True)
        raise

    db.executar(
        """INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por) VALUES (?, ?, ?, ?)
           ON CONFLICT (disciplina_id, arquivo) DO UPDATE
           SET trechos = excluded.trechos, enviado_por = excluded.enviado_por, criado_em = CURRENT_TIMESTAMP""",
        (disciplina_id, nome, trechos, usuario_id),
    )
    return {"arquivo": nome, "trechos": trechos}


def remover_documento(disciplina_id: int, arquivo: str) -> None:
    nome = nome_seguro(arquivo)
    rag.remover_documento(disciplina_id, nome)
    rag.caminho_do_pdf(disciplina_id, nome).unlink(missing_ok=True)
    db.executar("DELETE FROM documentos WHERE disciplina_id = ? AND arquivo = ?", (disciplina_id, nome))
