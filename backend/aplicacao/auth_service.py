"""Regras de negócio de cadastro, login e sessões.

Sessões: no login geramos um token aleatório de 256 bits (secrets.token_urlsafe),
enviamos ao navegador num cookie HttpOnly (o JavaScript da página não consegue
lê-lo, o que protege contra roubo de sessão por XSS) e guardamos no banco só o
hash SHA-256 do token — nunca o valor bruto (ver core/seguranca.py). A sessão
expira em config.DURACAO_SESSAO_SEGUNDOS, tanto no cookie quanto no banco.

Rate limit: 5 tentativas de login com falha por e-mail em 15 minutos (config)
bloqueiam novas tentativas com 429 — proteção simples contra força bruta. Há
também limites por IP para login e cadastro. E-mail e IP entram no banco só como
pseudônimos (aplicacao/pseudonimo.py). Fica no banco (não em memória) para
sobreviver a reinícios e funcionar igual com múltiplos processos.
"""
import hmac
import logging
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .. import config
from ..core import seguranca
from ..core.seguranca import conferir_senha, gerar_hash_senha, gerar_token_sessao, hash_token
from ..infraestrutura import db
from . import limite_service, pseudonimo
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
        "SELECT COUNT(*) AS n FROM tentativas_login WHERE chave = ? AND criado_em > datetime('now', ?)",
        (pseudonimo.chave("email", email), f"-{config.JANELA_TENTATIVAS_LOGIN_MINUTOS} minutes"),
    )["n"]
    if total >= config.LIMITE_TENTATIVAS_LOGIN:
        raise HTTPException(
            429, "Muitas tentativas com senha incorreta. Tente novamente em alguns minutos.",
            headers={"Retry-After": str(config.JANELA_TENTATIVAS_LOGIN_MINUTOS * 60)},
        )


def _registrar_tentativa_falha(email: str) -> None:
    with db.conectar() as c:
        _limpar_tentativas_antigas(c)
        c.execute("INSERT INTO tentativas_login (chave) VALUES (?)", (pseudonimo.chave("email", email),))


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
        """SELECT u.id, u.nome, u.email, u.tipo, u.administrador, u.aceite_privacidade_versao,
                  u.maioridade_declarada_em, u.email_verificado_em, u.ultimo_acesso
           FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id
           WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP AND u.sistema = 0""",
        (hash_token(token),),
    )


def ciencia_pendente(usuario: dict) -> bool:
    """Falta confirmar a leitura da versão atual do aviso ou a idade mínima."""
    return (usuario.get("aceite_privacidade_versao") != config.POLITICA_PRIVACIDADE_VERSAO
            or not usuario.get("maioridade_declarada_em"))


def perfil_publico(usuario: dict) -> dict:
    """O que o frontend recebe sobre a própria conta."""
    return {
        "id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"], "tipo": usuario["tipo"],
        "administrador": usuario.get("administrador", 0),
        "ciencia_pendente": ciencia_pendente(usuario),
        "email_verificado": bool(usuario.get("email_verificado_em")),
    }


def registrar_acesso(usuario: dict) -> None:
    """Guarda o último acesso (no máximo uma escrita por hora): base da contagem de
    usuários ativos nas métricas e de uma futura regra para contas inativas."""
    ultimo = usuario.get("ultimo_acesso")
    limite = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    if ultimo is None or ultimo < limite:
        db.executar("UPDATE usuarios SET ultimo_acesso = CURRENT_TIMESTAMP WHERE id = ?", (usuario["id"],))


def registrar_ciencia(usuario_id: int) -> None:
    db.executar(
        """UPDATE usuarios SET aceite_privacidade_versao = ?, aceite_privacidade_em = CURRENT_TIMESTAMP,
                  maioridade_declarada_em = CURRENT_TIMESTAMP WHERE id = ?""",
        (config.POLITICA_PRIVACIDADE_VERSAO, usuario_id),
    )
    logger.info("ciencia_privacidade", extra={"usuario_id": usuario_id, "versao": config.POLITICA_PRIVACIDADE_VERSAO})


def exigir_declaracoes(aceite_privacidade: bool, declara_maioridade: bool) -> None:
    if not aceite_privacidade:
        raise HTTPException(400, "Para criar a conta, confirme que leu o aviso de privacidade.")
    if not declara_maioridade:
        raise HTTPException(
            400, f"O Assistente de Estudos é só para quem tem {config.IDADE_MINIMA} anos ou mais.",
        )


def encerrar_sessao(token: str) -> None:
    db.executar("DELETE FROM sessoes WHERE token = ?", (hash_token(token),))


def encerrar_outras_sessoes(usuario_id: int, token_atual: str) -> None:
    db.executar(
        "DELETE FROM sessoes WHERE usuario_id = ? AND token != ?", (usuario_id, hash_token(token_atual)),
    )


# ---------------------------------------------------------------- cadastro / login

