"""Regras de negócio do painel do professor."""
from ..infraestrutura import db


def perguntas_dos_alunos(disciplina_id: int) -> list[dict]:
    return db.consultar(
        """SELECT p.pergunta, p.resposta, p.criado_em, u.nome AS aluno
           FROM perguntas p JOIN usuarios u ON u.id = p.usuario_id
           WHERE p.disciplina_id = ? AND u.tipo = 'aluno'
           ORDER BY p.criado_em DESC LIMIT 200""",
        (disciplina_id,),
    )


def notas_dos_alunos(disciplina_id: int) -> list[dict]:
    return db.consultar(
        """SELECT u.nome AS aluno, r.arquivo, r.acertos, r.total, r.criado_em
           FROM resultados_simulado r JOIN usuarios u ON u.id = r.usuario_id
           WHERE r.disciplina_id = ? AND u.tipo = 'aluno'
           ORDER BY r.criado_em DESC LIMIT 200""",
        (disciplina_id,),
    )
