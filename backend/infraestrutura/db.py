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
    administrador INTEGER NOT NULL DEFAULT 0 CHECK (administrador IN (0, 1)),
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

-- Suporte: chamados abertos pelos usuários e respondidos por um administrador
CREATE TABLE IF NOT EXISTS chamados_suporte (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria     TEXT NOT NULL,
    assunto       TEXT NOT NULL,
    mensagem      TEXT NOT NULL,
    resposta      TEXT,           -- NULL enquanto ninguém responder
    respondido_em TEXT,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensagens_turma (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    texto         TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tentativas de login com falha (limite contra força bruta). `chave` é um pseudônimo
-- (HMAC) do e-mail digitado, nunca o e-mail em si (aplicacao/pseudonimo.py).
CREATE TABLE IF NOT EXISTS tentativas_login (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chave       TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Rate limit genérico (aplicacao/limite_service.py): quantas requisições uma
-- chave fez a uma rota, para bloquear automação/abuso de custo. A chave é
-- "usuario:<id>" ou o pseudônimo (HMAC) de um IP; nunca o IP em si.
CREATE TABLE IF NOT EXISTS limite_uso (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chave       TEXT NOT NULL,
    rota        TEXT NOT NULL,
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_limite_uso_chave_rota ON limite_uso (chave, rota, criado_em);

-- Matrícula do aluno nas disciplinas que escolheu (no cadastro ou depois).
-- Tabela nova: o backfill de quem já tinha conta fica em criar_tabelas().
CREATE TABLE IF NOT EXISTS matriculas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    disciplina_id INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (aluno_id, disciplina_id)
);

-- Simulados gerados: o gabarito fica só aqui até a pessoa responder, e a nota é
-- calculada pelo servidor (antes o navegador recebia o gabarito e informava a nota).
CREATE TABLE IF NOT EXISTS simulados (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    disciplina_id  INTEGER NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    arquivo        TEXT NOT NULL,
    questoes_json  TEXT NOT NULL,
    respostas_json TEXT,
    acertos        INTEGER,
    total          INTEGER NOT NULL,
    criado_em      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_em  TEXT
);

-- Métricas de uso sem dado pessoal: só contagens por dia e por evento
-- (infraestrutura/metricas.py). Não há coluna de usuário de propósito.
CREATE TABLE IF NOT EXISTS metricas_diarias (
    dia     TEXT NOT NULL,
    evento  TEXT NOT NULL,
    total   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (dia, evento)
);

-- Links enviados por e-mail (redefinir senha, confirmar e-mail, trocar e-mail). Guarda só
-- o hash do token, que vale uma vez e expira. `dado` é o novo e-mail, na troca.
CREATE TABLE IF NOT EXISTS tokens_conta (
    token_hash  TEXT PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL CHECK (tipo IN ('redefinir_senha', 'verificar_email', 'trocar_email')),
    dado        TEXT,
    expires_at  TEXT NOT NULL,
    usado_em    TEXT,
    criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# Colunas criadas depois que o banco já existia: CREATE TABLE IF NOT EXISTS não as
# acrescenta em tabelas antigas, então criar_tabelas() adiciona com ALTER TABLE.
MIGRACOES = [
    ("eventos", "hora", "TEXT"),
    ("sessoes", "expires_at", "TEXT"),
    ("usuarios", "administrador", "INTEGER NOT NULL DEFAULT 0"),
    # Ciência do aviso de privacidade e declaração de idade mínima (LGPD, arts. 9º e 14).
    # Não guardamos data de nascimento: só a versão do aviso lido e quando a pessoa declarou.
    ("usuarios", "aceite_privacidade_versao", "TEXT"),
    ("usuarios", "aceite_privacidade_em", "TEXT"),
    ("usuarios", "maioridade_declarada_em", "TEXT"),
    ("usuarios", "ultimo_acesso", "TEXT"),
    ("usuarios", "email_verificado_em", "TEXT"),
    # Conta de sistema ("Professor removido"): recebe as disciplinas de professores que
    # excluíram a conta e não faz login.
    ("usuarios", "sistema", "INTEGER NOT NULL DEFAULT 0"),
]


@contextmanager
def conectar():
    """Abre uma conexão, faz commit no fim (ou rollback se der erro) e fecha."""
    # timeout: espera até 15 s por um lock (a indexação em segundo plano grava em paralelo)
    conexao = sqlite3.connect(ARQUIVO_DB, timeout=15)
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


def _migracao_dados_1(c) -> None:
    """Pseudonimização e limpeza de dados antigos (out/2026)."""
    # Sessões criadas antes de expires_at existir nunca expiravam
    c.execute("DELETE FROM sessoes WHERE expires_at IS NULL")
    # Limites e tentativas guardavam IP e e-mail em texto puro. São registros de
    # minutos, então é seguro apagar tudo; os novos já entram pseudonimizados.
    c.execute("DELETE FROM limite_uso")
    colunas = {linha["name"] for linha in c.execute("PRAGMA table_info(tentativas_login)")}
    if "email" in colunas:
        c.execute("DROP TABLE tentativas_login")
        c.execute(
            """CREATE TABLE tentativas_login (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   chave TEXT NOT NULL,
                   criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"""
        )
    # Eventos de demonstração eram recriados a cada dia de reinício do servidor
    c.execute(
        """DELETE FROM eventos WHERE id IN (
               SELECT e.id FROM eventos e JOIN usuarios u ON u.id = e.usuario_id
               WHERE u.email LIKE 'demo-%@exemplo.local' AND e.id NOT IN (
                   SELECT MIN(e2.id) FROM eventos e2 JOIN usuarios u2 ON u2.id = e2.usuario_id
                   WHERE u2.email LIKE 'demo-%@exemplo.local'
                   GROUP BY e2.disciplina_id, e2.usuario_id, e2.titulo))"""
    )


# Correções de dados que rodam uma única vez por banco, na ordem. O número
# aplicado fica em PRAGMA user_version.
MIGRACOES_DE_DADOS = [
    _migracao_dados_1,
]


def criar_tabelas() -> None:
    with conectar() as c:
        matriculas_e_nova = not c.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'matriculas'"
        ).fetchone()
        c.executescript(ESQUEMA)
        for tabela, coluna, tipo in MIGRACOES:
            colunas = {linha["name"] for linha in c.execute(f"PRAGMA table_info({tabela})")}
            if coluna not in colunas:
                c.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        versao = c.execute("PRAGMA user_version").fetchone()[0]
        for numero, migracao in enumerate(MIGRACOES_DE_DADOS, start=1):
            if numero > versao:
                migracao(c)
                c.execute(f"PRAGMA user_version = {numero}")
        if matriculas_e_nova:
            # Quem já tinha conta antes da matrícula por disciplina existir via todas as
            # disciplinas; sem isso perderia acesso ao que já estudava.
            c.execute(
                """INSERT INTO matriculas (aluno_id, disciplina_id)
                   SELECT u.id, d.id FROM usuarios u, disciplinas d WHERE u.tipo = 'aluno'"""
            )


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
