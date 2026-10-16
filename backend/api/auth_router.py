"""Rotas de cadastro, login, logout e configurações da conta.

Rotas ficam finas: só leem a requisição, chamam a camada de aplicação
(aplicacao/auth_service.py) e devolvem a resposta HTTP.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from pydantic import BaseModel, Field

from .. import config
from ..aplicacao import auth_service, links_conta_service
from ..aplicacao.auth_service import NOME_COOKIE
from ..infraestrutura import correio
from .dependencias import usuario_atual

router = APIRouter(prefix="/api/auth")


def _definir_cookie(resposta: Response, token: str, duracao_segundos: int) -> None:
    resposta.set_cookie(
        NOME_COOKIE, token, httponly=True, samesite="lax",
        secure=config.APP_ENV == "production", max_age=duracao_segundos, path="/",
    )


class Cadastro(BaseModel):
    nome: str = Field(max_length=120)
    email: str = Field(max_length=254)
    senha: str = Field(min_length=10, max_length=128)
    tipo: str
    codigo_professor: str = Field(default="", max_length=128)
    disciplinas: list[int] = []
    aceite_privacidade: bool = False   # "Li o aviso de privacidade"
    declara_maioridade: bool = False   # "Tenho 18 anos ou mais"


class Login(BaseModel):
    email: str = Field(max_length=254)
    senha: str = Field(max_length=128)


@router.post("/cadastro")
def cadastrar(dados: Cadastro, request: Request, resposta: Response, tarefas: BackgroundTasks):
    ip = request.client.host if request.client else "desconhecido"
    usuario, token, duracao = auth_service.cadastrar(
        dados.nome, dados.email, dados.senha, dados.tipo, ip, dados.codigo_professor, dados.disciplinas,
        dados.aceite_privacidade, dados.declara_maioridade,
    )
    _definir_cookie(resposta, token, duracao)
    if correio.disponivel():
        links_conta_service.enviar_verificacao(usuario, tarefas)
    return usuario


class PedidoRedefinicao(BaseModel):
    email: str = Field(max_length=254)


class Redefinicao(BaseModel):
    token: str = Field(max_length=200)
    nova_senha: str = Field(min_length=10, max_length=128)


class TokenDeEmail(BaseModel):
    token: str = Field(max_length=200)


@router.post("/esqueci-senha")
def esqueci_senha(dados: PedidoRedefinicao, request: Request, tarefas: BackgroundTasks):
    ip = request.client.host if request.client else "desconhecido"
    links_conta_service.solicitar_redefinicao(dados.email, ip, tarefas)
    return {"ok": True, "mensagem": "Se houver uma conta com esse e-mail, enviamos um link para criar uma senha nova."}


@router.post("/redefinir-senha")
def redefinir_senha(dados: Redefinicao):
    links_conta_service.redefinir_senha(dados.token, dados.nova_senha)
    return {"ok": True}


@router.post("/confirmar-email")
def confirmar_email(dados: TokenDeEmail):
    return {"ok": True, "resultado": links_conta_service.confirmar_email(dados.token)}


@router.post("/reenviar-verificacao")
def reenviar_verificacao(tarefas: BackgroundTasks, usuario: dict = Depends(usuario_atual)):
    links_conta_service.reenviar_verificacao(usuario, tarefas)
    return {"ok": True}


@router.post("/login")
def entrar(dados: Login, request: Request, resposta: Response):
    ip = request.client.host if request.client else "desconhecido"
    usuario, token, duracao = auth_service.entrar(dados.email, dados.senha, ip)
    _definir_cookie(resposta, token, duracao)
    return usuario


@router.post("/logout")
def sair(request: Request, resposta: Response):
    token = request.cookies.get(NOME_COOKIE)
    if token:
        auth_service.encerrar_sessao(token)
    resposta.delete_cookie(NOME_COOKIE, path="/", secure=config.APP_ENV == "production", httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/eu")
def eu(usuario: dict = Depends(usuario_atual)):
    return auth_service.perfil_publico(usuario)


# ---------------------------------------------------------------- configurações da conta

class Perfil(BaseModel):
    nome: str


class TrocaSenha(BaseModel):
    senha_atual: str = Field(max_length=128)
    nova_senha: str = Field(min_length=10, max_length=128)


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
