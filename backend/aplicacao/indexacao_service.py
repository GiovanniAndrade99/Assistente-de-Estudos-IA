"""Indexação de PDFs em segundo plano.

O envio grava o arquivo e responde na hora (202); um único worker extrai o texto
(com OCR se preciso), gera os embeddings e troca os trechos no índice, atualizando
`documentos.status` e `documentos.progresso` para a barra de progresso da tela.

Um worker só: o índice vetorial é um arquivo único e a cota do Gemini é por minuto.
Nos testes (iniciar(sincrono=True)) a indexação roda na própria requisição.

`TRAVA_DOCUMENTOS` impede que remover um documento e terminar a indexação dele se
cruzem: sem ela, trechos de um PDF já removido poderiam voltar ao índice.
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from ..erros import ErroDeUso
from ..infraestrutura import db, rag

logger = logging.getLogger("indexacao")

TRAVA_DOCUMENTOS = threading.Lock()
_executor: ThreadPoolExecutor | None = None


def iniciar(sincrono: bool = False) -> None:
    global _executor
    if not sincrono and _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="indexacao")


def parar() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


def enfileirar(documento_id: int) -> None:
    if _executor is None:
        indexar_documento(documento_id)
    else:
        _executor.submit(indexar_documento, documento_id)


def retomar_pendentes() -> int:
    """Na subida do servidor: documentos que estavam sendo processados quando ele parou
    voltam para a fila, e documentos 'pronto' sem trechos no índice são refeitos."""
    pendentes = db.consultar("SELECT id, disciplina_id, arquivo, status FROM documentos")
    total = 0
    for doc in pendentes:
        sem_trechos = doc["status"] == "pronto" and not rag.banco().tem_trechos(doc["disciplina_id"], doc["arquivo"])
        if doc["status"] == "processando" or sem_trechos:
            db.executar("UPDATE documentos SET status = 'processando', progresso = 0, erro = NULL WHERE id = ?",
                        (doc["id"],))
            enfileirar(doc["id"])
            total += 1
    return total


def _progresso(documento_id: int, inicio: int, fim: int):
    ultimo = [-1]

    def atualizar(feitas: int, total: int) -> None:
        valor = inicio + (fim - inicio) * feitas // max(total, 1)
        if valor >= ultimo[0] + 5 or feitas == total:  # no máximo uma escrita a cada 5%
            ultimo[0] = valor
            db.executar("UPDATE documentos SET progresso = ? WHERE id = ?", (valor, documento_id))
    return atualizar


def _ainda_e_o_mesmo(documento: dict) -> bool:
    """O documento não foi removido nem reenviado enquanto era indexado."""
    atual = db.consultar_um("SELECT versao FROM documentos WHERE id = ?", (documento["id"],))
    return atual is not None and atual["versao"] == documento["versao"]


def indexar_documento(documento_id: int) -> None:
    documento = db.consultar_um("SELECT * FROM documentos WHERE id = ?", (documento_id,))
    if not documento:
        return
    disciplina_id, arquivo = documento["disciplina_id"], documento["arquivo"]
    try:
        paginas = rag.extrair_paginas(rag.caminho_do_pdf(disciplina_id, arquivo),
                                      _progresso(documento_id, 0, 40))
        trechos = rag.montar_trechos(disciplina_id, arquivo, paginas)
        vetores = rag.gerar_embeddings_com_progresso(trechos, _progresso(documento_id, 40, 99))
        with TRAVA_DOCUMENTOS:
            if not _ainda_e_o_mesmo(documento):
                return
            rag.banco().substituir(disciplina_id, arquivo, vetores, trechos)
            with db.conectar() as c:
                c.execute("DELETE FROM paginas_documento WHERE documento_id = ?", (documento_id,))
                c.executemany("INSERT INTO paginas_documento (documento_id, pagina, texto) VALUES (?, ?, ?)",
                              [(documento_id, numero, texto) for numero, texto in paginas])
                c.execute("""UPDATE documentos SET status = 'pronto', progresso = 100, erro = NULL, trechos = ?
                             WHERE id = ?""", (len(trechos), documento_id))
        logger.info("documento_indexado", extra={"documento_id": documento_id, "trechos": len(trechos)})
    except ErroDeUso as erro:
        _marcar_erro(documento, erro.mensagem)
    except Exception:
        logger.exception("indexacao_falhou", extra={"documento_id": documento_id})
        _marcar_erro(documento, "Não foi possível processar o PDF. Tente enviar de novo em alguns minutos.")


def _marcar_erro(documento: dict, mensagem: str) -> None:
    with TRAVA_DOCUMENTOS:
        if _ainda_e_o_mesmo(documento):
            db.executar("UPDATE documentos SET status = 'erro', erro = ? WHERE id = ?", (mensagem, documento["id"]))
