"""Banco de dados relacional (SQLite) com usuários, sessões, disciplinas,
documentos e o histórico de uso (perguntas e notas de simulados).

Os vetores dos trechos continuam no banco vetorial (vetores.py); aqui ficam
só os dados "de sistema".
"""
import sqlite3
from contextlib import contextmanager

from .. import config

ARQUIVO_DB = config.PASTA_DADOS / "app.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('aluno', 'professor')),
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessoes (
    token       TEXT PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disciplinas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL UNIQUE,
    criado_por  INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    arquivo       TEXT NOT NULL,
    trechos       INTEGER NOT NULL,
    enviado_por   INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (disciplina_id, arquivo)
);

CREATE TABLE IF NOT EXISTS perguntas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    pergunta      TEXT NOT NULL,
    resposta      TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resultados_simulado (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    arquivo       TEXT NOT NULL,
    acertos       INTEGER NOT NULL,
    total         INTEGER NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Calendário: eventos do professor valem para a turma (publico = 1);
-- os dos alunos são lembretes pessoais (publico = 0)
CREATE TABLE IF NOT EXISTS eventos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    titulo        TEXT NOT NULL,
    data          TEXT NOT NULL,  -- AAAA-MM-DD
    hora          TEXT,           -- HH:MM, ou NULL para o dia todo
    descricao     TEXT NOT NULL DEFAULT '',
    publico       INTEGER NOT NULL DEFAULT 0,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS atividades (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    criado_por    INTEGER NOT NULL REFERENCES usuarios(id),
    titulo        TEXT NOT NULL,
    descricao     TEXT NOT NULL DEFAULT '',
    prazo         TEXT NOT NULL,  -- AAAA-MM-DD
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entregas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    atividade_id  INTEGER NOT NULL REFERENCES atividades(id) ON DELETE CASCADE,
    aluno_id      INTEGER NOT NULL REFERENCES usuarios(id),
    resposta      TEXT NOT NULL,
    nota          REAL,           -- NULL enquanto o professor não corrigir
    comentario    TEXT,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (atividade_id, aluno_id)
);

CREATE TABLE IF NOT EXISTS videos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    disciplina_id  INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    adicionado_por INTEGER NOT NULL REFERENCES usuarios(id),
    titulo         TEXT NOT NULL,
    url            TEXT NOT NULL,
    descricao      TEXT NOT NULL DEFAULT '',
    criado_em      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Aulas (PDFs) que cada usuário marcou como estudadas: base do progresso por disciplina
CREATE TABLE IF NOT EXISTS aulas_concluidas (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    documento_id  INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, documento_id)
);

CREATE TABLE IF NOT EXISTS mensagens_turma (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    texto         TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tentativas de login/cadastro com falha, por e-mail (rate limit contra força bruta).
-- Tabela nova: não precisa de ALTER TABLE em bancos já existentes.
CREATE TABLE IF NOT EXISTS tentativas_login (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# Colunas criadas depois que o banco já existia: CREATE TABLE IF NOT EXISTS não as
# acrescenta em tabelas antigas, então criar_tabelas() adiciona com ALTER TABLE.
MIGRACOES = [
    ("eventos", "hora", "TEXT"),
    ("sessoes", "expires_at", "TEXT"),
]


@contextmanager
def conectar():
    """Abre uma conexão, faz commit no fim (ou rollback se der erro) e fecha."""
    conexao = sqlite3.connect(ARQUIVO_DB)
    conexao.row_factory = sqlite3.Row  # linhas acessíveis por nome: linha["email"]
    conexao.execute("PRAGMA foreign_keys = ON")
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def criar_tabelas() -> None:
    with conectar() as c:
        c.executescript(ESQUEMA)
        for tabela, coluna, tipo in MIGRACOES:
            colunas = {linha["name"] for linha in c.execute(f"PRAGMA table_info({tabela})")}
            if coluna not in colunas:
                c.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def consultar(sql: str, parametros: tuple = ()) -> list[dict]:
    with conectar() as c:
        return [dict(linha) for linha in c.execute(sql, parametros)]


def consultar_um(sql: str, parametros: tuple = ()) -> dict | None:
    linhas = consultar(sql, parametros)
    return linhas[0] if linhas else None


def executar(sql: str, parametros: tuple = ()) -> int:
    """Executa INSERT/UPDATE/DELETE. Retorna o id da linha inserida."""
    with conectar() as c:
        return c.execute(sql, parametros).lastrowid
