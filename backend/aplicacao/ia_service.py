"""Informações sobre a IA em uso, mostradas na tela "Sobre o assistente IA"."""
from .. import config


def sobre_a_ia() -> dict:
    return {
        "provedor": "Google Gemini",
        "modelo": config.GEMINI_MODEL,
        "modelos_reserva": config.GEMINI_MODELOS_RESERVA,
        "modelo_embeddings": config.GEMINI_EMBED_MODEL,
        "tamanho_trecho": config.TAMANHO_TRECHO,
        "sobreposicao": config.SOBREPOSICAO,
        "top_k": config.TOP_K,
    }
