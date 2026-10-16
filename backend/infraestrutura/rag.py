"""Pipeline RAG (Retrieval-Augmented Generation), feito sem frameworks.

Indexação (upload de um PDF):
    PDF -> texto por página -> trechos (chunks) -> embeddings -> banco vetorial

Consulta (pergunta do aluno):
    pergunta -> embedding -> busca dos trechos mais parecidos (cosseno)
    -> prompt (trechos + pergunta) -> Gemini -> resposta com citações

PDF escaneado: quando uma página quase não tem texto, o texto é lido por OCR
(Tesseract, via PyMuPDF), se o Tesseract com os idiomas configurados existir.
"""
import logging
from pathlib import Path

import httpx
import pymupdf
from google import genai
from google.genai import types
from google.genai.errors import APIError

from .. import config
from ..erros import ErroDeUso
from ..prompts import SISTEMA_CHAT, montar_prompt_chat
from . import metricas
from .vetores import BancoVetorial

logger = logging.getLogger("rag")

_banco: BancoVetorial | None = None
_cliente_gemini = None
_tessdata: str | None | bool = False  # False = ainda não procurado


def banco() -> BancoVetorial:
    """Índice vetorial, carregado do disco no primeiro uso (não na importação)."""
    global _banco
    if _banco is None:
        _banco = BancoVetorial(config.PASTA_INDICE)
    return _banco


def _gemini() -> genai.Client:
    """Cria o cliente do Gemini só quando for usado (dá um erro claro se faltar a chave)."""
    global _cliente_gemini
    if _cliente_gemini is None:
        if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "cole_sua_chave_aqui":
            logger.error("gemini_sem_chave")  # o operador vê no log: falta GEMINI_API_KEY no .env
            raise ErroDeUso("O assistente de IA não está configurado no servidor. Avise o administrador.", 503)
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


def registrar_uso(resposta) -> None:
    """Conta chamadas e tokens do Gemini nas métricas diárias (custo da API)."""
    uso = getattr(resposta, "usage_metadata", None)
    metricas.registrar("chamadas_ia")
    if uso:
        metricas.registrar("tokens_entrada", getattr(uso, "prompt_token_count", 0) or 0)
        saida = (getattr(uso, "candidates_token_count", 0) or 0) + (getattr(uso, "thoughts_token_count", 0) or 0)
        metricas.registrar("tokens_saida", saida)


def _sem_ferramentas(configuracao: types.GenerateContentConfig | None):
    """O app não usa function calling; desligado, o SDK não registra avisos a cada chamada."""
    desligado = types.AutomaticFunctionCallingConfig(disable=True)
    if configuracao is None:
        return types.GenerateContentConfig(automatic_function_calling=desligado)
    return configuracao.model_copy(update={"automatic_function_calling": desligado})


def gerar_conteudo(contents: str, configuracao: types.GenerateContentConfig):
    """Chama o Gemini tentando o modelo principal e, se falhar, os modelos reserva.

    Retorna (resposta, nome_do_modelo_usado).
    """
    configuracao = _sem_ferramentas(configuracao)
    modelos = [config.GEMINI_MODEL] + config.GEMINI_MODELOS_RESERVA
    ultimo_erro = None
    for modelo in modelos:
        try:
            resposta = _gemini().models.generate_content(
                model=modelo, contents=contents, config=configuracao,
            )
            registrar_uso(resposta)
            return resposta, modelo
        except APIError as erro:
            # 404 = modelo descontinuado; 429 = sem cota; 5xx = sobrecarga
            if erro.code not in (404, 429) and erro.code < 500:
                raise
            ultimo_erro = erro
        except httpx.TimeoutException as erro:
            ultimo_erro = erro
        logger.warning(
            "modelo_gemini_falhou",
            extra={"modelo": modelo, "erro": str(ultimo_erro)},
        )
    if isinstance(ultimo_erro, APIError):
        raise ultimo_erro
    raise ErroDeUso("O Gemini demorou demais para responder. Tente novamente em instantes.", 504)


