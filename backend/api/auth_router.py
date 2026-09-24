"""Rotas de cadastro, login, logout e configurações da conta.

Rotas ficam finas: só leem a requisição, chamam a camada de aplicação
(aplicacao/auth_service.py) e devolvem a resposta HTTP.
"""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from .. import config
from ..aplicacao import auth_service
from ..aplicacao.auth_service import NOME_COOKIE
from .dependencias import usuario_atual

router = APIRouter(prefix="/api/auth")


def _definir_cookie(resposta: Response, token: str, duracao_segundos: int) -> None:
    resposta.set_cookie(
        NOME_COOKIE, token, httponly=True, samesite="lax",
        secure=config.APP_ENV == "production", max_age=duracao_segundos,
    )


class Cadastro(BaseModel):
    nome: str
    email: str
    senha: str
    tipo: str
    disciplinas: list[int] = []


class Login(BaseModel):
    email: str
    senha: str


@router.post("/cadastro")
def cadastrar(dados: Cadastro, resposta: Response):
    usuario, token, duracao = auth_service.cadastrar(dados.nome, dados.email, dados.senha, dados.tipo, dados.disciplinas)
    _definir_cookie(resposta, token, duracao)
    return usuario


@router.post("/login")
def entrar(dados: Login, resposta: Response):
    usuario, token, duracao = auth_service.entrar(dados.email, dados.senha)
    _definir_cookie(resposta, token, duracao)
    return usuario


@router.post("/logout")
def sair(request: Request, resposta: Response):
    token = request.cookies.get(NOME_COOKIE)
    if token:
        auth_service.encerrar_sessao(token)
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
    return auth_service.atualizar_perfil(usuario, dados.nome)


@router.post("/senha")
def trocar_senha(dados: TrocaSenha, request: Request, usuario: dict = Depends(usuario_atual)):
    auth_service.trocar_senha(usuario, dados.senha_atual, dados.nova_senha, request.cookies.get(NOME_COOKIE))
    return {"ok": True}


@router.post("/encerrar-outras-sessoes")
def encerrar_outras_sessoes(request: Request, usuario: dict = Depends(usuario_atual)):
    auth_service.encerrar_outras_sessoes(usuario["id"], request.cookies.get(NOME_COOKIE))
    return {"ok": True}
