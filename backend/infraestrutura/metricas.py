"""Métricas de uso sem dado pessoal: só contagens por dia e por evento.

A tabela não tem coluna de usuário, IP nem texto: "quantas perguntas foram feitas
hoje" não identifica ninguém, então não é dado pessoal. Registrar uma métrica
nunca pode derrubar a operação principal, por isso os erros só vão para o log.
"""
import logging

from . import db

logger = logging.getLogger("metricas")

EVENTOS = (
    "cadastro_aluno", "cadastro_professor", "login", "pergunta_chat", "primeira_pergunta", "resumo",
    "flashcards", "simulado_gerado", "simulado_corrigido", "upload_pdf", "dados_exportados", "conta_excluida",
    "chamadas_ia", "tokens_entrada", "tokens_saida", "respostas_do_cache",
)


def registrar(evento: str, quantidade: int = 1) -> None:
    if quantidade <= 0:
        return
    try:
        db.executar(
            """INSERT INTO metricas_diarias (dia, evento, total) VALUES (date('now'), ?, ?)
               ON CONFLICT (dia, evento) DO UPDATE SET total = total + excluded.total""",
            (evento, quantidade),
        )
    except Exception:
        logger.exception("metrica_falhou", extra={"evento": evento})


def resumo(dias: int) -> dict:
    linhas = db.consultar(
        """SELECT dia, evento, total FROM metricas_diarias
           WHERE dia > date('now', ?) ORDER BY dia""",
        (f"-{dias} days",),
    )
    totais: dict[str, int] = {}
    por_dia: dict[str, dict[str, int]] = {}
    for linha in linhas:
        totais[linha["evento"]] = totais.get(linha["evento"], 0) + linha["total"]
        por_dia.setdefault(linha["dia"], {})[linha["evento"]] = linha["total"]
    contas = db.consultar_um(
        """SELECT SUM(tipo = 'aluno') AS alunos, SUM(tipo = 'professor') AS professores,
                  SUM(ultimo_acesso > datetime('now', '-7 days')) AS ativos_7_dias
           FROM usuarios WHERE sistema = 0 AND email NOT LIKE 'demo-%@exemplo.local'"""
    )
    return {
        "dias": dias,
        "totais": totais,
        "por_dia": [{"dia": dia, **eventos} for dia, eventos in sorted(por_dia.items())],
        "contas": {k: contas[k] or 0 for k in ("alunos", "professores", "ativos_7_dias")},
    }
