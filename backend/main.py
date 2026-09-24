"""API do Assistente de Estudos (FastAPI).

Rodar a partir da pasta raiz do projeto:
    uvicorn backend.main:app --reload --port 8002
e abrir http://localhost:8002
"""
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.genai.errors import APIError
from pydantic import BaseModel, Field

from . import auth, config, db, demo, estudo, rag, turma
from .auth import somente_professor, usuario_atual

db.criar_tabelas()
for _disciplina_demo in db.consultar("SELECT id FROM disciplinas"):
    demo.popular_dados_demo(_disciplina_demo["id"])
app = FastAPI(title="Assistente de Estudos")
app.include_router(auth.router)
app.include_router(turma.router)


# Erros conhecidos viram mensagens legíveis para o frontend
@app.exception_handler(ValueError)
@app.exception_handler(RuntimeError)
def erro_de_uso(request: Request, erro: Exception):
    return JSONResponse(status_code=400, content={"detail": str(erro)})


@app.exception_handler(APIError)
def erro_do_gemini(request: Request, erro: APIError):
    return JSONResponse(status_code=502, content={"detail": f"Erro na API do Gemini: {erro.message}"})


class NovaDisciplina(BaseModel):
    nome: str


class Pergunta(BaseModel):
    pergunta: str


class PedidoEstudo(BaseModel):
    arquivo: str
    quantidade: int = Field(default=10, ge=1, le=30)


class AulaConcluida(BaseModel):
    concluida: bool


class ResultadoSimulado(BaseModel):
    arquivo: str
    acertos: int = Field(ge=0)
    total: int = Field(ge=1)


def _disciplina(disciplina_id: int) -> dict:
    disciplina = db.consultar_um("SELECT * FROM disciplinas WHERE id = ?", (disciplina_id,))
    if not disciplina:
        raise HTTPException(404, "Disciplina não encontrada.")
    return disciplina


def _nome_seguro(arquivo: str) -> str:
    return Path(arquivo).name  # evita caminhos como ../../


# ---------------------------------------------------------------- disciplinas

@app.get("/api/disciplinas")
def listar_disciplinas(usuario: dict = Depends(usuario_atual)):
    return db.consultar(
        """SELECT d.id, d.nome, d.criado_por, u.nome AS criador,
                  (SELECT COUNT(*) FROM documentos WHERE disciplina_id = d.id) AS documentos
           FROM disciplinas d JOIN usuarios u ON u.id = d.criado_por
           ORDER BY d.nome"""
    )


@app.post("/api/disciplinas")
def criar_disciplina(dados: NovaDisciplina, usuario: dict = Depends(usuario_atual)):
    nome = dados.nome.strip()
    if not nome:
        raise HTTPException(400, "Informe o nome da disciplina.")
    if db.consultar_um("SELECT id FROM disciplinas WHERE nome = ?", (nome,)):
        raise HTTPException(400, "Já existe uma disciplina com esse nome.")
    novo_id = db.executar("INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", (nome, usuario["id"]))
    demo.popular_dados_demo(novo_id)
    return {"id": novo_id, "nome": nome}


