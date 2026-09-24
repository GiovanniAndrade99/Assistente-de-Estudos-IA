"""Ferramentas de estudo: resumo, flashcards e simulado.

Diferente do chat (que usa RAG e manda só os trechos mais relevantes), aqui o
documento inteiro vai para o modelo, porque um resumo ou simulado precisa cobrir
todo o conteúdo. Isso aproveita a janela de contexto grande do Gemini.

Flashcards e simulado usam "saída estruturada": passamos um schema (classes
Pydantic abaixo) e o Gemini é obrigado a responder num JSON nesse formato,
que o frontend consegue montar direto na tela.
"""
from fastapi import HTTPException
from pydantic import BaseModel
from google.genai import types

from .. import prompts
from ..infraestrutura import db
from ..infraestrutura.rag import caminho_do_pdf, extrair_paginas, gerar_conteudo
from .disciplinas_service import disciplina_ou_404
from .documentos_service import nome_seguro

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
    caminho = caminho_do_pdf(disciplina_id, arquivo)
    if not caminho.exists():
        raise ValueError(f"Arquivo não encontrado: {arquivo}")
    texto = "\n\n".join(f"[Página {n}]\n{t}" for n, t in extrair_paginas(caminho))
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
    return gerar_conteudo(prompt, configuracao)


def _aviso(cortado: bool) -> str | None:
    if cortado:
        return "Documento muito grande: só o início foi usado."
    return None


def resumir(disciplina_id: int, arquivo: str) -> dict:
    documento, cortado = texto_do_documento(disciplina_id, arquivo)
    resposta, modelo = _gerar(prompts.PROMPT_RESUMO.format(documento=documento), temperatura=0.3)
    return {"arquivo": arquivo, "resumo": resposta.text, "aviso": _aviso(cortado), "modelo": modelo}


def gerar_flashcards(disciplina_id: int, arquivo: str, quantidade: int = 10) -> dict:
    documento, cortado = texto_do_documento(disciplina_id, arquivo)
    prompt = prompts.PROMPT_FLASHCARDS.format(documento=documento, quantidade=quantidade)
    resposta, modelo = _gerar(prompt, temperatura=0.5, schema=list[Flashcard])
    cartoes = [c.model_dump() for c in resposta.parsed]
    return {"arquivo": arquivo, "flashcards": cartoes, "aviso": _aviso(cortado), "modelo": modelo}


def gerar_simulado(disciplina_id: int, arquivo: str, quantidade: int = 5) -> dict:
    documento, cortado = texto_do_documento(disciplina_id, arquivo)
    prompt = prompts.PROMPT_SIMULADO.format(documento=documento, quantidade=quantidade)
    resposta, modelo = _gerar(prompt, temperatura=0.5, schema=list[Questao])
    # Descarta questões malformadas (o modelo às vezes erra o número de alternativas)
    questoes = [
        q.model_dump() for q in resposta.parsed
        if len(q.alternativas) == 4 and 0 <= q.correta < 4
    ]
    return {"arquivo": arquivo, "questoes": questoes, "aviso": _aviso(cortado), "modelo": modelo}


# ---------------------------------------------------------------- resultados do simulado

def salvar_resultado_simulado(disciplina_id: int, usuario_id: int, arquivo: str, acertos: int, total: int) -> None:
    disciplina_ou_404(disciplina_id)
    if acertos > total:
        raise HTTPException(400, "Acertos maior que o total.")
    db.executar(
        """INSERT INTO resultados_simulado (usuario_id, disciplina_id, arquivo, acertos, total)
           VALUES (?, ?, ?, ?, ?)""",
        (usuario_id, disciplina_id, nome_seguro(arquivo), acertos, total),
    )


def meus_resultados_simulado(disciplina_id: int, usuario_id: int) -> list[dict]:
    return db.consultar(
        """SELECT arquivo, acertos, total, criado_em FROM resultados_simulado
           WHERE disciplina_id = ? AND usuario_id = ? ORDER BY criado_em DESC LIMIT 50""",
        (disciplina_id, usuario_id),
    )
