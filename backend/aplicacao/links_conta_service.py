"""Links de conta enviados por e-mail: redefinir senha, confirmar e trocar e-mail.

Segurança e privacidade:
- o banco guarda só o hash do token; cada link vale uma vez e expira;
- o token vai no fragmento da URL (#t=...), que o navegador não manda ao servidor
  ao abrir a página, então não aparece em logs de acesso nem de proxy;
- "esqueci a senha" responde igual exista ou não a conta;
- a troca de e-mail é confirmada por link no endereço NOVO, e o endereço antigo é
  avisado: assim uma sessão roubada não toma a conta trocando o e-mail.
"""
import logging
import re

from fastapi import BackgroundTasks, HTTPException

from .. import config
from ..core.seguranca import conferir_senha, gerar_hash_senha, gerar_token_sessao, hash_token
from ..infraestrutura import correio, db
from . import limite_service, pseudonimo

logger = logging.getLogger("conta")

VALIDADE = {"redefinir_senha": "+30 minutes", "verificar_email": "+48 hours", "trocar_email": "+48 hours"}
PAGINA = {
    "redefinir_senha": "redefinir-senha.html",
    "verificar_email": "verificar-email.html",
    "trocar_email": "verificar-email.html",
}
LINK_INVALIDO = "Este link é inválido, já foi usado ou venceu. Peça um novo."


def _exigir_correio() -> None:
    if not correio.disponivel():
        raise HTTPException(503, "O envio de e-mails não está configurado neste servidor.")


def _validar_email(email: str) -> str:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "E-mail inválido.")
    return email


def _criar_token(usuario_id: int, tipo: str, dado: str | None = None) -> str:
    token = gerar_token_sessao()
    with db.conectar() as c:
        # Só o link mais recente de cada tipo vale
        c.execute(
            "UPDATE tokens_conta SET usado_em = CURRENT_TIMESTAMP WHERE usuario_id = ? AND tipo = ? AND usado_em IS NULL",
            (usuario_id, tipo),
        )
        c.execute(
            """INSERT INTO tokens_conta (token_hash, usuario_id, tipo, dado, expires_at)
               VALUES (?, ?, ?, ?, datetime('now', ?))""",
            (hash_token(token), usuario_id, tipo, dado, VALIDADE[tipo]),
        )
    return token


def _link(tipo: str, token: str) -> str:
    return f"{config.APP_URL_BASE}/{PAGINA[tipo]}#t={token}"


def _consumir(token: str, tipos: tuple[str, ...]) -> dict:
    """Marca o link como usado (uma vez só) e devolve o registro."""
    with db.conectar() as c:
        linha = c.execute(
            "SELECT * FROM tokens_conta WHERE token_hash = ? AND usado_em IS NULL AND expires_at > CURRENT_TIMESTAMP",
            (hash_token(token or ""),),
        ).fetchone()
        if not linha or linha["tipo"] not in tipos:
            raise HTTPException(400, LINK_INVALIDO)
        usado = c.execute(
            "UPDATE tokens_conta SET usado_em = CURRENT_TIMESTAMP WHERE token_hash = ? AND usado_em IS NULL",
            (linha["token_hash"],),
        ).rowcount
        if not usado:  # dois cliques simultâneos no mesmo link
            raise HTTPException(400, LINK_INVALIDO)
        return dict(linha)


# ---------------------------------------------------------------- senha

def solicitar_redefinicao(email: str, ip: str, tarefas: BackgroundTasks) -> None:
    _exigir_correio()
    email = email.strip().lower()
    limite_service.limitar(pseudonimo.chave("ip", ip), "esqueci_senha", 5, 15)
    limite_service.limitar(pseudonimo.chave("email", email), "esqueci_senha", 3, 60)
    usuario = db.consultar_um("SELECT id, nome, email FROM usuarios WHERE email = ? AND sistema = 0", (email,))
    if not usuario:
        return  # mesma resposta: não revela se o e-mail tem conta
    token = _criar_token(usuario["id"], "redefinir_senha")
    link = _link("redefinir_senha", token)
    tarefas.add_task(
        correio.enviar, usuario["email"], "Redefinir sua senha · Assistente de Estudos",
        f"Olá, {usuario['nome']}.\n\nRecebemos um pedido para redefinir a senha da sua conta. Para criar uma "
        f"senha nova, abra o link abaixo em até 30 minutos:\n\n{link}\n\nSe não foi você, ignore este e-mail: "
        "sua senha continua a mesma.",
        link, usuario["id"],
    )


