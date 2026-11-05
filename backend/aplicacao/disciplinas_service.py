"""Regras de negócio de disciplinas."""
import shutil

from fastapi import HTTPException

from .. import config
from ..infraestrutura import db, rag
from . import demo_service


def disciplina_ou_404(disciplina_id: int) -> dict:
    disciplina = db.consultar_um("SELECT * FROM disciplinas WHERE id = ?", (disciplina_id,))
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    return disciplina


def professor_administra(usuario: dict, disciplina_id: int) -> bool:
    """Administrador vê tudo; professor comum só as disciplinas que escolheu no cadastro."""
    if usuario.get("administrador"):
        return True
    return db.consultar_um(
        "SELECT 1 AS x FROM professor_disciplinas WHERE professor_id = ? AND disciplina_id = ?",
        (usuario["id"], disciplina_id),
    ) is not None


def conferir_acesso(usuario: dict, disciplina_id: int) -> None:
    """404 se a disciplina não existe; 403 se for professor de outra matéria."""
    disciplina_ou_404(disciplina_id)
    if usuario["tipo"] == "professor" and not professor_administra(usuario, disciplina_id):
        raise HTTPException(403, "Você não administra esta disciplina.")


def vincular_professor(professor_id: int, disciplina_ids: list[int]) -> bool:
    """Registra as matérias que o professor administra. False se algum id não existir."""
    ids = set(disciplina_ids)
    marcadores = ",".join("?" * len(ids))
    if len(db.consultar(f"SELECT id FROM disciplinas WHERE id IN ({marcadores})", tuple(ids))) != len(ids):
        return False
    for disciplina_id in ids:
        db.executar("INSERT OR IGNORE INTO professor_disciplinas (professor_id, disciplina_id) VALUES (?, ?)",
                    (professor_id, disciplina_id))
    return True


def listar_disciplinas(usuario: dict) -> list[dict]:
    # Aluno só vê as disciplinas em que está matriculado; professor só as que administra
    # (o administrador vê todas).
    if usuario["tipo"] == "aluno":
        filtro_matricula = "JOIN matriculas m ON m.disciplina_id = d.id AND m.aluno_id = ?"
        parametros = (usuario["id"],)
    elif not usuario.get("administrador"):
        filtro_matricula = "JOIN professor_disciplinas pd ON pd.disciplina_id = d.id AND pd.professor_id = ?"
        parametros = (usuario["id"],)
    else:
        filtro_matricula, parametros = "", ()
    return db.consultar(
        f"""SELECT d.id, d.nome, d.criado_por, u.nome AS criador,
                   (SELECT COUNT(*) FROM documentos WHERE disciplina_id = d.id) AS documentos
            FROM disciplinas d JOIN usuarios u ON u.id = d.criado_por
            {filtro_matricula}
            ORDER BY d.nome""",
        parametros,
    )


def listar_disciplinas_publico() -> list[dict]:
    """Lista mínima (id + nome), sem exigir login: usada na tela de cadastro."""
    return db.consultar("SELECT id, nome FROM disciplinas ORDER BY nome")


def criar_disciplina(nome: str, usuario: dict) -> dict:
    nome = nome.strip()
    if not nome:
        raise HTTPException(400, "Informe o nome da disciplina.")
    if db.consultar_um("SELECT id FROM disciplinas WHERE nome = ?", (nome,)):
        raise HTTPException(400, "Já existe uma disciplina com esse nome.")
    novo_id = db.executar("INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", (nome, usuario["id"]))
    if usuario["tipo"] == "aluno":
        db.executar("INSERT OR IGNORE INTO matriculas (aluno_id, disciplina_id) VALUES (?, ?)",
                     (usuario["id"], novo_id))
    else:
        vincular_professor(usuario["id"], [novo_id])
    demo_service.popular_dados_demo(novo_id)
    return {"id": novo_id, "nome": nome}


def matricular(aluno_id: int, disciplina_ids: list[int]) -> None:
    if not disciplina_ids:
        return
    marcadores = ",".join("?" * len(disciplina_ids))
    validos = db.consultar(f"SELECT id FROM disciplinas WHERE id IN ({marcadores})", tuple(disciplina_ids))
    for disciplina in validos:
        db.executar("INSERT OR IGNORE INTO matriculas (aluno_id, disciplina_id) VALUES (?, ?)",
                     (aluno_id, disciplina["id"]))


def remover_disciplina(disciplina_id: int, usuario_id: int) -> None:
    if disciplina_ou_404(disciplina_id)["criado_por"] != usuario_id:
        raise HTTPException(403, "Só quem criou a disciplina pode removê-la.")
    rag.remover_documento(disciplina_id)
    shutil.rmtree(config.PASTA_UPLOADS / str(disciplina_id), ignore_errors=True)
    db.executar("DELETE FROM disciplinas WHERE id = ?", (disciplina_id,))
