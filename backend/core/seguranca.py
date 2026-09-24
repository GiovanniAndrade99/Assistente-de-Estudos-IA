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

ITERACOES_SENHA = 200_000


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES_SENHA)
    return f"{ITERACOES_SENHA}${sal.hex()}${h.hex()}"


def conferir_senha(senha: str, salvo: str) -> bool:
    iteracoes, sal_hex, hash_hex = salvo.split("$")
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), int(iteracoes))
    return hmac.compare_digest(h.hex(), hash_hex)  # comparação em tempo constante


def gerar_token_sessao() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
