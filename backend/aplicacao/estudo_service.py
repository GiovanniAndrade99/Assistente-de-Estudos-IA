"""Ferramentas de estudo: resumo, flashcards e simulado.

Diferente do chat (que usa RAG e manda só os trechos mais relevantes), aqui o
documento inteiro vai para o modelo, porque um resumo ou simulado precisa cobrir
todo o conteúdo. Isso aproveita a janela de contexto grande do Gemini.

Flashcards e simulado usam "saída estruturada": passamos um schema (classes
Pydantic abaixo) e o Gemini é obrigado a responder num JSON nesse formato,
que o frontend consegue montar direto na tela.

Simulado: o gabarito fica no servidor. O navegador recebe só perguntas e
alternativas, manda as respostas e recebe a correção, calculada aqui.
"""
import json

from fastapi import HTTPException
from pydantic import BaseModel
from google.genai import types

from .. import prompts
from ..erros import ErroDeUso
from ..infraestrutura import db, metricas, rag
from . import limite_service

# Limite de caracteres enviados ao modelo (~50 mil tokens), para não estourar a
# cota por minuto do nível gratuito em apostilas muito grandes.
LIMITE_CARACTERES = 200_000


class Flashcard(BaseModel):
    frente: str
    verso: str
    pagina: int


class Questao(BaseModel):
    pergunta: str
    alternativas: list[str]
    correta: int
    explicacao: str
    pagina: int


def texto_do_documento(disciplina_id: int, arquivo: str) -> tuple[str, bool]:
    """Texto do PDF com marcações [Página N]. Retorna (texto, foi_cortado)."""
    # Só documentos cadastrados na disciplina: não basta o arquivo existir na pasta
    documento = db.consultar_um("SELECT id, status FROM documentos WHERE disciplina_id = ? AND arquivo = ?",
                                (disciplina_id, arquivo))
    if not documento:
        raise ErroDeUso("Arquivo não encontrado nesta disciplina.", 404)
    if documento["status"] != "pronto":
        raise ErroDeUso("Este PDF ainda está sendo processado. Tente de novo quando terminar.", 409)
    paginas = [(l["pagina"], l["texto"]) for l in db.consultar(
        "SELECT pagina, texto FROM paginas_documento WHERE documento_id = ? ORDER BY pagina", (documento["id"],))]
    if not paginas:  # documento indexado antes do texto ser guardado
        caminho = rag.caminho_do_pdf(disciplina_id, arquivo)
        if not caminho.exists():
            raise ErroDeUso("Arquivo não encontrado nesta disciplina.", 404)
        paginas = rag.extrair_paginas(caminho)
    texto = "\n\n".join(f"[Página {n}]\n{t}" for n, t in paginas)
    if len(texto) > LIMITE_CARACTERES:
        return texto[:LIMITE_CARACTERES], True
    return texto, False


def _gerar(prompt: str, temperatura: float, schema=None):
    configuracao = types.GenerateContentConfig(
        system_instruction=prompts.SISTEMA_ESTUDO,
        temperature=temperatura,
    )
    if schema is not None:
        configuracao.response_mime_type = "application/json"
        configuracao.response_schema = schema
    return rag.gerar_conteudo(prompt, configuracao)


def _aviso(cortado: bool) -> str | None:
    if cortado:
        return "Documento muito grande: só o início foi usado."
    return None


def _limitar_estudo(usuario_id: int) -> None:
    limite_service.limitar(f"usuario:{usuario_id}", "estudo", limite=15, janela_minutos=5)


def resumir(disciplina_id: int, arquivo: str, usuario_id: int) -> dict:
    _limitar_estudo(usuario_id)
    documento, cortado = texto_do_documento(disciplina_id, arquivo)
    resposta, modelo = _gerar(prompts.PROMPT_RESUMO.format(documento=documento), temperatura=0.3)
    metricas.registrar("resumo")
    return {"arquivo": arquivo, "resumo": resposta.text, "aviso": _aviso(cortado), "modelo": modelo}


