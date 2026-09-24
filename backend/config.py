"""Configurações do projeto, lidas do arquivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# "production" liga cookie seguro (HTTPS) e cabeçalho HSTS; em dev (http://localhost)
# isso quebraria o teste local, então o padrão é "development".
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

TAMANHO_MAX_UPLOAD_MB = int(os.getenv("TAMANHO_MAX_UPLOAD_MB", "20"))
DURACAO_SESSAO_SEGUNDOS = 60 * 60 * 24 * 7  # 7 dias

# Rate limit de login/cadastro (proteção contra força bruta)
LIMITE_TENTATIVAS_LOGIN = 5
JANELA_TENTATIVAS_LOGIN_MINUTOS = 15

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

# Modelos reserva: se o principal estiver sobrecarregado (503), sem cota (429)
# ou demorar demais, o app tenta o próximo da lista.
GEMINI_MODELOS_RESERVA = [
    m.strip() for m in os.getenv("GEMINI_MODELS_FALLBACK", "gemini-3.5-flash,gemini-3.1-flash-lite").split(",")
    if m.strip()
]
TEMPO_LIMITE_SEGUNDOS = 60  # por tentativa

PASTA_DADOS = RAIZ / "data"
PASTA_UPLOADS = PASTA_DADOS / "uploads"
PASTA_INDICE = PASTA_DADOS / "indice"
PASTA_FRONTEND = RAIZ / "frontend"

# Parâmetros do RAG (bons candidatos para experimentar e comparar no relatório)
TAMANHO_TRECHO = 1000   # caracteres por trecho (chunk)
SOBREPOSICAO = 200      # caracteres repetidos entre trechos vizinhos
TOP_K = 5               # quantos trechos são enviados ao modelo por pergunta

PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
PASTA_INDICE.mkdir(parents=True, exist_ok=True)
