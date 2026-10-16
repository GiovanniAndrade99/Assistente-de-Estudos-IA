"""Trilha até a prova e baralho de revisão espaçada.

Trilha: plano semanal de estudo de uma disciplina até uma data-alvo (prova da
disciplina, ENADE, transferência externa ou segunda graduação). O plano é calculado
sem IA, por regras fixas: distribui as aulas ainda não estudadas pelas semanas que
faltam e deixa a última semana para revisão geral e simulado. É recalculado a cada
visita, então acompanha as aulas marcadas como estudadas.

Baralho: flashcards salvos pela pessoa, revisados no dia certo pelo algoritmo SM-2
(cartão fácil volta em intervalos cada vez maiores; cartão errado volta amanhã).
"""
import json
import math
from datetime import date, timedelta
from pathlib import Path

from ..erros import ErroDeUso
from ..infraestrutura import db
from .disciplinas_service import disciplina_ou_404

OBJETIVOS = {
    "prova": "Prova da disciplina",
    "enade": "ENADE",
    "transferencia": "Transferência externa",
    "segunda_graduacao": "Segunda graduação",
}
HORIZONTE_MAXIMO_DIAS = 730
MAXIMO_CARTOES_POR_DISCIPLINA = 2000
ARQUIVO_UNIVERSIDADES = Path(__file__).resolve().parent.parent / "dados" / "universidades.json"


