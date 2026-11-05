"""Regras de negócio de cadastro, login e sessões.

Sessões: no login geramos um token aleatório de 256 bits (secrets.token_urlsafe),
enviamos ao navegador num cookie HttpOnly (o JavaScript da página não consegue
lê-lo, o que protege contra roubo de sessão por XSS) e guardamos no banco só o
hash SHA-256 do token — nunca o valor bruto (ver core/seguranca.py). A sessão
expira em config.DURACAO_SESSAO_SEGUNDOS, tanto no cookie quanto no banco.

Rate limit: 5 tentativas de login com falha por e-mail em 15 minutos (config)
bloqueiam novas tentativas com 429 — proteção simples contra força bruta.
Fica no banco (não em memória) para sobreviver ao `--reload` do uvicorn e
funcionar igual com múltiplos processos/workers.
"""
import hashlib
import logging
import re
import secrets
import sqlite3

from fastapi import HTTPException

from .. import config
from ..core.seguranca import conferir_senha, gerar_hash_senha, gerar_token_sessao, hash_token
from ..infraestrutura import db
from ..infraestrutura.email import enviar_email
from . import disciplinas_service

logger = logging.getLogger("auth")

NOME_COOKIE = "sessao"


# ---------------------------------------------------------------- rate limit
#
# As comparações de data usam as funções de data do próprio SQLite
# (`datetime('now', ...)`), não `datetime.now().isoformat()` do Python: as
# colunas `criado_em`/`expires_at` são preenchidas por `CURRENT_TIMESTAMP` do
# SQLite (formato "AAAA-MM-DD HH:MM:SS", sem fuso), que não é comparável como
# string com o formato do Python (com "T" e "+00:00") — misturar os dois faz
# a comparação de string dar sempre falso/verdadeiro pelo caractere errado.

def _limpar_tentativas_antigas(c) -> None:
    c.execute(
        "DELETE FROM tentativas_login WHERE criado_em <= datetime('now', ?)",
        (f"-{config.JANELA_TENTATIVAS_LOGIN_MINUTOS} minutes",),
    )


def _verificar_rate_limit(email: str) -> None:
    total = db.consultar_um(
        "SELECT COUNT(*) AS n FROM tentativas_login WHERE email = ? AND criado_em > datetime('now', ?)",
        (email, f"-{config.JANELA_TENTATIVAS_LOGIN_MINUTOS} minutes"),
    )["n"]
    if total >= config.LIMITE_TENTATIVAS_LOGIN:
        raise HTTPException(429, "Muitas tentativas com senha incorreta. Tente novamente em alguns minutos.")


def _registrar_tentativa_falha(email: str) -> None:
    with db.conectar() as c:
        _limpar_tentativas_antigas(c)
        c.execute("INSERT INTO tentativas_login (email) VALUES (?)", (email,))


# ---------------------------------------------------------------- sessão

def _iniciar_sessao(usuario_id: int) -> tuple[str, int]:
    """Cria uma sessão nova. Retorna (token_bruto_para_o_cookie, duracao_em_segundos)."""
    token = gerar_token_sessao()
    db.executar(
        "INSERT INTO sessoes (token, usuario_id, expires_at) VALUES (?, ?, datetime('now', ?))",
        (hash_token(token), usuario_id, f"+{config.DURACAO_SESSAO_SEGUNDOS} seconds"),
    )
    return token, config.DURACAO_SESSAO_SEGUNDOS


def usuario_da_sessao(token: str | None) -> dict | None:
    if not token:
        return None
    return db.consultar_um(
        """SELECT u.id, u.nome, u.email, u.tipo, u.administrador FROM sessoes s
           JOIN usuarios u ON u.id = s.usuario_id
           WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > CURRENT_TIMESTAMP)""",
        (hash_token(token),),
    )


def encerrar_sessao(token: str) -> None:
    db.executar("DELETE FROM sessoes WHERE token = ?", (hash_token(token),))


