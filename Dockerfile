FROM python:3.12-slim

# Tesseract com português: OCR de PDFs escaneados
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY scripts ./scripts

# Usuário sem privilégios; data/ (banco, PDFs e índice) é o único diretório gravável
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/backups \
    && chown -R app:app /app/data /app/backups
USER app

EXPOSE 8002
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8002/api/health', timeout=4).status == 200 else 1)"]

# --no-access-log: o log de acesso do próprio app (JSON, sem IP) substitui o do uvicorn.
# --proxy-headers só confia em X-Forwarded-* vindos de FORWARDED_ALLOW_IPS (padrão 127.0.0.1).
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8002", "--no-access-log", "--proxy-headers"]
