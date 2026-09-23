"""Cadastro, login e sessões.

Senhas: nunca são guardadas em texto puro. Guardamos um hash PBKDF2-SHA256 com
um "sal" aleatório por usuário e muitas iterações, o que torna ataques de força
bruta lentos. Formato salvo: "iteracoes$sal_hex$hash_hex".

Sessões: no login geramos um token aleatório, salvamos no banco e enviamos ao
navegador num cookie HttpOnly (o JavaScript da página não consegue lê-lo, o que
protege contra roubo de sessão por XSS).
"""
import hashlib
import hmac
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from . import db

ITERACOES = 200_000
NOME_COOKIE = "sessao"

router = APIRouter(prefix="/api/auth")


# ---------------------------------------------------------------- senhas

def gerar_hash(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
    return f"{ITERACOES}${sal.hex()}${h.hex()}"


def conferir_senha(senha: str, salvo: str) -> bool:
    iteracoes, sal_hex, hash_hex = salvo.split("$")
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), int(iteracoes))
    return hmac.compare_digest(h.hex(), hash_hex)  # comparação em tempo constante


# ---------------------------------------------------------------- dependências

def usuario_atual(request: Request) -> dict:
    """Use em rotas que exigem login: `usuario: dict = Depends(usuario_atual)`."""
    token = request.cookies.get(NOME_COOKIE)
    usuario = token and db.consultar_um(
        """SELECT u.id, u.nome, u.email, u.tipo FROM sessoes s
           JOIN usuarios u ON u.id = s.usuario_id WHERE s.token = ?""",
        (token,),
    )
    if not usuario:
        raise HTTPException(401, "Faça login para continuar.")
    return usuario


def somente_professor(usuario: dict = Depends(usuario_atual)) -> dict:
    if usuario["tipo"] != "professor":
        raise HTTPException(403, "Área restrita a professores.")
    return usuario


# ---------------------------------------------------------------- rotas

class Cadastro(BaseModel):
    nome: str
    email: str
    senha: str
    tipo: str


class Login(BaseModel):
    email: str
    senha: str


def _iniciar_sessao(resposta: Response, usuario_id: int) -> None:
    token = secrets.token_urlsafe(32)
    db.executar("INSERT INTO sessoes (token, usuario_id) VALUES (?, ?)", (token, usuario_id))
    resposta.set_cookie(
        NOME_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7,  # 7 dias
    )


@router.post("/cadastro")
def cadastrar(dados: Cadastro, resposta: Response):
    nome, email = dados.nome.strip(), dados.email.strip().lower()
    if not nome:
        raise HTTPException(400, "Informe seu nome.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "E-mail inválido.")
    if len(dados.senha) < 6:
        raise HTTPException(400, "A senha precisa ter pelo menos 6 caracteres.")
    if dados.tipo not in ("aluno", "professor"):
        raise HTTPException(400, "Tipo deve ser 'aluno' ou 'professor'.")
    if db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,)):
        raise HTTPException(400, "Este e-mail já está cadastrado.")

    usuario_id = db.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, gerar_hash(dados.senha), dados.tipo),
    )
    _iniciar_sessao(resposta, usuario_id)
    return {"id": usuario_id, "nome": nome, "email": email, "tipo": dados.tipo}


@router.post("/login")
def entrar(dados: Login, resposta: Response):
    usuario = db.consultar_um("SELECT * FROM usuarios WHERE email = ?", (dados.email.strip().lower(),))
    # Mesma mensagem para e-mail ou senha errados: não revela quais e-mails existem
    if not usuario or not conferir_senha(dados.senha, usuario["senha_hash"]):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    _iniciar_sessao(resposta, usuario["id"])
    return {k: usuario[k] for k in ("id", "nome", "email", "tipo")}


@router.post("/logout")
def sair(request: Request, resposta: Response):
    token = request.cookies.get(NOME_COOKIE)
    if token:
        db.executar("DELETE FROM sessoes WHERE token = ?", (token,))
    resposta.delete_cookie(NOME_COOKIE)
    return {"ok": True}


@router.get("/eu")
def eu(usuario: dict = Depends(usuario_atual)):
    return usuario


# ---------------------------------------------------------------- configurações da conta

class Perfil(BaseModel):
    nome: str


class TrocaSenha(BaseModel):
    senha_atual: str
    nova_senha: str


@router.put("/perfil")
def atualizar_perfil(dados: Perfil, usuario: dict = Depends(usuario_atual)):
    nome = dados.nome.strip()
    if not nome:
        raise HTTPException(400, "Informe seu nome.")
    db.executar("UPDATE usuarios SET nome = ? WHERE id = ?", (nome, usuario["id"]))
    return {**usuario, "nome": nome}


@router.post("/senha")
def trocar_senha(dados: TrocaSenha, request: Request, usuario: dict = Depends(usuario_atual)):
    salvo = db.consultar_um("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario["id"],))
    if not conferir_senha(dados.senha_atual, salvo["senha_hash"]):
        raise HTTPException(400, "Senha atual incorreta.")
    if len(dados.nova_senha) < 6:
        raise HTTPException(400, "A nova senha precisa ter pelo menos 6 caracteres.")
    db.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (gerar_hash(dados.nova_senha), usuario["id"]))
    _encerrar_outras_sessoes(request, usuario["id"])  # quem tinha a senha antiga perde o acesso
    return {"ok": True}


def _encerrar_outras_sessoes(request: Request, usuario_id: int) -> None:
    db.executar("DELETE FROM sessoes WHERE usuario_id = ? AND token != ?",
                (usuario_id, request.cookies.get(NOME_COOKIE)))


@router.post("/encerrar-outras-sessoes")
def encerrar_outras_sessoes(request: Request, usuario: dict = Depends(usuario_atual)):
    _encerrar_outras_sessoes(request, usuario["id"])
    return {"ok": True}