def encerrar_outras_sessoes(usuario_id: int, token_atual: str) -> None:
    db.executar(
        "DELETE FROM sessoes WHERE usuario_id = ? AND token != ?", (usuario_id, hash_token(token_atual)),
    )


# ---------------------------------------------------------------- cadastro / login

def _hash_codigo(email: str, codigo: str) -> str:
    return hashlib.sha256(f"{email}:{codigo}".encode()).hexdigest()


def _enviar_codigo(usuario: dict) -> None:
    """Gera um código de 6 dígitos novo (invalida o anterior) e o envia por e-mail."""
    recente = db.consultar_um(
        "SELECT 1 AS x FROM codigos_verificacao WHERE usuario_id = ? AND criado_em > datetime('now', ?)",
        (usuario["id"], f"-{config.CODIGO_REENVIO_SEGUNDOS} seconds"),
    )
    if recente:
        raise HTTPException(429, f"Aguarde {config.CODIGO_REENVIO_SEGUNDOS} segundos para pedir outro código.")
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.executar(
        """INSERT OR REPLACE INTO codigos_verificacao (usuario_id, codigo_hash, expira_em, tentativas)
           VALUES (?, ?, datetime('now', ?), 0)""",
        (usuario["id"], _hash_codigo(usuario["email"], codigo), f"+{config.CODIGO_VALIDADE_MINUTOS} minutes"),
    )
    enviar_email(
        usuario["email"],
        "Seu código de confirmação · Assistente de Estudos",
        f"Olá, {usuario['nome']}!\n\nSeu código de confirmação é: {codigo}\n\n"
        f"Ele vale por {config.CODIGO_VALIDADE_MINUTOS} minutos. Se não foi você, ignore este e-mail.\n",
    )


def _pendente(usuario: dict) -> dict:
    return {"verificacao_pendente": True, "email": usuario["email"]}