def cadastrar(
    nome: str, email: str, senha: str, tipo: str, ip: str = "desconhecido", codigo_professor: str = "",
    disciplina_ids: list[int] | None = None, aceite_privacidade: bool = False, declara_maioridade: bool = False,
) -> tuple[dict, str, int]:
    # Limite por IP (não por e-mail): evita que um script crie muitas contas
    # trocando de e-mail a cada tentativa. O IP entra só como pseudônimo.
    limite_service.limitar(pseudonimo.chave("ip", ip), "cadastro", config.LIMITE_CADASTROS_POR_IP, 15)
    nome, email = nome.strip(), email.strip().lower()
    if not nome:
        raise HTTPException(400, "Informe seu nome.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "E-mail inválido.")
    if not 10 <= len(senha) <= 128:
        raise HTTPException(400, "A senha precisa ter entre 10 e 128 caracteres.")
    if tipo not in ("aluno", "professor"):
        raise HTTPException(400, "Tipo deve ser 'aluno' ou 'professor'.")
    exigir_declaracoes(aceite_privacidade, declara_maioridade)
    # Sem isso, qualquer visitante marcaria "Professor" na tela de cadastro e
    # ganharia o painel do professor. Só quem recebeu o código (config.py/.env)
    # pode criar conta desse tipo.
    if tipo == "professor":
        if not config.CODIGO_PROFESSOR:
            raise HTTPException(503, "O cadastro de professores está desativado neste servidor.")
        if not hmac.compare_digest(codigo_professor.strip(), config.CODIGO_PROFESSOR):
            raise HTTPException(403, "Código de professor incorreto.")
    if db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,)):
        raise HTTPException(400, "Este e-mail já está cadastrado.")

    try:
        usuario_id = db.executar(
            """INSERT INTO usuarios (nome, email, senha_hash, tipo, aceite_privacidade_versao,
                                     aceite_privacidade_em, maioridade_declarada_em)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (nome, email, gerar_hash_senha(senha), tipo, config.POLITICA_PRIVACIDADE_VERSAO),
        )
    except sqlite3.IntegrityError as erro:  # dois cadastros simultâneos com o mesmo e-mail
        raise HTTPException(400, "Este e-mail já está cadastrado. Entre na conta ou use outro e-mail.") from erro
    if tipo == "aluno" and disciplina_ids:
        disciplinas_service.matricular(usuario_id, disciplina_ids)
    token, duracao = _iniciar_sessao(usuario_id)
    logger.info("usuario_cadastrado", extra={"usuario_id": usuario_id, "tipo": tipo})
    usuario = db.consultar_um("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
    return perfil_publico(usuario), token, duracao


_hash_ficticio: str | None = None


def _conferir_senha_de_conta_inexistente(senha: str) -> None:
    """Gasta o mesmo tempo de um login real: sem isso, a resposta mais rápida
    para e-mail desconhecido revelaria quais e-mails têm conta."""
    global _hash_ficticio
    if _hash_ficticio is None:
        _hash_ficticio = gerar_hash_senha(secrets.token_urlsafe(16))
    conferir_senha(senha, _hash_ficticio)


def entrar(email: str, senha: str, ip: str = "desconhecido") -> tuple[dict, str, int]:
    email = email.strip().lower()
    limite_service.limitar(pseudonimo.chave("ip", ip), "login", config.LIMITE_LOGINS_POR_IP, 15)
    _verificar_rate_limit(email)
    usuario = db.consultar_um("SELECT * FROM usuarios WHERE email = ? AND sistema = 0", (email,))
    if not usuario:
        _conferir_senha_de_conta_inexistente(senha)
    # Mesma mensagem para e-mail ou senha errados: não revela quais e-mails existem
    if not usuario or not conferir_senha(senha, usuario["senha_hash"]):
        _registrar_tentativa_falha(email)
        logger.info("login_falhou")
        raise HTTPException(401, "E-mail ou senha incorretos.")
    # Atualização gradual de hashes antigos após autenticação válida.
    if int(usuario["senha_hash"].split("$", 1)[0]) < seguranca.ITERACOES_SENHA:
        db.executar(
            "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
            (gerar_hash_senha(senha), usuario["id"]),
        )
    token, duracao = _iniciar_sessao(usuario["id"])
    logger.info("login_ok", extra={"usuario_id": usuario["id"]})
    return perfil_publico(usuario), token, duracao


# ---------------------------------------------------------------- conta

def atualizar_perfil(usuario: dict, nome: str) -> dict:
    nome = nome.strip()
    if not nome:
        raise HTTPException(400, "Informe seu nome.")
    db.executar("UPDATE usuarios SET nome = ? WHERE id = ?", (nome, usuario["id"]))
    return perfil_publico({**usuario, "nome": nome})


def trocar_senha(usuario: dict, senha_atual: str, nova_senha: str, token_atual: str) -> None:
    salvo = db.consultar_um("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario["id"],))
    if not conferir_senha(senha_atual, salvo["senha_hash"]):
        raise HTTPException(400, "Senha atual incorreta.")
    if not 10 <= len(nova_senha) <= 128:
        raise HTTPException(400, "A nova senha precisa ter entre 10 e 128 caracteres.")
    db.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (gerar_hash_senha(nova_senha), usuario["id"]))
    encerrar_outras_sessoes(usuario["id"], token_atual)  # quem tinha a senha antiga perde o acesso
    logger.info("senha_trocada", extra={"usuario_id": usuario["id"]})
