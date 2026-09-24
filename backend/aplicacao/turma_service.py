"""Regras de negócio dos recursos da turma em cada disciplina: calendário,
atividades, videoaulas e chat entre os participantes.

Regras de permissão:
- Calendário: professor cria eventos para a turma; aluno cria lembretes pessoais.
- Atividades: professor cria e corrige; aluno entrega (e pode reenviar até ser corrigido).
- Videoaulas: professor adiciona e remove; todos assistem.
- Chat da turma: todos os usuários logados leem e escrevem.
"""
import logging
import re
from datetime import date

from fastapi import HTTPException

from ..infraestrutura import db

logger = logging.getLogger("turma")


def conferir_disciplina(disciplina_id: int) -> None:
    if not db.consultar_um("SELECT id FROM disciplinas WHERE id = ?", (disciplina_id,)):
        raise HTTPException(404, "Disciplina não encontrada.")


def _obrigatorio(valor: str, campo: str) -> str:
    valor = valor.strip()
    if not valor:
        raise HTTPException(400, f"Informe {campo}.")
    return valor


def _data(texto: str) -> str:
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        raise HTTPException(400, "Data inválida (use AAAA-MM-DD).")


# ---------------------------------------------------------------- calendário

def listar_eventos(disciplina_id: int, usuario_id: int) -> list[dict]:
    return db.consultar(
        """SELECT e.id, e.titulo, e.data, e.hora, e.descricao, e.publico, e.usuario_id, u.nome AS autor
           FROM eventos e JOIN usuarios u ON u.id = e.usuario_id
           WHERE e.disciplina_id = ? AND (e.publico = 1 OR e.usuario_id = ?)
           ORDER BY e.data, e.hora IS NOT NULL, e.hora, e.id""",
        (disciplina_id, usuario_id),
    )


