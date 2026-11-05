"""Envio de e-mail por SMTP.

Sem SMTP configurado (SMTP_HOST vazio), em desenvolvimento o conteúdo é só escrito no
log do servidor, para dar para testar o cadastro sem servidor de e-mail. Em produção
a falta de SMTP é um erro: nunca deixamos o código vazar para o log lá.
"""
import logging
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException

from .. import config

logger = logging.getLogger("email")


def enviar_email(destino: str, assunto: str, corpo: str) -> None:
    if not config.SMTP_HOST:
        if config.APP_ENV == "production":
            logger.error("smtp_nao_configurado")
            raise HTTPException(503, "O envio de e-mail não está configurado. Fale com o administrador.")
        logger.warning("email_simulado", extra={"destino": destino, "assunto": assunto, "corpo": corpo})
        print(f"\n[E-MAIL SIMULADO] Para: {destino}\nAssunto: {assunto}\n{corpo}\n", flush=True)
        return

    mensagem = EmailMessage()
    mensagem["From"] = config.SMTP_FROM
    mensagem["To"] = destino
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as servidor:
            servidor.starttls()
            if config.SMTP_USER:
                servidor.login(config.SMTP_USER, config.SMTP_PASSWORD)
            servidor.send_message(mensagem)
    except (smtplib.SMTPException, OSError) as erro:
        logger.error("falha_envio_email", extra={"erro": type(erro).__name__})
        raise HTTPException(503, "Não foi possível enviar o e-mail agora. Tente novamente em instantes.") from erro