@app.delete("/api/disciplinas/{disciplina_id}")
def remover_disciplina(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    if _disciplina(disciplina_id)["criado_por"] != usuario["id"]:
        raise HTTPException(403, "Só quem criou a disciplina pode removê-la.")
    rag.remover_documento(disciplina_id)
    shutil.rmtree(config.PASTA_UPLOADS / str(disciplina_id), ignore_errors=True)
    db.executar("DELETE FROM disciplinas WHERE id = ?", (disciplina_id,))
    return {"ok": True}


# ---------------------------------------------------------------- documentos

@app.get("/api/disciplinas/{disciplina_id}/documentos")
def listar_documentos(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    _disciplina(disciplina_id)
    return db.consultar(
        """SELECT doc.id, doc.arquivo, doc.trechos, doc.criado_em, u.nome AS enviado_por,
                  (c.documento_id IS NOT NULL) AS concluida
           FROM documentos doc JOIN usuarios u ON u.id = doc.enviado_por
           LEFT JOIN aulas_concluidas c ON c.documento_id = doc.id AND c.usuario_id = ?
           WHERE doc.disciplina_id = ? ORDER BY doc.arquivo""",
        (usuario["id"], disciplina_id),
    )


@app.post("/api/disciplinas/{disciplina_id}/documentos")
def enviar_documento(disciplina_id: int, arquivo: UploadFile, usuario: dict = Depends(usuario_atual)):
    _disciplina(disciplina_id)
    nome = _nome_seguro(arquivo.filename or "")
    if not nome.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um arquivo .pdf")

    destino = rag.caminho_do_pdf(disciplina_id, nome)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(arquivo.file.read())
    try:
        trechos = rag.indexar_pdf(disciplina_id, nome)
    except Exception:
        destino.unlink(missing_ok=True)
        raise

    db.executar(
        """INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por) VALUES (?, ?, ?, ?)
           ON CONFLICT (disciplina_id, arquivo) DO UPDATE
           SET trechos = excluded.trechos, enviado_por = excluded.enviado_por, criado_em = CURRENT_TIMESTAMP""",
        (disciplina_id, nome, trechos, usuario["id"]),
    )
    return {"arquivo": nome, "trechos": trechos}


@app.delete("/api/disciplinas/{disciplina_id}/documentos/{arquivo}")
def remover_documento(disciplina_id: int, arquivo: str, usuario: dict = Depends(usuario_atual)):
    nome = _nome_seguro(arquivo)
    rag.remover_documento(disciplina_id, nome)
    rag.caminho_do_pdf(disciplina_id, nome).unlink(missing_ok=True)
    db.executar("DELETE FROM documentos WHERE disciplina_id = ? AND arquivo = ?", (disciplina_id, nome))
    return {"ok": True}


# ---------------------------------------------------------------- chat (RAG)

@app.post("/api/disciplinas/{disciplina_id}/chat")
def chat(disciplina_id: int, dados: Pergunta, usuario: dict = Depends(usuario_atual)):
    _disciplina(disciplina_id)
    if not dados.pergunta.strip():
        raise HTTPException(400, "Pergunta vazia")
    resultado = rag.responder(dados.pergunta, disciplina_id)
    db.executar(  # histórico usado no painel do professor
        "INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta) VALUES (?, ?, ?, ?)",
        (usuario["id"], disciplina_id, dados.pergunta.strip(), resultado["resposta"]),
    )
    return resultado


# ---------------------------------------------------------------- estudo

@app.post("/api/disciplinas/{disciplina_id}/resumo")
def resumo(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(usuario_atual)):
    return estudo.resumir(disciplina_id, _nome_seguro(dados.arquivo))


@app.post("/api/disciplinas/{disciplina_id}/flashcards")
def flashcards(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(usuario_atual)):
    return estudo.gerar_flashcards(disciplina_id, _nome_seguro(dados.arquivo), dados.quantidade)


@app.post("/api/disciplinas/{disciplina_id}/simulado")
def simulado(disciplina_id: int, dados: PedidoEstudo, usuario: dict = Depends(usuario_atual)):
    return estudo.gerar_simulado(disciplina_id, _nome_seguro(dados.arquivo), dados.quantidade)


@app.post("/api/disciplinas/{disciplina_id}/simulado/resultado")
def salvar_resultado(disciplina_id: int, dados: ResultadoSimulado, usuario: dict = Depends(usuario_atual)):
    _disciplina(disciplina_id)
    if dados.acertos > dados.total:
        raise HTTPException(400, "Acertos maior que o total.")
    db.executar(
        """INSERT INTO resultados_simulado (usuario_id, disciplina_id, arquivo, acertos, total)
           VALUES (?, ?, ?, ?, ?)""",
        (usuario["id"], disciplina_id, _nome_seguro(dados.arquivo), dados.acertos, dados.total),
    )
    return {"ok": True}


@app.get("/api/disciplinas/{disciplina_id}/simulado/meus")
def meus_resultados(disciplina_id: int, usuario: dict = Depends(usuario_atual)):
    return db.consultar(
        """SELECT arquivo, acertos, total, criado_em FROM resultados_simulado
           WHERE disciplina_id = ? AND usuario_id = ? ORDER BY criado_em DESC LIMIT 50""",
        (disciplina_id, usuario["id"]),
    )


# ---------------------------------------------------------------- visão geral e progresso

@app.get("/api/visao-geral")
def visao_geral(usuario: dict = Depends(usuario_atual)):
    """Todas as disciplinas com suas aulas (e se o usuário já estudou cada uma) e atividades."""
    disciplinas = {d["id"]: {**d, "aulas": [], "atividades": []}
                   for d in db.consultar("SELECT id, nome FROM disciplinas ORDER BY nome")}
    for aula in db.consultar(
        """SELECT doc.id, doc.disciplina_id, doc.arquivo, (c.documento_id IS NOT NULL) AS concluida
           FROM documentos doc
           LEFT JOIN aulas_concluidas c ON c.documento_id = doc.id AND c.usuario_id = ?
           ORDER BY doc.arquivo""",
        (usuario["id"],),
    ):
        disciplinas[aula.pop("disciplina_id")]["aulas"].append({**aula, "concluida": bool(aula["concluida"])})
    for atividade in db.consultar(
        """SELECT a.id, a.disciplina_id, a.titulo, a.prazo, e.criado_em AS entregue_em, e.nota,
                  (SELECT COUNT(*) FROM entregas WHERE atividade_id = a.id) AS total_entregas
           FROM atividades a
           LEFT JOIN entregas e ON e.atividade_id = a.id AND e.aluno_id = ?
           ORDER BY a.prazo, a.id""",
        (usuario["id"],),
    ):
        disciplinas[atividade.pop("disciplina_id")]["atividades"].append(atividade)
    return list(disciplinas.values())


@app.put("/api/aulas/{documento_id}/concluida")
def marcar_aula(documento_id: int, dados: AulaConcluida, usuario: dict = Depends(usuario_atual)):
    if not db.consultar_um("SELECT id FROM documentos WHERE id = ?", (documento_id,)):
        raise HTTPException(404, "Aula não encontrada.")
    if dados.concluida:
        db.executar("INSERT OR IGNORE INTO aulas_concluidas (usuario_id, documento_id) VALUES (?, ?)",
                    (usuario["id"], documento_id))
    else:
        db.executar("DELETE FROM aulas_concluidas WHERE usuario_id = ? AND documento_id = ?",
                    (usuario["id"], documento_id))
    return {"ok": True}


# ---------------------------------------------------------------- lembretes

@app.get("/api/lembretes")
def lembretes_do_dia(data: str, usuario: dict = Depends(usuario_atual)):
    """Eventos com horário do dia (de todas as disciplinas), para o aviso na hora marcada."""
    return db.consultar(
        """SELECT e.id, e.titulo, e.hora, e.descricao, d.nome AS disciplina
           FROM eventos e JOIN disciplinas d ON d.id = e.disciplina_id
           WHERE e.data = ? AND e.hora IS NOT NULL AND (e.publico = 1 OR e.usuario_id = ?)
           ORDER BY e.hora""",
        (data, usuario["id"]),
    )


# ---------------------------------------------------------------- painel do professor

@app.get("/api/professor/perguntas")
def perguntas_dos_alunos(disciplina_id: int, professor: dict = Depends(somente_professor)):
    return db.consultar(
        """SELECT p.pergunta, p.resposta, p.criado_em, u.nome AS aluno
           FROM perguntas p JOIN usuarios u ON u.id = p.usuario_id
           WHERE p.disciplina_id = ? AND u.tipo = 'aluno'
           ORDER BY p.criado_em DESC LIMIT 200""",
        (disciplina_id,),
    )


@app.get("/api/professor/notas")
def notas_dos_alunos(disciplina_id: int, professor: dict = Depends(somente_professor)):
    return db.consultar(
        """SELECT u.nome AS aluno, r.arquivo, r.acertos, r.total, r.criado_em
           FROM resultados_simulado r JOIN usuarios u ON u.id = r.usuario_id
           WHERE r.disciplina_id = ? AND u.tipo = 'aluno'
           ORDER BY r.criado_em DESC LIMIT 200""",
        (disciplina_id,),
    )


# O próprio FastAPI serve o frontend (HTML/CSS/JS). Precisa ficar por último.
app.mount("/", StaticFiles(directory=config.PASTA_FRONTEND, html=True), name="frontend")
