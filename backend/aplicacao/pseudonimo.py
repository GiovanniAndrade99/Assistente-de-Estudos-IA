"""Pseudônimos de IP e e-mail guardados só para limitar tentativas (LGPD, art. 6º, III e VII).

Com HMAC e um segredo do servidor (SEGREDO_APP), o banco não guarda o IP nem o
e-mail digitado, e quem tiver só o banco não consegue revertê-los testando
valores: um hash simples de IPv4 seria revertido tentando os 4 bilhões de endereços.
"""
import secrets

from .. import config
from ..core.seguranca import hmac_hex

# Sem SEGREDO_APP (só permitido fora de produção) usa um segredo aleatório por
# processo: os limites continuam funcionando, mas zeram quando o servidor reinicia.
_SEGREDO_DO_PROCESSO = secrets.token_bytes(32)


def chave(tipo: str, valor: str) -> str:
    segredo = config.SEGREDO_APP.encode() if config.SEGREDO_APP else _SEGREDO_DO_PROCESSO
    return f"{tipo}:{hmac_hex(segredo, f'{tipo}:{valor.strip().lower()}')}"