def gerar_conteudo_stream(contents: str, configuracao: types.GenerateContentConfig):
    """Como gerar_conteudo, mas devolve (pedaços_de_texto, modelo). Troca de modelo só
    antes do primeiro pedaço: depois disso o texto já está chegando na tela."""
    configuracao = _sem_ferramentas(configuracao)
    modelos = [config.GEMINI_MODEL] + config.GEMINI_MODELOS_RESERVA
    ultimo_erro = None
    for modelo in modelos:
        try:
            fluxo = iter(_gemini().models.generate_content_stream(
                model=modelo, contents=contents, config=configuracao,
            ))
            primeiro = next(fluxo, None)
        except APIError as erro:
            if erro.code not in (404, 429) and erro.code < 500:
                raise
            ultimo_erro = erro
        except httpx.TimeoutException as erro:
            ultimo_erro = erro
        else:
            return _pedacos(primeiro, fluxo), modelo
        logger.warning("modelo_gemini_falhou", extra={"modelo": modelo, "erro": str(ultimo_erro)})
    if isinstance(ultimo_erro, APIError):
        raise ultimo_erro
    raise ErroDeUso("O Gemini demorou demais para responder. Tente novamente em instantes.", 504)


def _pedacos(primeiro, fluxo):
    ultimo = None
    for parte in _encadear(primeiro, fluxo):
        ultimo = parte
        if parte.text:
            yield parte.text
    if ultimo is not None:
        registrar_uso(ultimo)  # o último pedaço traz o total de tokens


def _encadear(primeiro, fluxo):
    if primeiro is not None:
        yield primeiro
    yield from fluxo


# ---------------------------------------------------------------- indexação

_FLAGS_TEXTO = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
MINIMO_DE_TEXTO = 20  # abaixo disso a página é tratada como imagem (PDF escaneado)


def tessdata() -> str | None:
    """Pasta dos idiomas do Tesseract, procurada uma vez só (cada busca abre um processo)."""
    global _tessdata
    if _tessdata is False:
        if not config.OCR_HABILITADO:
            _tessdata = None
        else:
            try:
                _tessdata = config.TESSDATA or pymupdf.get_tessdata()
            except Exception:  # Tesseract não instalado
                _tessdata = None
            if not _tessdata:
                logger.warning("ocr_indisponivel")
    return _tessdata or None


def _texto_da_pagina(pagina, numero: int) -> str:
    # Sem PRESERVE_LIGATURES: "ﬁ" (um caractere só) vira "fi", senão a busca não casa as palavras
    texto = " ".join(pagina.get_text(flags=_FLAGS_TEXTO).split())
    if len(texto) >= MINIMO_DE_TEXTO or numero > config.OCR_MAX_PAGINAS or not pagina.get_images():
        return texto
    pasta_idiomas = tessdata()
    if not pasta_idiomas:
        return texto
    try:
        camada = pagina.get_textpage_ocr(language=config.OCR_IDIOMAS, dpi=config.OCR_DPI, full=True,
                                         tessdata=pasta_idiomas)
        return " ".join(pagina.get_text(textpage=camada, flags=_FLAGS_TEXTO).split())
    except Exception:
        logger.warning("ocr_falhou", extra={"pagina": numero})
        return texto


def extrair_paginas(caminho: Path, progresso=None) -> list[tuple[int, str]]:
    """Retorna [(numero_da_pagina, texto), ...], pulando páginas vazias.
    `progresso(feitas, total)` é chamado a cada página (para a barra de progresso)."""
    paginas = []
    with pymupdf.open(caminho) as pdf:
        total = len(pdf)
        for numero, pagina in enumerate(pdf, start=1):
            texto = _texto_da_pagina(pagina, numero)
            if texto:
                paginas.append((numero, texto))
            if progresso:
                progresso(numero, total)
    return paginas


