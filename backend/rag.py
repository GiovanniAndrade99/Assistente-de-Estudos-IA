"""Pipeline RAG (Retrieval-Augmented Generation), feito sem frameworks.

Indexação (upload de um PDF):
    PDF -> texto por página -> trechos (chunks) -> embeddings -> banco vetorial

Consulta (pergunta do aluno):
    pergunta -> embedding -> busca dos trechos mais parecidos (cosseno)
    -> prompt (trechos + pergunta) -> Gemini -> resposta com citações
"""
from pathlib import Path

import httpx
import pymupdf
from google import genai
from google.genai import types
from google.genai.errors import APIError

from . import config
from .prompts import SISTEMA_CHAT, montar_prompt_chat
from .vetores import BancoVetorial

_banco = BancoVetorial(config.PASTA_INDICE)
_cliente_gemini = None


def _gemini() -> genai.Client:
    """Cria o cliente do Gemini só quando for usado (dá um erro claro se faltar a chave)."""
    global _cliente_gemini
    if _cliente_gemini is None:
        if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "cole_sua_chave_aqui":
            raise RuntimeError("GEMINI_API_KEY não configurada. Veja o arquivo .env.example.")
        _cliente_gemini = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=config.TEMPO_LIMITE_SEGUNDOS * 1000,  # em milissegundos
                # O nível gratuito devolve 429 (limite por minuto) e 503 (modelo sobrecarregado)
                # com frequência; tenta de novo esperando 2s, 4s...
                retry_options=types.HttpRetryOptions(
                    attempts=3, initial_delay=2, max_delay=10, http_status_codes=[429, 503],
                ),
            ),
        )
    return _cliente_gemini


def gerar_conteudo(contents: str, configuracao: types.GenerateContentConfig):
    """Chama o Gemini tentando o modelo principal e, se falhar, os modelos reserva.

    Retorna (resposta, nome_do_modelo_usado).
    """
    modelos = [config.GEMINI_MODEL] + config.GEMINI_MODELOS_RESERVA
    ultimo_erro = None
    for modelo in modelos:
        try:
            resposta = _gemini().models.generate_content(
                model=modelo, contents=contents, config=configuracao,
            )
            return resposta, modelo
        except APIError as erro:
            # 404 = modelo descontinuado; 429 = sem cota; 5xx = sobrecarga
            if erro.code not in (404, 429) and erro.code < 500:
                raise
            ultimo_erro = erro
        except httpx.TimeoutException as erro:
            ultimo_erro = erro
        print(f"[gemini] {modelo} falhou ({ultimo_erro}); tentando o próximo modelo")
    if isinstance(ultimo_erro, APIError):
        raise ultimo_erro
    raise RuntimeError("O Gemini demorou demais para responder. Tente novamente em instantes.")


# ---------------------------------------------------------------- indexação

def extrair_paginas(caminho: Path) -> list[tuple[int, str]]:
    """Retorna [(numero_da_pagina, texto), ...], pulando páginas vazias."""
    paginas = []
    with pymupdf.open(caminho) as pdf:
        for numero, pagina in enumerate(pdf, start=1):
            # Sem PRESERVE_LIGATURES: "ﬁ" (um caractere só) vira "fi", senão a busca não casa as palavras
            texto = pagina.get_text(flags=pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES)
            texto = " ".join(texto.split())  # normaliza espaços
            if texto:
                paginas.append((numero, texto))
    return paginas


def dividir_em_trechos(texto: str) -> list[str]:
    """Divide o texto em pedaços de ~TAMANHO_TRECHO caracteres com sobreposição.

    Tenta cortar num espaço para não partir palavras no meio.
    """
    tamanho, sobreposicao = config.TAMANHO_TRECHO, config.SOBREPOSICAO
    trechos, inicio = [], 0
    while inicio < len(texto):
        fim = min(inicio + tamanho, len(texto))
        if fim < len(texto):
            espaco = texto.rfind(" ", inicio + tamanho // 2, fim)
            if espaco != -1:
                fim = espaco
        trechos.append(texto[inicio:fim].strip())
        if fim >= len(texto):
            break
        inicio = max(fim - sobreposicao, inicio + 1)
    return [t for t in trechos if t]


def gerar_embeddings(textos: list[str], tipo: str) -> list[list[float]]:
    """Transforma textos em vetores. tipo = RETRIEVAL_DOCUMENT ou RETRIEVAL_QUERY."""
    vetores = []
    for i in range(0, len(textos), 100):  # a API aceita até 100 textos por chamada
        resposta = _gemini().models.embed_content(
            model=config.GEMINI_EMBED_MODEL,
            contents=textos[i:i + 100],
            config=types.EmbedContentConfig(task_type=tipo),
        )
        vetores.extend(e.values for e in resposta.embeddings)
    return vetores


def caminho_do_pdf(disciplina_id: int, arquivo: str) -> Path:
    """Os PDFs ficam em data/uploads/<id da disciplina>/<arquivo>.pdf"""
    return config.PASTA_UPLOADS / str(disciplina_id) / Path(arquivo).name


def indexar_pdf(disciplina_id: int, arquivo: str) -> int:
    """Lê um PDF já salvo e guarda seus trechos no banco vetorial. Retorna quantos trechos."""
    remover_documento(disciplina_id, arquivo)  # se reenviarem o mesmo arquivo, substitui

    trechos = [
        {"texto": trecho, "arquivo": arquivo, "pagina": pagina, "disciplina_id": disciplina_id}
        for pagina, texto_pagina in extrair_paginas(caminho_do_pdf(disciplina_id, arquivo))
        for trecho in dividir_em_trechos(texto_pagina)
    ]
    if not trechos:
        raise ValueError("Não foi possível extrair texto do PDF (pode ser um PDF escaneado/imagem).")

    vetores = gerar_embeddings([t["texto"] for t in trechos], "RETRIEVAL_DOCUMENT")
    _banco.adicionar(vetores, trechos)
    return len(trechos)


def remover_documento(disciplina_id: int, arquivo: str | None = None) -> None:
    """Remove um arquivo da disciplina (ou todos, se arquivo=None) do banco vetorial."""
    _banco.remover(disciplina_id, arquivo)


# ---------------------------------------------------------------- consulta

def buscar(pergunta: str, disciplina_id: int, k: int = config.TOP_K) -> list[dict]:
    """Retorna os k trechos da disciplina mais parecidos com a pergunta."""
    if len(_banco) == 0:
        return []
    vetor = gerar_embeddings([pergunta], "RETRIEVAL_QUERY")[0]
    return _banco.buscar(vetor, k, disciplina_id)


def responder(pergunta: str, disciplina_id: int) -> dict:
    """Fluxo completo do RAG: busca os trechos e pede a resposta ao Gemini."""
    trechos = buscar(pergunta, disciplina_id)
    if not trechos:
        return {"resposta": "Esta disciplina ainda não tem materiais. Envie um PDF primeiro.", "fontes": []}

    resposta, modelo = gerar_conteudo(
        montar_prompt_chat(pergunta, trechos),
        types.GenerateContentConfig(
            system_instruction=SISTEMA_CHAT,
            temperature=0.2,  # baixa = respostas mais fiéis ao material
        ),
    )
    return {"resposta": resposta.text, "fontes": trechos, "modelo": modelo}
