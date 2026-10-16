"""Pseudonimização, retenção, migração de dados antigos e backup."""
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from apoio import DECLARACOES, criar_usuario, entrar

HEX64 = re.compile(r"^[a-z]+:[0-9a-f]{64}$")


def test_tentativas_e_limites_guardam_so_pseudonimos(client, database):
    email = "Pessoa.Real@example.test"
    for _ in range(2):
        client.post("/api/auth/login", json={"email": email, "senha": "senha-errada-123"})
    client.post("/api/auth/cadastro", json={
        "nome": "Teste", "email": "novo@example.test", "senha": "senha-segura-123", "tipo": "aluno",
        **DECLARACOES,
    })

    chaves = [l["chave"] for l in database.consultar("SELECT chave FROM tentativas_login")]
    chaves += [l["chave"] for l in database.consultar("SELECT chave FROM limite_uso WHERE chave NOT LIKE 'usuario:%'")]
    assert chaves, "deveria haver registros de tentativa e de limite"
    for chave in chaves:
        assert HEX64.match(chave), chave
        assert "example.test" not in chave and "testclient" not in chave


def test_limite_por_email_continua_valendo_com_pseudonimo(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "alvo@example.test", "senha": "senha-errada-123"})
    bloqueada = client.post("/api/auth/login", json={"email": "ALVO@example.test", "senha": "senha-errada-123"})
    assert bloqueada.status_code == 429


def test_login_com_email_inexistente_tambem_confere_uma_senha(client, monkeypatch):
    """Tempo de resposta igual: não dá para descobrir quais e-mails têm conta."""
    from backend.aplicacao import auth_service

    chamadas = []
    original = auth_service.conferir_senha
    monkeypatch.setattr(auth_service, "conferir_senha", lambda s, h: chamadas.append(1) or original(s, h))
    assert client.post("/api/auth/login", json={"email": "ninguem@example.test", "senha": "x" * 12}).status_code == 401
    assert chamadas


def test_sessao_sem_validade_e_recusada(client, database):
    from backend.core.seguranca import gerar_token_sessao, hash_token

    usuario_id = criar_usuario("antiga@example.test")
    token = gerar_token_sessao()
    database.executar("INSERT INTO sessoes (token, usuario_id, expires_at) VALUES (?, ?, NULL)",
                      (hash_token(token), usuario_id))
    client.cookies.set("sessao", token)
    assert client.get("/api/auth/eu").status_code == 401


def test_producao_sem_segredo_nao_sobe(monkeypatch):
    from backend import config
    from backend.main import criar_app

    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "SEGREDO_APP", "")
    with pytest.raises(RuntimeError, match="SEGREDO_APP"):
        with TestClient(criar_app(iniciar_tarefas=False)):
            pass


def test_migracao_corrige_banco_antigo(tmp_path, monkeypatch):
    """Banco no formato anterior: e-mail cru nas tentativas, IP cru nos limites,
    sessão sem validade e evento de demonstração duplicado."""
    from backend.infraestrutura import db

    arquivo = tmp_path / "antigo.db"
    conexao = sqlite3.connect(arquivo)
    conexao.executescript("""
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL, tipo TEXT NOT NULL, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE sessoes (token TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE disciplinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE eventos (id INTEGER PRIMARY KEY AUTOINCREMENT, disciplina_id INTEGER NOT NULL, usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL, data TEXT NOT NULL, descricao TEXT NOT NULL DEFAULT '', publico INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE tentativas_login (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE limite_uso (id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT NOT NULL, rota TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES ('Prof. demo', 'demo-professor@exemplo.local', 'x', 'professor');
        INSERT INTO disciplinas (nome, criado_por) VALUES ('Cálculo', 1);
        INSERT INTO sessoes (token, usuario_id) VALUES ('t', 1);
        INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, publico) VALUES (1, 1, 'Revisão', '2026-09-01', 1);
        INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, publico) VALUES (1, 1, 'Revisão', '2026-09-02', 1);
        INSERT INTO tentativas_login (email) VALUES ('pessoa@example.test');
        INSERT INTO limite_uso (chave, rota) VALUES ('ip:203.0.113.9', 'cadastro');
    """)
    conexao.commit()
    conexao.close()

    monkeypatch.setattr(db, "ARQUIVO_DB", arquivo)
    db.criar_tabelas()
    db.criar_tabelas()  # rodar de novo não muda nada

    assert db.consultar("SELECT * FROM sessoes") == []
    assert db.consultar("SELECT * FROM limite_uso") == []
    assert "chave" in {l["name"] for l in db.consultar("PRAGMA table_info(tentativas_login)")}
    assert db.consultar("SELECT COUNT(*) AS n FROM tentativas_login")[0]["n"] == 0
    assert db.consultar("SELECT COUNT(*) AS n FROM eventos")[0]["n"] == 1
    assert db.consultar("PRAGMA user_version")[0]["user_version"] == len(db.MIGRACOES_DE_DADOS)


