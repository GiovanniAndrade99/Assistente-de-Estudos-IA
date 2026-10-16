"""Controle de custo da IA: cota diária por pessoa, teto diário do sistema e cache.

Cache: respostas do chat e resumos ficam guardados por disciplina, sem nenhum dado
de quem perguntou. A chave é um hash (SHA-256) da disciplina, da versão do índice,
da versão dos prompts, do modelo e da pergunta normalizada; a pergunta em si não é
gravada. Pergunta repetida na mesma disciplina volta do cache sem chamar o Gemini e
sem gastar a cota. PDF novo ou removido sobe `disciplinas.versao_indice` e apaga o
cache da disciplina.
"""
import hashlib
import json
import re

from .. import config, prompts
from ..erros import ErroDeUso
from ..infraestrutura import db, metricas
from . import limite_service


def _normalizar(pergunta: str) -> str:
    """"O que é um algoritmo?" e "o que é um  algoritmo" viram a mesma chave."""
    return re.sub(r"\s+", " ", pergunta.lower()).strip(" ?!.")


def _hash(*partes) -> str:
    return hashlib.sha256("\x1f".join(str(p) for p in partes).encode("utf-8")).hexdigest()


def chave_chat(disciplina_id: int, pergunta: str) -> str:
    versao = db.consultar_um("SELECT versao_indice FROM disciplinas WHERE id = ?", (disciplina_id,))["versao_indice"]
    return _hash("chat", disciplina_id, versao, prompts.VERSAO_PROMPTS, config.GEMINI_MODEL, _normalizar(pergunta))


def chave_resumo(disciplina_id: int, arquivo: str) -> str:
    documento = db.consultar_um("SELECT id, versao FROM documentos WHERE disciplina_id = ? AND arquivo = ?",
                                (disciplina_id, arquivo))
    return _hash("resumo", disciplina_id, documento["id"], documento["versao"], prompts.VERSAO_PROMPTS,
                 config.GEMINI_MODEL)


def ler(chave: str) -> dict | None:
    if config.CACHE_RESPOSTAS_DIAS <= 0:
        return None
    linha = db.consultar_um(
        "SELECT dados_json FROM cache_respostas WHERE chave = ? AND criado_em > datetime('now', ?)",
        (chave, f"-{config.CACHE_RESPOSTAS_DIAS} days"),
    )
    if not linha:
        return None
    metricas.registrar("respostas_do_cache")
    return json.loads(linha["dados_json"])


def guardar(chave: str, disciplina_id: int, dados: dict) -> None:
    if config.CACHE_RESPOSTAS_DIAS <= 0:
        return
    db.executar(
        """INSERT INTO cache_respostas (chave, disciplina_id, dados_json) VALUES (?, ?, ?)
           ON CONFLICT (chave) DO UPDATE SET dados_json = excluded.dados_json, criado_em = CURRENT_TIMESTAMP""",
        (chave, disciplina_id, json.dumps(dados, ensure_ascii=False)),
    )


def invalidar_disciplina(conexao, disciplina_id: int) -> None:
    """Chamado na mesma transação que muda os documentos da disciplina."""
    conexao.execute("UPDATE disciplinas SET versao_indice = versao_indice + 1 WHERE id = ?", (disciplina_id,))
    conexao.execute("DELETE FROM cache_respostas WHERE disciplina_id = ?", (disciplina_id,))


def antes_de_chamar_ia(usuario_id: int) -> None:
    """Teto do sistema e cota diária da pessoa. Só para pedidos que vão mesmo ao Gemini."""
    if config.TETO_TOKENS_DIA > 0 and metricas.tokens_hoje() >= config.TETO_TOKENS_DIA:
        raise ErroDeUso("O limite diário de uso da IA do sistema foi atingido. Ela volta amanhã; "
                        "respostas já dadas antes continuam disponíveis.", 503)
    usuario = db.consultar_um("SELECT tipo, administrador FROM usuarios WHERE id = ?", (usuario_id,))
    professor = usuario["tipo"] == "professor" or usuario["administrador"]
    cota = config.COTA_IA_DIA_PROFESSOR if professor else config.COTA_IA_DIA_ALUNO
    if cota > 0:
        limite_service.limitar(
            f"usuario:{usuario_id}", "cota_ia_dia", cota, 24 * 60,
            mensagem=f"Você chegou ao limite de {cota} pedidos à IA em 24 horas. "
                     "Perguntas repetidas continuam respondendo; o limite libera aos poucos.",
        )