def redefinir_senha(token: str, nova_senha: str) -> None:
    if not 10 <= len(nova_senha) <= 128:
        raise HTTPException(400, "A nova senha precisa ter entre 10 e 128 caracteres.")
    registro = _consumir(token, ("redefinir_senha",))
    usuario_id = registro["usuario_id"]
    with db.conectar() as c:
        c.execute("UPDATE usuarios SET senha_hash = ?, email_verificado_em = COALESCE(email_verificado_em, "
                  "CURRENT_TIMESTAMP) WHERE id = ?", (gerar_hash_senha(nova_senha), usuario_id))
        # Quem tinha a senha antiga (ou uma sessão roubada) perde o acesso
        c.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))
        c.execute("UPDATE tokens_conta SET usado_em = CURRENT_TIMESTAMP WHERE usuario_id = ? AND usado_em IS NULL",
                  (usuario_id,))
    logger.info("senha_redefinida", extra={"usuario_id": usuario_id})


# ---------------------------------------------------------------- e-mail

def enviar_verificacao(usuario: dict, tarefas: BackgroundTasks) -> None:
    token = _criar_token(usuario["id"], "verificar_email")
    link = _link("verificar_email", token)
    tarefas.add_task(
        correio.enviar, usuario["email"], "Confirme seu e-mail · Assistente de Estudos",
        f"Olá, {usuario['nome']}.\n\nPara confirmar que este e-mail é seu, abra o link abaixo (vale por 48 horas):"
        f"\n\n{link}\n\nSe você não criou uma conta no Assistente de Estudos, ignore este e-mail.",
        link, usuario["id"],
    )


def reenviar_verificacao(usuario: dict, tarefas: BackgroundTasks) -> None:
    _exigir_correio()
    if usuario.get("email_verificado_em"):
        raise HTTPException(400, "Seu e-mail já está confirmado.")
    limite_service.limitar(f"usuario:{usuario['id']}", "reenviar_verificacao", 3, 60)
    enviar_verificacao(usuario, tarefas)


def solicitar_troca_email(usuario: dict, novo_email: str, senha: str, tarefas: BackgroundTasks) -> None:
    _exigir_correio()
    novo_email = _validar_email(novo_email)
    salvo = db.consultar_um("SELECT senha_hash, email, nome FROM usuarios WHERE id = ?", (usuario["id"],))
    if not conferir_senha(senha, salvo["senha_hash"]):
        raise HTTPException(400, "Senha incorreta.")
    if novo_email == salvo["email"]:
        raise HTTPException(400, "Esse já é o seu e-mail.")
    if db.consultar_um("SELECT 1 FROM usuarios WHERE email = ?", (novo_email,)):
        raise HTTPException(400, "Este e-mail já está em uso por outra conta.")
    limite_service.limitar(f"usuario:{usuario['id']}", "trocar_email", 3, 60)
    token = _criar_token(usuario["id"], "trocar_email", novo_email)
    link = _link("trocar_email", token)
    tarefas.add_task(
        correio.enviar, novo_email, "Confirme seu novo e-mail · Assistente de Estudos",
        f"Olá, {salvo['nome']}.\n\nPara usar este endereço na sua conta do Assistente de Estudos, abra o link abaixo "
        f"(vale por 48 horas):\n\n{link}\n\nSe você não pediu esta troca, ignore este e-mail.",
        link, usuario["id"],
    )
    tarefas.add_task(
        correio.enviar, salvo["email"], "Pedido de troca de e-mail · Assistente de Estudos",
        f"Olá, {salvo['nome']}.\n\nPediram para trocar o e-mail da sua conta para outro endereço. A troca só vale "
        "depois de confirmada no endereço novo. Se não foi você, troque sua senha e encerre as outras sessões nas "
        "Configurações.",
        None, usuario["id"],
    )


def confirmar_email(token: str) -> str:
    """Confirma o e-mail da conta ou conclui uma troca de e-mail. Devolve o que aconteceu."""
    registro = _consumir(token, ("verificar_email", "trocar_email"))
    if registro["tipo"] == "verificar_email":
        db.executar("UPDATE usuarios SET email_verificado_em = CURRENT_TIMESTAMP WHERE id = ?", (registro["usuario_id"],))
        return "verificado"
    novo = registro["dado"]
    if db.consultar_um("SELECT 1 FROM usuarios WHERE email = ? AND id != ?", (novo, registro["usuario_id"])):
        raise HTTPException(400, "Este e-mail passou a ser usado por outra conta. Peça a troca de novo.")
    db.executar("UPDATE usuarios SET email = ?, email_verificado_em = CURRENT_TIMESTAMP WHERE id = ?",
                (novo, registro["usuario_id"]))
    logger.info("email_trocado", extra={"usuario_id": registro["usuario_id"]})
    return "trocado"