def test_limpeza_apaga_o_que_passou_do_prazo_e_mantem_o_resto(database):
    from backend.aplicacao import retencao_service

    aluno = criar_usuario("aluno@example.test")
    prof = criar_usuario("prof@example.test", "professor")
    disciplina = database.executar("INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", ("Álgebra", prof))
    for idade, texto in (("-13 months", "antiga"), ("-1 day", "recente")):
        database.executar(
            "INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta, criado_em) "
            "VALUES (?, ?, ?, 'r', datetime('now', ?))", (aluno, disciplina, texto, idade))
        database.executar(
            "INSERT INTO mensagens_turma (disciplina_id, usuario_id, texto, criado_em) VALUES (?, ?, ?, datetime('now', ?))",
            (disciplina, aluno, texto, idade))
    database.executar("INSERT INTO sessoes (token, usuario_id, expires_at) VALUES ('vencida', ?, datetime('now', '-1 hour'))",
                      (aluno,))
    database.executar("INSERT INTO sessoes (token, usuario_id, expires_at) VALUES ('valida', ?, datetime('now', '+1 day'))",
                      (aluno,))
    database.executar("INSERT INTO limite_uso (chave, rota, criado_em) VALUES ('usuario:1', 'chat', datetime('now', '-2 days'))")

    apagados = retencao_service.executar_limpeza()

    assert [l["pergunta"] for l in database.consultar("SELECT pergunta FROM perguntas")] == ["recente"]
    assert [l["texto"] for l in database.consultar("SELECT texto FROM mensagens_turma")] == ["recente"]
    assert [l["token"] for l in database.consultar("SELECT token FROM sessoes")] == ["valida"]
    assert database.consultar("SELECT * FROM limite_uso") == []
    assert apagados["perguntas"] == 1 and apagados["sessoes_vencidas"] == 1


def test_backup_e_restauracao_devolvem_o_banco(database, tmp_path):
    from backend import config
    from scripts import backup, restaurar_backup

    criar_usuario("antes@example.test")
    (config.PASTA_UPLOADS / "1").mkdir()
    (config.PASTA_UPLOADS / "1" / "aula.pdf").write_bytes(b"%PDF-1.4 teste")

    pasta = backup.fazer_backup()
    assert (pasta / "manifesto.json").exists()
    assert (pasta / "uploads" / "1" / "aula.pdf").exists()

    criar_usuario("depois@example.test")
    reserva = restaurar_backup.restaurar(pasta)

    emails = [l["email"] for l in database.consultar("SELECT email FROM usuarios")]
    assert emails == ["antes@example.test"]
    assert reserva is not None and (reserva / "app.db").exists()
    assert (config.PASTA_UPLOADS / "1" / "aula.pdf").read_bytes() == b"%PDF-1.4 teste"


def test_backups_vencidos_sao_apagados(tmp_path):
    from scripts import backup

    (tmp_path / "2020-01-01_000000").mkdir()
    (tmp_path / "pasta-qualquer").mkdir()
    recente = backup.fazer_backup(tmp_path)
    apagados = backup.apagar_vencidos(tmp_path, dias=30)
    assert [p.name for p in apagados] == ["2020-01-01_000000"]
    assert recente.exists() and (tmp_path / "pasta-qualquer").exists()


def test_entrar_continua_funcionando(client):
    criar_usuario("ok@example.test")
    entrar(client, "ok@example.test")
    assert client.get("/api/auth/eu").json()["email"] == "ok@example.test"