def cadastrar(nome: str, email: str, senha: str, tipo: str, disciplina_ids: list[int] | None = None) -> tuple[dict, str | None, int]:
    nome, email = nome.strip(), email.strip().lower()
    if not nome:
        raise HTTPException(400, "Informe seu nome.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "E-mail inválido.")
    if len(senha) < 6:
        raise HTTPException(400, "A senha precisa ter pelo menos 6 caracteres.")
    if tipo not in ("aluno", "professor"):
        raise HTTPException(400, "Tipo deve ser 'aluno' ou 'professor'.")
    if tipo == "professor" and not disciplina_ids:
        raise HTTPException(400, "Escolha a matéria que você administra.")
    if db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,)):
        raise HTTPException(400, "Este e-mail já está cadastrado.")

    try:
        usuario_id = db.executar(
            "INSERT INTO usuarios (nome, email, senha_hash, tipo, email_verificado) VALUES (?, ?, ?, ?, ?)",
            (nome, email, gerar_hash_senha(senha), tipo, 0 if tipo == "professor" else 1),
        )
    except sqlite3.IntegrityError as erro:  # dois cadastros simultâneos com o mesmo e-mail
        raise HTTPException(400, "Este e-mail já está cadastrado. Entre na conta ou use outro e-mail.") from erro
    if tipo == "aluno":
        disciplinas_service.matricular(usuario_id, disciplina_ids or [])
    else:
        if not disciplinas_service.vincular_professor(usuario_id, disciplina_ids):
            db.executar("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            raise HTTPException(400, "Matéria inválida.")
        usuario = {"id": usuario_id, "nome": nome, "email": email}
        try:
            _enviar_codigo(usuario)
        except HTTPException:
            db.executar("DELETE FROM usuarios WHERE id = ?", (usuario_id,))  # sem e-mail enviado não há conta
            raise
        logger.info("professor_cadastrado_pendente", extra={"usuario_id": usuario_id})
        return _pendente(usuario), None, 0
    token, duracao = _iniciar_sessao(usuario_id)
    logger.info("usuario_cadastrado", extra={"usuario_id": usuario_id, "tipo": tipo})
    return {"id": usuario_id, "nome": nome, "email": email, "tipo": tipo, "administrador": 0}, token, duracao


def verificar_email(email: str, codigo: str) -> tuple[dict, str, int]:
    email, codigo = email.strip().lower(), codigo.strip()
    _verificar_rate_limit(email)
    usuario = db.consultar_um("SELECT * FROM usuarios WHERE email = ? AND email_verificado = 0", (email,))
    registro = usuario and db.consultar_um(
        "SELECT *, expira_em > datetime('now') AS valido FROM codigos_verificacao WHERE usuario_id = ?",
        (usuario["id"],),
    )
    if not registro or not registro["valido"] or registro["tentativas"] >= config.CODIGO_MAX_TENTATIVAS:
        raise HTTPException(400, "Código expirado ou inválido. Peça um novo código.")
    if not secrets.compare_digest(registro["codigo_hash"], _hash_codigo(email, codigo)):
        db.executar("UPDATE codigos_verificacao SET tentativas = tentativas + 1 WHERE usuario_id = ?", (usuario["id"],))
        raise HTTPException(400, "Código incorreto.")
    db.executar("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (usuario["id"],))
    db.executar("DELETE FROM codigos_verificacao WHERE usuario_id = ?", (usuario["id"],))
    token, duracao = _iniciar_sessao(usuario["id"])
    logger.info("email_verificado", extra={"usuario_id": usuario["id"]})
    return {k: usuario[k] for k in ("id", "nome", "email", "tipo", "administrador")}, token, duracao


def reenviar_codigo(email: str) -> None:
    """Resposta igual exista ou não a conta: não revela quais e-mails estão cadastrados."""
    usuario = db.consultar_um("SELECT * FROM usuarios WHERE email = ? AND email_verificado = 0", (email.strip().lower(),))
    if usuario:
        _enviar_codigo(usuario)


def entrar(email: str, senha: str) -> tuple[dict, str | None, int]:
    email = email.strip().lower()
    _verificar_rate_limit(email)
    usuario = db.consultar_um("SELECT * FROM usuarios WHERE email = ?", (email,))
    # Mesma mensagem para e-mail ou senha errados: não revela quais e-mails existem
    if not usuario or not conferir_senha(senha, usuario["senha_hash"]):
        _registrar_tentativa_falha(email)
        logger.info("login_falhou", extra={"email": email})
        raise HTTPException(401, "E-mail ou senha incorretos.")
    if not usuario["email_verificado"]:
        try:
            _enviar_codigo(usuario)
        except HTTPException as erro:
            if erro.status_code != 429:  # 429 = código recém-enviado: segue para a tela do código
                raise
        return _pendente(usuario), None, 0
    token, duracao = _iniciar_sessao(usuario["id"])
    logger.info("login_ok", extra={"usuario_id": usuario["id"]})
    return {k: usuario[k] for k in ("id", "nome", "email", "tipo", "administrador")}, token, duracao


# ---------------------------------------------------------------- conta

def atualizar_perfil(usuario: dict, nome: str) -> dict:
    nome = nome.strip()
    if not nome:
        raise HTTPException(400, "Informe seu nome.")
    db.executar("UPDATE usuarios SET nome = ? WHERE id = ?", (nome, usuario["id"]))
    return {**usuario, "nome": nome}


def trocar_senha(usuario: dict, senha_atual: str, nova_senha: str, token_atual: str) -> None:
    salvo = db.consultar_um("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario["id"],))
    if not conferir_senha(senha_atual, salvo["senha_hash"]):
        raise HTTPException(400, "Senha atual incorreta.")
    if len(nova_senha) < 6:
        raise HTTPException(400, "A nova senha precisa ter pelo menos 6 caracteres.")
    db.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (gerar_hash_senha(nova_senha), usuario["id"]))
    encerrar_outras_sessoes(usuario["id"], token_atual)  # quem tinha a senha antiga perde o acesso
    logger.info("senha_trocada", extra={"usuario_id": usuario["id"]})
