"""Retenção de dados (LGPD, arts. 15 e 16): apaga o que passou do prazo.

Os prazos ficam no config.py / .env (RETENCAO_*) e estão descritos no aviso de
privacidade. A limpeza roda na subida do servidor, a cada INTERVALO_LIMPEZA_HORAS
e pode ser disparada com `python -m scripts.limpeza`. O log registra só contagens.
"""
import logging

from .. import config
from ..infraestrutura import db

logger = logging.getLogger("retencao")


def _regras() -> list[tuple[str, str, tuple]]:
    def meses(n: int) -> str:
        return f"-{n} months"

    regras = [
        # Segurança e controle de abuso: vida curta
        ("sessoes_vencidas", "DELETE FROM sessoes WHERE expires_at IS NULL OR expires_at <= CURRENT_TIMESTAMP", ()),
        ("tentativas_login", "DELETE FROM tentativas_login WHERE criado_em <= datetime('now', ?)",
         (f"-{config.JANELA_TENTATIVAS_LOGIN_MINUTOS} minutes",)),
        ("limites_de_uso", "DELETE FROM limite_uso WHERE criado_em <= datetime('now', '-1 day')", ()),
        # Contagens anônimas: não são dados pessoais, mas não precisam crescer para sempre
        ("metricas_antigas", "DELETE FROM metricas_diarias WHERE dia <= date('now', '-24 months')", ()),
        # Simulados gerados e nunca respondidos
        ("simulados_abandonados", "DELETE FROM simulados WHERE finalizado_em IS NULL "
                                  "AND criado_em <= datetime('now', '-7 days')", ()),
        # Cache de respostas da IA (sem dado de quem perguntou) depois da validade
        ("cache_de_respostas", "DELETE FROM cache_respostas WHERE criado_em <= datetime('now', ?)",
         (f"-{max(config.CACHE_RESPOSTAS_DIAS, 0)} days",)),
        # Links de e-mail usados ou vencidos (o de troca guarda o novo e-mail)
        ("links_de_conta", "DELETE FROM tokens_conta WHERE expires_at <= datetime('now', '-1 day') "
                           "OR usado_em <= datetime('now', '-1 day')", ()),
    ]
    if config.RETENCAO_HISTORICO_MESES > 0:
        prazo = (meses(config.RETENCAO_HISTORICO_MESES),)
        regras += [
            ("perguntas", "DELETE FROM perguntas WHERE criado_em <= datetime('now', ?)", prazo),
            ("resultados_simulado", "DELETE FROM resultados_simulado WHERE criado_em <= datetime('now', ?)", prazo),
            ("simulados", "DELETE FROM simulados WHERE criado_em <= datetime('now', ?)", prazo),
            ("eventos", "DELETE FROM eventos WHERE data <= date('now', ?)", prazo),
        ]
    if config.RETENCAO_MENSAGENS_MESES > 0:
        regras.append(("mensagens_turma", "DELETE FROM mensagens_turma WHERE criado_em <= datetime('now', ?)",
                       (meses(config.RETENCAO_MENSAGENS_MESES),)))
    if config.RETENCAO_CHAMADOS_MESES > 0:
        regras.append(("chamados_respondidos",
                       "DELETE FROM chamados_suporte WHERE resposta IS NOT NULL AND respondido_em <= datetime('now', ?)",
                       (meses(config.RETENCAO_CHAMADOS_MESES),)))
    return regras


def executar_limpeza() -> dict[str, int]:
    apagados = {}
    with db.conectar() as c:
        for nome, sql, parametros in _regras():
            apagados[nome] = c.execute(sql, parametros).rowcount
    logger.info("limpeza_de_retencao", extra={"apagados": apagados})
    return apagados
