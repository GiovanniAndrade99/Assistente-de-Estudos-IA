"""Envio de e-mail transacional por SMTP (qualquer provedor).

Chama-se `correio` e não `email` para não esconder o módulo `email` da biblioteca
padrão. Sem SMTP configurado:
- em desenvolvimento, o link vai só para o log do servidor (para testar sem
  provedor), sem o endereço de e-mail;
- em produção, quem chama deve recusar a operação com 503 (`disponivel()`).
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from .. import config

logger = logging.getLogger("correio")


def configurado() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_REMETENTE)


def disponivel() -> bool:
    """Dá para usar recursos que dependem de e-mail? Fora de produção, sempre (vai para o log)."""
    return configurado() or config.APP_ENV != "production"


def _enviar_smtp(mensagem: EmailMessage) -> None:
    contexto = ssl.create_default_context()
    if config.SMTP_PORTA == 465:
        servidor = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORTA, context=contexto, timeout=20)
    else:
        servidor = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORTA, timeout=20)
    with servidor:
        if config.SMTP_PORTA != 465:
            servidor.starttls(context=contexto)
        if config.SMTP_USUARIO:
            servidor.login(config.SMTP_USUARIO, config.SMTP_SENHA)
        servidor.send_message(mensagem)


def enviar(destinatario: str, assunto: str, texto: str, link: str | None = None, usuario_id: int | None = None) -> None:
    """Envia o e-mail. Feito para rodar em segundo plano: falhas viram log, não exceção."""
    if not configurado():
        if config.APP_ENV != "production":
            logger.warning("email_so_no_log_desenvolvimento",
                           extra={"assunto": assunto, "link": link, "usuario_id": usuario_id})
        return
    mensagem = EmailMessage()
    mensagem["From"] = config.SMTP_REMETENTE
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(texto)
    try:
        _enviar_smtp(mensagem)
        logger.info("email_enviado", extra={"assunto": assunto, "usuario_id": usuario_id})
    except (OSError, smtplib.SMTPException):
        logger.exception("email_falhou", extra={"assunto": assunto, "usuario_id": usuario_id})
