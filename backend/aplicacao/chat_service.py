"""Regras de negócio do chat com o material (RAG).

Pergunta repetida na disciplina volta do cache (custo_service) sem chamar o Gemini e
sem gastar a cota diária; o histórico do professor registra a pergunta do mesmo jeito.
"""
import json
import logging

from fastapi import HTTPException

from .. import config
from ..erros import ErroDeUso
from ..infraestrutura import db, metricas, rag
from . import custo_service, limite_service
from .disciplinas_service import disciplina_ou_404

logger = logging.getLogger("chat")


def _validar(disciplina_id: int, pergunta: str, usuario_id: int) -> str:
    disciplina_ou_404(disciplina_id)
    pergunta = pergunta.strip()
    if not pergunta:
        raise HTTPException(400, "Pergunta vazia")
    limite_service.limitar(f"usuario:{usuario_id}", "chat", config.LIMITE_CHAT_5MIN, janela_minutos=5)
    return pergunta


def _com_documento_id(disciplina_id: int, fontes: list[dict]) -> list[dict]:
    """Acrescenta o id de cada documento citado, para a citação abrir o PDF na página."""
    ids = {l["arquivo"]: l["id"] for l in db.consultar(
        "SELECT id, arquivo FROM documentos WHERE disciplina_id = ?", (disciplina_id,))}
    return [{**f, "documento_id": ids.get(f["arquivo"])} for f in fontes]


def _guardar(usuario_id: int, disciplina_id: int, pergunta: str, resposta: str) -> None:
    db.executar(  # histórico usado no painel do professor
        "INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta) VALUES (?, ?, ?, ?)",
        (usuario_id, disciplina_id, pergunta, resposta),
    )
    registrar_pergunta(usuario_id)


def chat(disciplina_id: int, pergunta: str, usuario_id: int) -> dict:
    pergunta = _validar(disciplina_id, pergunta, usuario_id)
    chave = custo_service.chave_chat(disciplina_id, pergunta)
    resultado = custo_service.ler(chave)
    if resultado:
        resultado["cache"] = True
    else:
        custo_service.antes_de_chamar_ia(usuario_id)
        resultado = rag.responder(pergunta, disciplina_id)
        if resultado["fontes"]:
            custo_service.guardar(chave, disciplina_id, resultado)
    resultado["fontes"] = _com_documento_id(disciplina_id, resultado["fontes"])
    _guardar(usuario_id, disciplina_id, pergunta, resultado["resposta"])
    return resultado


def _evento(nome: str, dados) -> str:
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"


def chat_stream(disciplina_id: int, pergunta: str, usuario_id: int):
    """Prepara tudo que pode falhar com status HTTP (permissão, limites, cota, busca dos
    trechos) e devolve um gerador de eventos SSE: fontes, texto (pedaços), fim ou erro.
    A pergunta só é guardada no histórico quando a resposta termina."""
    pergunta = _validar(disciplina_id, pergunta, usuario_id)
    chave = custo_service.chave_chat(disciplina_id, pergunta)
    guardada = custo_service.ler(chave)
    if guardada:
        return _eventos_do_cache(disciplina_id, pergunta, usuario_id, guardada)
    custo_service.antes_de_chamar_ia(usuario_id)
    trechos = rag.buscar(pergunta, disciplina_id)
    fontes = _com_documento_id(disciplina_id, trechos)

    def eventos():
        yield _evento("fontes", fontes)
        if not trechos:
            yield _evento("texto", rag.SEM_MATERIAL)
            yield _evento("fim", {"resposta": rag.SEM_MATERIAL, "modelo": None})
            return
        partes = []
        try:
            pedacos, modelo = rag.responder_stream(pergunta, trechos)
            for pedaco in pedacos:
                partes.append(pedaco)
                yield _evento("texto", pedaco)
        except ErroDeUso as erro:
            yield _evento("erro", erro.mensagem)
            return
        except Exception as erro:  # o status HTTP (200) já foi enviado: o erro vai como evento
            logger.warning("chat_stream_falhou", extra={"erro": type(erro).__name__})
            yield _evento("erro", "O serviço de IA respondeu com erro. Tente novamente em instantes.")
            return
        resposta = "".join(partes)
        custo_service.guardar(chave, disciplina_id, {"resposta": resposta, "fontes": trechos, "modelo": modelo})
        _guardar(usuario_id, disciplina_id, pergunta, resposta)
        yield _evento("fim", {"resposta": resposta, "modelo": modelo})

    return eventos()


def _eventos_do_cache(disciplina_id: int, pergunta: str, usuario_id: int, guardada: dict):
    yield _evento("fontes", _com_documento_id(disciplina_id, guardada["fontes"]))
    yield _evento("texto", guardada["resposta"])
    _guardar(usuario_id, disciplina_id, pergunta, guardada["resposta"])
    yield _evento("fim", {"resposta": guardada["resposta"], "modelo": guardada.get("modelo"), "cache": True})


def registrar_pergunta(usuario_id: int) -> None:
    metricas.registrar("pergunta_chat")
    if db.consultar_um("SELECT COUNT(*) AS n FROM perguntas WHERE usuario_id = ?", (usuario_id,))["n"] == 1:
        metricas.registrar("primeira_pergunta")  # ativação: a pessoa usou o assistente pela primeira vez
