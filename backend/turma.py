"""Recursos da turma em cada disciplina: calendário, atividades, videoaulas e
chat entre os participantes.

Regras de permissão:
- Calendário: professor cria eventos para a turma; aluno cria lembretes pessoais.
- Atividades: professor cria e corrige; aluno entrega (e pode reenviar até ser corrigido).
- Videoaulas: professor adiciona e remove; todos assistem.
- Chat da turma: todos os usuários logados leem e escrevem.
"""
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import db
from .auth import somente_professor, usuario_atual


def _conferir_disciplina(disciplina_id: int) -> None:
    if not db.consultar_um("SELECT id FROM disciplinas WHERE id = ?", (disciplina_id,)):
        raise HTTPException(404, "Disciplina não encontrada.")


# Toda rota deste arquivo recebe {disciplina_id} e já confere se ela existe
router = APIRouter(prefix="/api/disciplinas/{disciplina_id}", dependencies=[Depends(_conferir_disciplina)])


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

class NovoEvento(BaseModel):
    titulo: str = Field(max_length=120)
    datas: list[str] = Field(min_length=1, max_length=100)  # um evento para cada dia escolhido
    hora: str | None = None                                  # "HH:MM"; None = dia todo
    descricao: str = Field(default="", max_length=1000)


@router.get("/eventos")
def listar_eventos(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return db.consultar(
        """SELECT e.id, e.titulo, e.data, e.hora, e.descricao, e.publico, e.usuario_id, u.nome AS autor
           FROM eventos e JOIN usuarios u ON u.id = e.usuario_id
           WHERE e.disciplina_id = ? AND (e.publico = 1 OR e.usuario_id = ?)
           ORDER BY e.data, e.hora IS NOT NULL, e.hora, e.id""",  # "dia todo" antes dos com horário
        (disciplina_id, usuario["id"]),
    )


@router.post("/eventos")
def criar_evento(disciplina_id: int, dados: NovoEvento, usuario: dict = Depends(usuario_atual)):
    publico = 1 if usuario["tipo"] == "professor" else 0
    if dados.hora is not None and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", dados.hora):
        raise HTTPException(400, "Horário inválido (use HH:MM).")
    titulo = _obrigatorio(dados.titulo, "o título")
    datas = sorted({_data(d) for d in dados.datas})
    with db.conectar() as c:  # todos os dias numa transação só
        c.executemany(
            """INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, hora, descricao, publico)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(disciplina_id, usuario["id"], titulo, d, dados.hora, dados.descricao.strip(), publico) for d in datas],
        )
    return {"criados": len(datas)}


@router.delete("/eventos/{evento_id}")
def remover_evento(disciplina_id: int, evento_id: int, usuario: dict = Depends(usuario_atual)):
    evento = db.consultar_um("SELECT usuario_id FROM eventos WHERE id = ? AND disciplina_id = ?",
                             (evento_id, disciplina_id))
    if not evento:
        raise HTTPException(404, "Evento não encontrado.")
    if evento["usuario_id"] != usuario["id"]:
        raise HTTPException(403, "Só quem criou o evento pode removê-lo.")
    db.executar("DELETE FROM eventos WHERE id = ?", (evento_id,))
    return {"ok": True}


# ---------------------------------------------------------------- atividades

class NovaAtividade(BaseModel):
    titulo: str = Field(max_length=150)
    descricao: str = Field(default="", max_length=5000)
    prazo: str


class Entrega(BaseModel):
    resposta: str = Field(max_length=10000)


class Correcao(BaseModel):
    nota: float = Field(ge=0, le=10)
    comentario: str = Field(default="", max_length=2000)


def _atividade(disciplina_id: int, atividade_id: int) -> dict:
    atividade = db.consultar_um("SELECT * FROM atividades WHERE id = ? AND disciplina_id = ?",
                                (atividade_id, disciplina_id))
    if not atividade:
        raise HTTPException(404, "Atividade não encontrada.")
    return atividade


@router.get("/atividades")
def listar_atividades(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    # Cada atividade vem com a entrega do próprio usuário (aluno) e o total de entregas (professor)
    return db.consultar(
        """SELECT a.id, a.titulo, a.descricao, a.prazo, a.criado_em, u.nome AS professor,
                  e.resposta, e.nota, e.comentario, e.criado_em AS entregue_em,
                  (SELECT COUNT(*) FROM entregas WHERE atividade_id = a.id) AS total_entregas
           FROM atividades a
           JOIN usuarios u ON u.id = a.criado_por
           LEFT JOIN entregas e ON e.atividade_id = a.id AND e.aluno_id = ?
           WHERE a.disciplina_id = ?
           ORDER BY a.prazo, a.id""",
        (usuario["id"], disciplina_id),
    )


@router.post("/atividades")
def criar_atividade(disciplina_id: int, dados: NovaAtividade, professor: dict = Depends(somente_professor)):
    novo_id = db.executar(
        "INSERT INTO atividades (disciplina_id, criado_por, titulo, descricao, prazo) VALUES (?, ?, ?, ?, ?)",
        (disciplina_id, professor["id"], _obrigatorio(dados.titulo, "o título"),
         dados.descricao.strip(), _data(dados.prazo)),
    )
    return {"id": novo_id}


@router.delete("/atividades/{atividade_id}")
def remover_atividade(disciplina_id: int, atividade_id: int, professor: dict = Depends(somente_professor)):
    _atividade(disciplina_id, atividade_id)
    db.executar("DELETE FROM atividades WHERE id = ?", (atividade_id,))
    return {"ok": True}


@router.post("/atividades/{atividade_id}/entrega")
def entregar_atividade(disciplina_id: int, atividade_id: int, dados: Entrega,
                       usuario: dict = Depends(usuario_atual)):
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
        (atividade_id, usuario["id"], _obrigatorio(dados.resposta, "a resposta")),
    )
    return {"ok": True}


@router.get("/atividades/{atividade_id}/entregas")
def listar_entregas(disciplina_id: int, atividade_id: int, professor: dict = Depends(somente_professor)):
    _atividade(disciplina_id, atividade_id)
    return db.consultar(
        """SELECT e.id, e.resposta, e.nota, e.comentario, e.criado_em, u.nome AS aluno
           FROM entregas e JOIN usuarios u ON u.id = e.aluno_id
           WHERE e.atividade_id = ? ORDER BY u.nome""",
        (atividade_id,),
    )


@router.put("/atividades/{atividade_id}/entregas/{entrega_id}")
def corrigir_entrega(disciplina_id: int, atividade_id: int, entrega_id: int, dados: Correcao,
                     professor: dict = Depends(somente_professor)):
    _atividade(disciplina_id, atividade_id)
    if not db.consultar_um("SELECT id FROM entregas WHERE id = ? AND atividade_id = ?", (entrega_id, atividade_id)):
        raise HTTPException(404, "Entrega não encontrada.")
    db.executar("UPDATE entregas SET nota = ?, comentario = ? WHERE id = ?",
                (dados.nota, dados.comentario.strip(), entrega_id))
    return {"ok": True}


# ---------------------------------------------------------------- videoaulas

class NovoVideo(BaseModel):
    titulo: str = Field(max_length=150)
    url: str = Field(max_length=500)
    descricao: str = Field(default="", max_length=1000)


@router.get("/videos")
def listar_videos(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return db.consultar(
        """SELECT v.id, v.titulo, v.url, v.descricao, v.criado_em, u.nome AS adicionado_por
           FROM videos v JOIN usuarios u ON u.id = v.adicionado_por
           WHERE v.disciplina_id = ? ORDER BY v.criado_em DESC, v.id DESC""",
        (disciplina_id,),
    )


@router.post("/videos")
def adicionar_video(disciplina_id: int, dados: NovoVideo, professor: dict = Depends(somente_professor)):
    url = dados.url.strip()
    if not url.startswith(("https://", "http://")):  # bloqueia links "javascript:" e afins
        raise HTTPException(400, "Informe um link começando com https://")
    novo_id = db.executar(
        "INSERT INTO videos (disciplina_id, adicionado_por, titulo, url, descricao) VALUES (?, ?, ?, ?, ?)",
        (disciplina_id, professor["id"], _obrigatorio(dados.titulo, "o título"), url, dados.descricao.strip()),
    )
    return {"id": novo_id}


@router.delete("/videos/{video_id}")
def remover_video(disciplina_id: int, video_id: int, professor: dict = Depends(somente_professor)):
    db.executar("DELETE FROM videos WHERE id = ? AND disciplina_id = ?", (video_id, disciplina_id))
    return {"ok": True}


# ---------------------------------------------------------------- chat da turma

class NovaMensagem(BaseModel):
    texto: str = Field(max_length=1000)


@router.get("/mensagens")
def listar_mensagens(disciplina_id: int, depois: int = 0, usuario: dict = Depends(usuario_atual)):
    """Sem `depois`: as 100 últimas. Com `depois`: só as novas (o frontend consulta a cada poucos segundos)."""
    linhas = db.consultar(
        """SELECT m.id, m.texto, m.criado_em, m.usuario_id, u.nome AS autor, u.tipo
           FROM mensagens_turma m JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.disciplina_id = ? AND m.id > ?
           ORDER BY m.id DESC LIMIT 100""",
        (disciplina_id, depois),
    )
    return linhas[::-1]  # mais antigas primeiro


@router.post("/mensagens")
def enviar_mensagem(disciplina_id: int, dados: NovaMensagem, usuario: dict = Depends(usuario_atual)):
    novo_id = db.executar(
        "INSERT INTO mensagens_turma (disciplina_id, usuario_id, texto) VALUES (?, ?, ?)",
        (disciplina_id, usuario["id"], _obrigatorio(dados.texto, "a mensagem")),
    )
    return {"id": novo_id}
