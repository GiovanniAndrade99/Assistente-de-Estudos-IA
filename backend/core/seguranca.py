"""Funções puras de segurança: hash de senha e de token de sessão.

Sem dependência de FastAPI/banco — só stdlib, para poder ser testado e
entendido isoladamente (camada de domínio: não sabe nada sobre HTTP ou SQL).

Senhas: nunca são guardadas em texto puro. Guardamos um hash PBKDF2-SHA256 com
um "sal" aleatório por usuário e muitas iterações, o que torna ataques de força
bruta lentos. Formato salvo: "iteracoes$sal_hex$hash_hex".

Tokens de sessão: guardamos no banco só o hash SHA-256 do token, nunca o valor
bruto (que fica só no cookie do navegador). Assim, um dump do banco não dá a
um atacante sessões prontas para usar — o token em si já tem 256 bits de
entropia (secrets.token_urlsafe(32)), então isso não ajuda contra força bruta,
só reduz o estrago de um vazamento do banco.
"""
import hashlib
import hmac
import secrets

# OWASP recomenda 600 mil para PBKDF2-HMAC-SHA256. O contador faz parte do
# formato salvo, então hashes antigos continuam verificáveis e são atualizados
# no próximo login bem-sucedido.
ITERACOES_SENHA = 600_000


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES_SENHA)
    return f"{ITERACOES_SENHA}${sal.hex()}${h.hex()}"


def conferir_senha(senha: str, salvo: str) -> bool:
    try:
        iteracoes, sal_hex, hash_hex = salvo.split("$")
        iteracoes = int(iteracoes)
        # Recusa parâmetros corrompidos ou adulterados que poderiam causar
        # consumo excessivo de CPU ou aceitar um hash fraco.
        if not 1 <= iteracoes <= ITERACOES_SENHA or len(bytes.fromhex(sal_hex)) != 16:
            return False
        hash_salvo = bytes.fromhex(hash_hex)
        if len(hash_salvo) != hashlib.sha256().digest_size:
            return False
        hash_calculado = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), iteracoes)
        return hmac.compare_digest(hash_calculado, hash_salvo)
    except (ValueError, TypeError):
        return False


def gerar_token_sessao() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hmac_hex(segredo: bytes, valor: str) -> str:
    """HMAC-SHA256 em hexadecimal: pseudônimo estável enquanto o segredo não mudar."""
    return hmac.new(segredo, valor.encode(), hashlib.sha256).hexdigest()
