"""Logging estruturado (JSON) para todo o backend.

Cada linha de log vai para stdout como um objeto JSON com timestamp, nível,
logger, mensagem e o `request_id` da requisição em andamento (lido do
ContextVar de middlewares/observabilidade.py) — assim qualquer linha pode ser
correlacionada com uma chamada específica do frontend.

Nunca logar segredos: senha, token de sessão (bruto ou com hash) e a chave do
Gemini não devem aparecer em nenhum `extra={...}` passado ao logger, mesmo em
nível DEBUG.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from ..middlewares.observabilidade import request_id_var

# Atributos que já existem em todo LogRecord "puro" (sem extra); qualquer
# outro atributo presente é considerado dado extra a incluir no JSON.
_ATRIBUTOS_PADRAO = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class FormatadorJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in _ATRIBUTOS_PADRAO}
        if record.exc_info:
            extras["exception"] = self.formatException(record.exc_info)
        dados.update(extras)
        return json.dumps(dados, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    manipulador = logging.StreamHandler(sys.stdout)
    manipulador.setFormatter(FormatadorJSON())
    logging.basicConfig(level=nivel, handlers=[manipulador], force=True)
    # Bibliotecas de terceiros barulhentas em INFO (httpx faz 1 log por chamada ao Gemini)
    logging.getLogger("httpx").setLevel(logging.WARNING)