def contar_paginas(conteudo: bytes) -> int:
    """Confere se os bytes são um PDF que abre e devolve o número de páginas."""
    if not conteudo.startswith(b"%PDF-"):
        raise ErroDeUso("O arquivo não é um PDF válido.")
    try:
        with pymupdf.open(stream=conteudo, filetype="pdf") as pdf:
            return len(pdf)
    except Exception as erro:
        raise ErroDeUso("Não foi possível abrir o PDF. Ele pode estar corrompido ou protegido por senha.") from erro


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


def montar_trechos(disciplina_id: int, arquivo: str, paginas: list[tuple[int, str]]) -> list[dict]:
    trechos = [
        {"texto": trecho, "arquivo": arquivo, "pagina": pagina, "disciplina_id": disciplina_id}
        for pagina, texto_pagina in paginas
        for trecho in dividir_em_trechos(texto_pagina)
    ]
    if not trechos:
        raise ErroDeUso("Não foi possível extrair texto do PDF. Se ele for escaneado, o OCR não encontrou "
                        "texto legível.")
    return trechos


def gerar_embeddings_com_progresso(trechos: list[dict], progresso=None) -> list[list[float]]:
    vetores = []
    for i in range(0, len(trechos), 100):
        vetores.extend(gerar_embeddings([t["texto"] for t in trechos[i:i + 100]], "RETRIEVAL_DOCUMENT"))
        if progresso:
            progresso(len(vetores), len(trechos))
    return vetores


def caminho_do_pdf(disciplina_id: int, arquivo: str) -> Path:
    """Os PDFs ficam em data/uploads/<id da disciplina>/<arquivo>.pdf"""
    return config.PASTA_UPLOADS / str(disciplina_id) / Path(arquivo).name


def indexar_pdf(disciplina_id: int, arquivo: str) -> int:
    """Lê um PDF já salvo e guarda seus trechos no banco vetorial, de uma vez (usado por
    scripts). Se o arquivo já estava indexado, os trechos antigos só saem quando os
    novos estão prontos. Retorna quantos trechos."""
    paginas = extrair_paginas(caminho_do_pdf(disciplina_id, arquivo))
    trechos = montar_trechos(disciplina_id, arquivo, paginas)
    vetores = gerar_embeddings_com_progresso(trechos)
    banco().substituir(disciplina_id, arquivo, vetores, trechos)
    return len(trechos)


def remover_documento(disciplina_id: int, arquivo: str | None = None) -> None:
    """Remove um arquivo da disciplina (ou todos, se arquivo=None) do banco vetorial."""
    banco().remover(disciplina_id, arquivo)


# ---------------------------------------------------------------- consulta

def buscar(pergunta: str, disciplina_id: int, k: int = config.TOP_K) -> list[dict]:
    """Retorna os k trechos da disciplina mais parecidos com a pergunta."""
    if len(banco()) == 0:
        return []
    vetor = gerar_embeddings([pergunta], "RETRIEVAL_QUERY")[0]
    return banco().buscar(vetor, k, disciplina_id)


SEM_MATERIAL = "Esta disciplina ainda não tem materiais. Envie um PDF primeiro."


def _configuracao_chat() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SISTEMA_CHAT,
        temperature=0.2,  # baixa = respostas mais fiéis ao material
    )


def responder(pergunta: str, disciplina_id: int) -> dict:
    """Fluxo completo do RAG: busca os trechos e pede a resposta ao Gemini."""
    trechos = buscar(pergunta, disciplina_id)
    if not trechos:
        return {"resposta": SEM_MATERIAL, "fontes": []}
    resposta, modelo = gerar_conteudo(montar_prompt_chat(pergunta, trechos), _configuracao_chat())
    return {"resposta": resposta.text, "fontes": trechos, "modelo": modelo}


def responder_stream(pergunta: str, trechos: list[dict]):
    """Pedaços da resposta conforme o Gemini gera. Devolve (pedaços, modelo)."""
    return gerar_conteudo_stream(montar_prompt_chat(pergunta, trechos), _configuracao_chat())
