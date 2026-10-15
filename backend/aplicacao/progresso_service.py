"""Regras de negócio de visão geral, progresso e lembretes."""
from fastapi import HTTPException

from ..infraestrutura import db
from . import participacao_service


def visao_geral(usuario: dict) -> list[dict]:
    """Disciplinas de que o usuário participa (matriculadas, no caso do aluno; as que
    criou, no caso do professor; todas, para o admin) com aulas e atividades."""
    usuario_id = usuario["id"]
    condicao, parametros = participacao_service.filtro_sql(usuario)
    linhas = db.consultar(f"SELECT d.id, d.nome FROM disciplinas d WHERE {condicao} ORDER BY d.nome", parametros)
    disciplinas = {d["id"]: {**d, "aulas": [], "atividades": []} for d in linhas}
    for aula in db.consultar(
        """SELECT doc.id, doc.disciplina_id, doc.arquivo, (c.documento_id IS NOT NULL) AS concluida
           FROM documentos doc
           LEFT JOIN aulas_concluidas c ON c.documento_id = doc.id AND c.usuario_id = ?
           ORDER BY doc.arquivo""",
        (usuario_id,),
    ):
        disciplina = disciplinas.get(aula.pop("disciplina_id"))
        if disciplina:
            disciplina["aulas"].append({**aula, "concluida": bool(aula["concluida"])})
    for atividade in db.consultar(
        """SELECT a.id, a.disciplina_id, a.titulo, a.prazo, e.criado_em AS entregue_em, e.nota,
                  (SELECT COUNT(*) FROM entregas WHERE atividade_id = a.id) AS total_entregas
           FROM atividades a
           LEFT JOIN entregas e ON e.atividade_id = a.id AND e.aluno_id = ?
           ORDER BY a.prazo, a.id""",
        (usuario_id,),
    ):
        disciplina = disciplinas.get(atividade.pop("disciplina_id"))
        if disciplina:
            disciplina["atividades"].append(atividade)
    return list(disciplinas.values())


def marcar_aula(documento_id: int, usuario: dict, concluida: bool) -> None:
    disciplina = db.consultar_um(
        """SELECT d.id, d.criado_por FROM documentos doc JOIN disciplinas d ON d.id = doc.disciplina_id
           WHERE doc.id = ?""",
        (documento_id,),
    )
    if not disciplina:
        raise HTTPException(404, "Aula não encontrada.")
    if not participacao_service.participa(usuario, disciplina):
        raise HTTPException(403, "Você não participa desta disciplina.")
    usuario_id = usuario["id"]
    if concluida:
        db.executar("INSERT OR IGNORE INTO aulas_concluidas (usuario_id, documento_id) VALUES (?, ?)",
                    (usuario_id, documento_id))
    else:
        db.executar("DELETE FROM aulas_concluidas WHERE usuario_id = ? AND documento_id = ?",
                    (usuario_id, documento_id))


def lembretes_do_dia(data: str, usuario: dict) -> list[dict]:
    """Eventos com horário do dia nas disciplinas de que o usuário participa, para o
    aviso na hora marcada."""
    condicao, parametros = participacao_service.filtro_sql(usuario)
    return db.consultar(
        f"""SELECT e.id, e.titulo, e.hora, e.descricao, d.nome AS disciplina
            FROM eventos e JOIN disciplinas d ON d.id = e.disciplina_id
            WHERE e.data = ? AND e.hora IS NOT NULL AND (e.publico = 1 OR e.usuario_id = ?)
              AND {condicao}
            ORDER BY e.hora""",
        (data, usuario["id"], *parametros),
    )