def gerar_flashcards(disciplina_id: int, arquivo: str, usuario_id: int, quantidade: int = 10) -> dict:
    _limitar_estudo(usuario_id)
    documento, cortado = texto_do_documento(disciplina_id, arquivo)
    prompt = prompts.PROMPT_FLASHCARDS.format(documento=documento, quantidade=quantidade)
    resposta, modelo = _gerar(prompt, temperatura=0.5, schema=list[Flashcard])
    cartoes = [c.model_dump() for c in resposta.parsed]
    metricas.registrar("flashcards")
    return {"arquivo": arquivo, "flashcards": cartoes, "aviso": _aviso(cortado), "modelo": modelo}


def gerar_simulado(disciplina_id: int, arquivo: str, usuario_id: int, quantidade: int = 5) -> dict:
    _limitar_estudo(usuario_id)
    documento, cortado = texto_do_documento(disciplina_id, arquivo)
    prompt = prompts.PROMPT_SIMULADO.format(documento=documento, quantidade=quantidade)
    resposta, modelo = _gerar(prompt, temperatura=0.5, schema=list[Questao])
    # Descarta questões malformadas (o modelo às vezes erra o número de alternativas)
    questoes = [
        q.model_dump() for q in resposta.parsed
        if len(q.alternativas) == 4 and 0 <= q.correta < 4
    ]
    if not questoes:
        raise ErroDeUso("Não foi possível montar o simulado. Tente de novo.", 502)
    metricas.registrar("simulado_gerado")
    simulado_id = db.executar(
        "INSERT INTO simulados (usuario_id, disciplina_id, arquivo, questoes_json, total) VALUES (?, ?, ?, ?, ?)",
        (usuario_id, disciplina_id, arquivo, json.dumps(questoes, ensure_ascii=False), len(questoes)),
    )
    return {
        "simulado_id": simulado_id,
        "arquivo": arquivo,
        # Sem gabarito, explicação nem página: só o que a pessoa precisa para responder
        "questoes": [{"pergunta": q["pergunta"], "alternativas": q["alternativas"]} for q in questoes],
        "aviso": _aviso(cortado),
        "modelo": modelo,
    }


# ---------------------------------------------------------------- correção do simulado

def corrigir_simulado(disciplina_id: int, simulado_id: int, usuario_id: int, respostas: list[int | None]) -> dict:
    simulado = db.consultar_um(
        "SELECT * FROM simulados WHERE id = ? AND disciplina_id = ? AND usuario_id = ?",
        (simulado_id, disciplina_id, usuario_id),
    )
    if not simulado:
        raise HTTPException(404, "Simulado não encontrado.")
    questoes = json.loads(simulado["questoes_json"])
    if len(respostas) != len(questoes):
        raise HTTPException(400, "Envie uma resposta (ou vazio) para cada questão.")
    correcao, acertos = [], 0
    for questao, marcada in zip(questoes, respostas):
        acertou = marcada == questao["correta"]
        acertos += acertou
        correcao.append({
            "marcada": marcada, "correta": questao["correta"], "acertou": acertou,
            "explicacao": questao["explicacao"], "pagina": questao["pagina"],
        })
    with db.conectar() as c:
        # Uma correção só: duas requisições ao mesmo tempo não geram duas notas
        corrigido = c.execute(
            """UPDATE simulados SET respostas_json = ?, acertos = ?, finalizado_em = CURRENT_TIMESTAMP
               WHERE id = ? AND finalizado_em IS NULL""",
            (json.dumps(respostas), acertos, simulado_id),
        ).rowcount
        if not corrigido:
            raise HTTPException(409, "Este simulado já foi corrigido.")
        c.execute(
            "INSERT INTO resultados_simulado (usuario_id, disciplina_id, arquivo, acertos, total) VALUES (?, ?, ?, ?, ?)",
            (usuario_id, disciplina_id, simulado["arquivo"], acertos, len(questoes)),
        )
    metricas.registrar("simulado_corrigido")
    return {"simulado_id": simulado_id, "acertos": acertos, "total": len(questoes), "correcao": correcao}


def meus_resultados_simulado(disciplina_id: int, usuario_id: int) -> list[dict]:
    return db.consultar(
        """SELECT arquivo, acertos, total, criado_em FROM resultados_simulado
           WHERE disciplina_id = ? AND usuario_id = ? ORDER BY criado_em DESC LIMIT 50""",
        (disciplina_id, usuario_id),
    )
