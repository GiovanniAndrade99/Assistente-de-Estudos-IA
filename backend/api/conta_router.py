"""Rotas da própria conta ligadas à LGPD: ciência do aviso de privacidade e
direitos do titular. Ficam liberadas mesmo antes da ciência (dependencias.py)."""
import json
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from pydantic import BaseModel, Field

from .. import config
from ..aplicacao import auth_service, conta_service, limite_service, links_conta_service
from ..aplicacao.auth_service import NOME_COOKIE
from .dependencias import usuario_atual

router = APIRouter(prefix="/api/conta")


class Ciencia(BaseModel):
    aceite_privacidade: bool = False
    declara_maioridade: bool = False


class TrocaEmail(BaseModel):
    novo_email: str = Field(max_length=254)
    senha: str = Field(max_length=128)


class Exclusao(BaseModel):
    senha: str = Field(max_length=128)
    confirmacao: str = Field(max_length=20)


@router.post("/ciencia-privacidade")
def registrar_ciencia(dados: Ciencia, usuario: dict = Depends(usuario_atual)):
    auth_service.exigir_declaracoes(dados.aceite_privacidade, dados.declara_maioridade)
    auth_service.registrar_ciencia(usuario["id"])
    return {"ok": True}


@router.get("/meus-dados")
def baixar_meus_dados(usuario: dict = Depends(usuario_atual)):
    limite_service.limitar(f"usuario:{usuario['id']}", "exportar_dados", 5, 60)
    conteudo = json.dumps(conta_service.exportar(usuario["id"]), ensure_ascii=False, indent=2, default=str)
    return Response(
        conteudo,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="meus-dados-{date.today().isoformat()}.json"'},
    )


@router.put("/email")
def trocar_email(dados: TrocaEmail, tarefas: BackgroundTasks, usuario: dict = Depends(usuario_atual)):
    links_conta_service.solicitar_troca_email(usuario, dados.novo_email, dados.senha, tarefas)
    return {"ok": True, "mensagem": "Enviamos um link para o novo e-mail. A troca vale depois que você confirmar por lá."}


@router.delete("")
def excluir_conta(dados: Exclusao, resposta: Response, usuario: dict = Depends(usuario_atual)):
    conta_service.excluir_conta(usuario, dados.senha, dados.confirmacao)
    resposta.delete_cookie(NOME_COOKIE, path="/", secure=config.APP_ENV == "production", httponly=True, samesite="lax")
    return {"ok": True}
