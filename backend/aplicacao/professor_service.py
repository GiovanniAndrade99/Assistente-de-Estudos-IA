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


def alunos_da_disciplina(disciplina_id: int) -> list[dict]:
    """Alunos matriculados, com entregas de atividades (e quantas aguardam correção) e simulados."""
    return db.consultar(
        """SELECT u.id, u.nome, u.email,
                  (u.email LIKE 'demo-%@exemplo.local') AS demonstracao,
                  (SELECT COUNT(*) FROM entregas e JOIN atividades a ON a.id = e.atividade_id
                    WHERE e.aluno_id = u.id AND a.disciplina_id = m.disciplina_id) AS entregas,
                  (SELECT COUNT(*) FROM entregas e JOIN atividades a ON a.id = e.atividade_id
                    WHERE e.aluno_id = u.id AND a.disciplina_id = m.disciplina_id AND e.nota IS NULL) AS a_corrigir,
                  (SELECT COUNT(*) FROM resultados_simulado r
                    WHERE r.usuario_id = u.id AND r.disciplina_id = m.disciplina_id) AS simulados
           FROM matriculas m JOIN usuarios u ON u.id = m.aluno_id
           WHERE m.disciplina_id = ?
           ORDER BY u.nome""",
        (disciplina_id,),
    )
