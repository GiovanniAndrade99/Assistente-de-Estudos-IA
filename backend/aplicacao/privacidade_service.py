"""Dados dinâmicos do aviso de privacidade (frontend/privacidade.html).

O texto do aviso fica no HTML; o que depende da instalação (quem é o controlador,
prazos de retenção, plano do provedor de IA) vem daqui, para o aviso nunca
divergir da configuração real do servidor.
"""
from .. import config

PRAZO_RESPOSTA_DIAS = 15  # LGPD, art. 19, II


def dados_publicos() -> dict:
    return {
        "versao": config.POLITICA_PRIVACIDADE_VERSAO,
        "controlador": {"nome": config.CONTROLADOR_NOME or None, "contato": config.CONTROLADOR_CONTATO or None},
        "encarregado": {"nome": config.ENCARREGADO_NOME or None, "email": config.ENCARREGADO_EMAIL or None},
        "idade_minima": config.IDADE_MINIMA,
        "provedor_ia": {"nome": "Google (API Gemini)", "plano_pago": config.GEMINI_PLANO_PAGO},
        "provedor_email": (config.SMTP_PROVEDOR_NOME or "um provedor de e-mail") if config.SMTP_HOST else None,
        "prazo_resposta_dias": PRAZO_RESPOSTA_DIAS,
        "retencao": {
            "sessao_dias": config.DURACAO_SESSAO_SEGUNDOS // 86400,
            "tentativas_login_minutos": config.JANELA_TENTATIVAS_LOGIN_MINUTOS,
            "historico_meses": config.RETENCAO_HISTORICO_MESES,
            "mensagens_meses": config.RETENCAO_MENSAGENS_MESES,
            "chamados_meses": config.RETENCAO_CHAMADOS_MESES,
            "backup_dias": config.RETENCAO_BACKUP_DIAS,
        },
    }
