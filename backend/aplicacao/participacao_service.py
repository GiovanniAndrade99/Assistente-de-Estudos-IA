"""Quem participa de cada disciplina: base da autorização por turma.

Participa da disciplina o administrador, o professor que a criou e o aluno
matriculado nela. Só quem participa vê o chat da turma (nomes e mensagens),
eventos, atividades, materiais e usa a IA sobre eles.
"""
from ..infraestrutura import db


def participa(usuario: dict, disciplina: dict) -> bool:
    if usuario.get("administrador"):
        return True
    if usuario["tipo"] == "professor":
        return disciplina["criado_por"] == usuario["id"]
    return db.consultar_um(
        "SELECT 1 FROM matriculas WHERE aluno_id = ? AND disciplina_id = ?",
        (usuario["id"], disciplina["id"]),
    ) is not None


def filtro_sql(usuario: dict, alias: str = "d") -> tuple[str, tuple]:
    """Condição SQL (e parâmetros) que limita as disciplinas às que o usuário participa.
    `alias` é sempre um nome fixo do código, nunca entrada do usuário."""
    if usuario.get("administrador"):
        return "1 = 1", ()
    if usuario["tipo"] == "professor":
        return f"{alias}.criado_por = ?", (usuario["id"],)
    return (
        f"EXISTS (SELECT 1 FROM matriculas m WHERE m.disciplina_id = {alias}.id AND m.aluno_id = ?)",
        (usuario["id"],),
    )