def universidades() -> dict:
    """Dados informativos de cursos de TI (aba "Universidades e vestibulares")."""
    return json.loads(ARQUIVO_UNIVERSIDADES.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- trilha

def montar_plano(aulas: list[dict], hoje: date, data_alvo: date, horas_semana: int) -> dict:
    """Plano semanal determinístico. `aulas`: [{"id", "arquivo", "concluida"}] na ordem do curso."""
    dias = (data_alvo - hoje).days
    total_semanas = max(1, math.ceil((dias + 1) / 7))
    pendentes = [a for a in aulas if not a["concluida"]]
    semanas_de_aula = total_semanas - 1 if total_semanas >= 2 else 1
    n = len(pendentes)
    blocos = [pendentes[i * n // semanas_de_aula:(i + 1) * n // semanas_de_aula] for i in range(semanas_de_aula)]

    semanas = []
    for i in range(total_semanas):
        inicio = hoje + timedelta(days=7 * i)
        fim = min(inicio + timedelta(days=6), data_alvo)
        da_semana = blocos[i] if i < semanas_de_aula else []
        final = total_semanas >= 2 and i == total_semanas - 1
        if final:
            tarefas = [
                {"tipo": "revisao_geral", "texto": "Revisão geral: releia os resumos de todas as aulas"},
                {"tipo": "simulado", "texto": "Simulado com o material inteiro, como ensaio da prova"},
                {"tipo": "cartoes", "texto": "Revisar os cartões do dia"},
            ]
        elif da_semana:
            tarefas = [{"tipo": "aula", "texto": f"Estudar {a['arquivo']}", "documento_id": a["id"]} for a in da_semana]
            tarefas += [
                {"tipo": "flashcards", "texto": "Gerar flashcards dessas aulas e salvar no baralho"},
                {"tipo": "simulado", "texto": "Fazer um simulado das aulas da semana"},
                {"tipo": "cartoes", "texto": "Revisar os cartões do dia"},
            ]
        else:
            tarefas = [
                {"tipo": "cartoes", "texto": "Revisar os cartões do dia"},
                {"tipo": "simulado", "texto": "Simulado de uma aula já estudada (escolha a mais difícil)"},
            ]
        semanas.append({"numero": i + 1, "inicio": inicio.isoformat(), "fim": fim.isoformat(),
                        "horas": horas_semana, "revisao_final": final, "tarefas": tarefas})
    return {"dias_restantes": dias, "aulas_total": len(aulas), "aulas_pendentes": n, "semanas": semanas}


def _aulas(usuario_id: int, disciplina_id: int) -> list[dict]:
    linhas = db.consultar(
        """SELECT doc.id, doc.arquivo, (c.documento_id IS NOT NULL) AS concluida
           FROM documentos doc LEFT JOIN aulas_concluidas c ON c.documento_id = doc.id AND c.usuario_id = ?
           WHERE doc.disciplina_id = ? AND doc.status = 'pronto' ORDER BY doc.arquivo""",
        (usuario_id, disciplina_id),
    )
    return [{**l, "concluida": bool(l["concluida"])} for l in linhas]


def obter(usuario_id: int, disciplina_id: int, hoje: date | None = None) -> dict:
    disciplina_ou_404(disciplina_id)
    hoje = hoje or date.today()
    trilha = db.consultar_um(
        "SELECT objetivo, data_alvo, horas_semana, atualizado_em FROM trilhas WHERE usuario_id = ? AND disciplina_id = ?",
        (usuario_id, disciplina_id),
    )
    plano = None
    if trilha:
        alvo = date.fromisoformat(trilha["data_alvo"])
        plano = montar_plano(_aulas(usuario_id, disciplina_id), hoje, max(alvo, hoje), trilha["horas_semana"])
    # Datas que o professor marcou no calendário da turma: sugestões de data-alvo
    datas_da_turma = db.consultar(
        """SELECT titulo, data FROM eventos WHERE disciplina_id = ? AND publico = 1 AND data >= ?
           ORDER BY data LIMIT 5""",
        (disciplina_id, hoje.isoformat()),
    )
    return {"objetivos": OBJETIVOS, "trilha": trilha, "plano": plano, "datas_da_turma": datas_da_turma,
            "baralho": resumo_do_baralho(usuario_id, disciplina_id)}


def salvar(usuario_id: int, disciplina_id: int, objetivo: str, data_alvo: date, horas_semana: int,
           hoje: date | None = None) -> dict:
    disciplina_ou_404(disciplina_id)
    hoje = hoje or date.today()
    if objetivo not in OBJETIVOS:
        raise ErroDeUso("Objetivo inválido.")
    if not hoje <= data_alvo <= hoje + timedelta(days=HORIZONTE_MAXIMO_DIAS):
        raise ErroDeUso("Escolha uma data a partir de hoje e em até 2 anos.")
    db.executar(
        """INSERT INTO trilhas (usuario_id, disciplina_id, objetivo, data_alvo, horas_semana) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (usuario_id, disciplina_id) DO UPDATE SET objetivo = excluded.objetivo,
               data_alvo = excluded.data_alvo, horas_semana = excluded.horas_semana, atualizado_em = CURRENT_TIMESTAMP""",
        (usuario_id, disciplina_id, objetivo, data_alvo.isoformat(), horas_semana),
    )
    return obter(usuario_id, disciplina_id, hoje)


def remover(usuario_id: int, disciplina_id: int) -> None:
    db.executar("DELETE FROM trilhas WHERE usuario_id = ? AND disciplina_id = ?", (usuario_id, disciplina_id))


# ---------------------------------------------------------------- baralho (SM-2)

def sm2(facilidade: float, intervalo: int, repeticoes: int, nota: int) -> tuple[float, int, int]:
    """Algoritmo SM-2 (SuperMemo 2). nota de 0 a 5; abaixo de 3 = errou e recomeça."""
    if nota < 3:
        repeticoes, intervalo = 0, 1
    else:
        repeticoes += 1
        intervalo = 1 if repeticoes == 1 else 6 if repeticoes == 2 else round(intervalo * facilidade)
    facilidade = max(1.3, facilidade + 0.1 - (5 - nota) * (0.08 + (5 - nota) * 0.02))
    return round(facilidade, 2), intervalo, repeticoes


def resumo_do_baralho(usuario_id: int, disciplina_id: int) -> dict:
    linha = db.consultar_um(
        """SELECT COUNT(*) AS total, COALESCE(SUM(proxima_revisao <= date('now')), 0) AS para_hoje
           FROM flashcards WHERE usuario_id = ? AND disciplina_id = ?""",
        (usuario_id, disciplina_id),
    )
    return {"total": linha["total"], "para_hoje": linha["para_hoje"]}


def salvar_cartoes(usuario_id: int, disciplina_id: int, arquivo: str, cartoes: list[dict]) -> dict:
    disciplina_ou_404(disciplina_id)
    if resumo_do_baralho(usuario_id, disciplina_id)["total"] + len(cartoes) > MAXIMO_CARTOES_POR_DISCIPLINA:
        raise ErroDeUso(f"O baralho desta disciplina chegou ao limite de {MAXIMO_CARTOES_POR_DISCIPLINA} cartões.")
    salvos = 0
    with db.conectar() as c:
        for cartao in cartoes:
            salvos += c.execute(
                """INSERT OR IGNORE INTO flashcards (usuario_id, disciplina_id, arquivo, frente, verso, pagina)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (usuario_id, disciplina_id, arquivo, cartao["frente"].strip(), cartao["verso"].strip(),
                 cartao.get("pagina")),
            ).rowcount
    return {"salvos": salvos, "repetidos": len(cartoes) - salvos, **resumo_do_baralho(usuario_id, disciplina_id)}


def cartoes_para_hoje(usuario_id: int, disciplina_id: int, limite: int = 30) -> dict:
    disciplina_ou_404(disciplina_id)
    cartoes = db.consultar(
        """SELECT id, frente, verso, arquivo, pagina, repeticoes FROM flashcards
           WHERE usuario_id = ? AND disciplina_id = ? AND proxima_revisao <= date('now')
           ORDER BY proxima_revisao, id LIMIT ?""",
        (usuario_id, disciplina_id, limite),
    )
    return {"cartoes": cartoes, **resumo_do_baralho(usuario_id, disciplina_id)}


def _cartao_da_pessoa(usuario_id: int, cartao_id: int) -> dict:
    cartao = db.consultar_um("SELECT * FROM flashcards WHERE id = ? AND usuario_id = ?", (cartao_id, usuario_id))
    if not cartao:  # cartão de outra pessoa responde igual a inexistente
        raise ErroDeUso("Cartão não encontrado.", 404)
    return cartao


def revisar(usuario_id: int, cartao_id: int, nota: int, hoje: date | None = None) -> dict:
    cartao = _cartao_da_pessoa(usuario_id, cartao_id)
    facilidade, intervalo, repeticoes = sm2(cartao["facilidade"], cartao["intervalo_dias"], cartao["repeticoes"], nota)
    proxima = (hoje or date.today()) + timedelta(days=intervalo)
    db.executar(
        """UPDATE flashcards SET facilidade = ?, intervalo_dias = ?, repeticoes = ?, proxima_revisao = ?,
                  revisado_em = CURRENT_TIMESTAMP WHERE id = ?""",
        (facilidade, intervalo, repeticoes, proxima.isoformat(), cartao_id),
    )
    return {"proxima_revisao": proxima.isoformat(), "intervalo_dias": intervalo}


def remover_cartao(usuario_id: int, cartao_id: int) -> None:
    _cartao_da_pessoa(usuario_id, cartao_id)
    db.executar("DELETE FROM flashcards WHERE id = ?", (cartao_id,))
