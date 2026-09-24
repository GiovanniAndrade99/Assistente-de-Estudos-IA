"""Regras de negócio de visão geral, progresso e lembretes."""
from fastapi import HTTPException

from ..infraestrutura import db


def visao_geral(usuario: dict) -> list[dict]:
    """Disciplinas do usuário (matriculadas, no caso do aluno; todas, no caso do professor)
    com suas aulas (e se o usuário já estudou cada uma) e atividades."""
    usuario_id = usuario["id"]
    if usuario["tipo"] == "aluno":
        linhas = db.consultar(
            """SELECT d.id, d.nome FROM disciplinas d
               JOIN matriculas m ON m.disciplina_id = d.id AND m.aluno_id = ?
               ORDER BY d.nome""",
            (usuario_id,),
        )
    else:
        linhas = db.consultar("SELECT id, nome FROM disciplinas ORDER BY nome")
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


def marcar_aula(documento_id: int, usuario_id: int, concluida: bool) -> None:
    if not db.consultar_um("SELECT id FROM documentos WHERE id = ?", (documento_id,)):
        raise HTTPException(404, "Aula não encontrada.")
    if concluida:
        db.executar("INSERT OR IGNORE INTO aulas_concluidas (usuario_id, documento_id) VALUES (?, ?)",
                    (usuario_id, documento_id))
    else:
        db.executar("DELETE FROM aulas_concluidas WHERE usuario_id = ? AND documento_id = ?",
                    (usuario_id, documento_id))


def lembretes_do_dia(data: str, usuario_id: int) -> list[dict]:
    """Eventos com horário do dia (de todas as disciplinas), para o aviso na hora marcada."""
    return db.consultar(
        """SELECT e.id, e.titulo, e.hora, e.descricao, d.nome AS disciplina
           FROM eventos e JOIN disciplinas d ON d.id = e.disciplina_id
           WHERE e.data = ? AND e.hora IS NOT NULL AND (e.publico = 1 OR e.usuario_id = ?)
           ORDER BY e.hora""",
        (data, usuario_id),
    )