def criar_evento(disciplina_id: int, usuario: dict, titulo: str, datas: list[str],
                  hora: str | None, descricao: str) -> int:
    publico = 1 if usuario["tipo"] == "professor" else 0
    if hora is not None and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
        raise HTTPException(400, "Horário inválido (use HH:MM).")
    titulo = _obrigatorio(titulo, "o título")
    datas_validas = sorted({_data(d) for d in datas})
    with db.conectar() as c:  # todos os dias numa transação só
        c.executemany(
            """INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, hora, descricao, publico)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(disciplina_id, usuario["id"], titulo, d, hora, descricao.strip(), publico) for d in datas_validas],
        )
    return len(datas_validas)


def remover_evento(disciplina_id: int, evento_id: int, usuario_id: int) -> None:
    evento = db.consultar_um("SELECT usuario_id FROM eventos WHERE id = ? AND disciplina_id = ?",
                             (evento_id, disciplina_id))
    if not evento:
        raise HTTPException(404, "Evento não encontrado.")
    if evento["usuario_id"] != usuario_id:
        raise HTTPException(403, "Só quem criou o evento pode removê-lo.")
    db.executar("DELETE FROM eventos WHERE id = ?", (evento_id,))


# ---------------------------------------------------------------- atividades

def _atividade(disciplina_id: int, atividade_id: int) -> dict:
    atividade = db.consultar_um("SELECT * FROM atividades WHERE id = ? AND disciplina_id = ?",
                                (atividade_id, disciplina_id))
    if not atividade:
        raise HTTPException(404, "Atividade não encontrada.")
    return atividade


def listar_atividades(disciplina_id: int, usuario_id: int) -> list[dict]:
    return db.consultar(
        """SELECT a.id, a.titulo, a.descricao, a.prazo, a.criado_em, u.nome AS professor,
                  e.resposta, e.nota, e.comentario, e.criado_em AS entregue_em,
                  (SELECT COUNT(*) FROM entregas WHERE atividade_id = a.id) AS total_entregas
           FROM atividades a
           JOIN usuarios u ON u.id = a.criado_por
           LEFT JOIN entregas e ON e.atividade_id = a.id AND e.aluno_id = ?
           WHERE a.disciplina_id = ?
           ORDER BY a.prazo, a.id""",
        (usuario_id, disciplina_id),
    )


def criar_atividade(disciplina_id: int, professor_id: int, titulo: str, descricao: str, prazo: str) -> int:
    return db.executar(
        "INSERT INTO atividades (disciplina_id, criado_por, titulo, descricao, prazo) VALUES (?, ?, ?, ?, ?)",
        (disciplina_id, professor_id, _obrigatorio(titulo, "o título"), descricao.strip(), _data(prazo)),
    )


def remover_atividade(disciplina_id: int, atividade_id: int) -> None:
    _atividade(disciplina_id, atividade_id)
    db.executar("DELETE FROM atividades WHERE id = ?", (atividade_id,))


def entregar_atividade(disciplina_id: int, atividade_id: int, usuario: dict, resposta: str) -> None:
    if usuario["tipo"] != "aluno":
        raise HTTPException(403, "Só alunos entregam atividades.")
    _atividade(disciplina_id, atividade_id)
    entrega = db.consultar_um("SELECT nota FROM entregas WHERE atividade_id = ? AND aluno_id = ?",
                              (atividade_id, usuario["id"]))
    if entrega and entrega["nota"] is not None:
        raise HTTPException(400, "Esta atividade já foi corrigida e não pode ser reenviada.")
    db.executar(
        """INSERT INTO entregas (atividade_id, aluno_id, resposta) VALUES (?, ?, ?)
           ON CONFLICT (atividade_id, aluno_id) DO UPDATE
           SET resposta = excluded.resposta, criado_em = CURRENT_TIMESTAMP""",
        (atividade_id, usuario["id"], _obrigatorio(resposta, "a resposta")),
    )


def listar_entregas(disciplina_id: int, atividade_id: int) -> list[dict]:
    _atividade(disciplina_id, atividade_id)
    return db.consultar(
        """SELECT e.id, e.resposta, e.nota, e.comentario, e.criado_em, u.nome AS aluno
           FROM entregas e JOIN usuarios u ON u.id = e.aluno_id
           WHERE e.atividade_id = ? ORDER BY u.nome""",
        (atividade_id,),
    )


def corrigir_entrega(disciplina_id: int, atividade_id: int, entrega_id: int, nota: float, comentario: str) -> None:
    _atividade(disciplina_id, atividade_id)
    if not db.consultar_um("SELECT id FROM entregas WHERE id = ? AND atividade_id = ?", (entrega_id, atividade_id)):
        raise HTTPException(404, "Entrega não encontrada.")
    db.executar("UPDATE entregas SET nota = ?, comentario = ? WHERE id = ?",
                (nota, comentario.strip(), entrega_id))


# ---------------------------------------------------------------- videoaulas

def listar_videos(disciplina_id: int) -> list[dict]:
    return db.consultar(
        """SELECT v.id, v.titulo, v.url, v.descricao, v.criado_em, u.nome AS adicionado_por
           FROM videos v JOIN usuarios u ON u.id = v.adicionado_por
           WHERE v.disciplina_id = ? ORDER BY v.criado_em DESC, v.id DESC""",
        (disciplina_id,),
    )


def adicionar_video(disciplina_id: int, professor_id: int, titulo: str, url: str, descricao: str) -> int:
    url = url.strip()
    if not url.startswith(("https://", "http://")):  # bloqueia links "javascript:" e afins
        raise HTTPException(400, "Informe um link começando com https://")
    return db.executar(
        "INSERT INTO videos (disciplina_id, adicionado_por, titulo, url, descricao) VALUES (?, ?, ?, ?, ?)",
        (disciplina_id, professor_id, _obrigatorio(titulo, "o título"), url, descricao.strip()),
    )


def remover_video(disciplina_id: int, video_id: int) -> None:
    db.executar("DELETE FROM videos WHERE id = ? AND disciplina_id = ?", (video_id, disciplina_id))


# ---------------------------------------------------------------- chat da turma

def listar_mensagens(disciplina_id: int, depois: int) -> list[dict]:
    """Sem `depois`: as 100 últimas. Com `depois`: só as novas (o frontend consulta a cada poucos segundos)."""
    linhas = db.consultar(
        """SELECT m.id, m.texto, m.criado_em, m.usuario_id, u.nome AS autor, u.tipo
           FROM mensagens_turma m JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.disciplina_id = ? AND m.id > ?
           ORDER BY m.id DESC LIMIT 100""",
        (disciplina_id, depois),
    )
    return linhas[::-1]  # mais antigas primeiro


def enviar_mensagem(disciplina_id: int, usuario_id: int, texto: str) -> int:
    return db.executar(
        "INSERT INTO mensagens_turma (disciplina_id, usuario_id, texto) VALUES (?, ?, ?)",
        (disciplina_id, usuario_id, _obrigatorio(texto, "a mensagem")),
    )
