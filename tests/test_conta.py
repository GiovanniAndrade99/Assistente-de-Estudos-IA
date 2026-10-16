"""Direitos do titular: exportar e excluir a conta, canal LGPD no suporte e
moderação do chat da turma."""
import json
import sqlite3

import pytest

from apoio import criar_disciplina, criar_usuario, entrar, matricular


@pytest.fixture
def turma(client, database):
    ids = {
        "prof": criar_usuario("prof@example.test", "professor", nome="Profa. Ana"),
        "aluna": criar_usuario("aluna@example.test", nome="Aluna Bia"),
        "colega": criar_usuario("colega@example.test", nome="Colega Caio"),
        "admin": criar_usuario("admin@example.test", "professor", administrador=True),
    }
    ids["disciplina"] = criar_disciplina("Cálculo I", ids["prof"])
    matricular(ids["aluna"], ids["disciplina"])
    matricular(ids["colega"], ids["disciplina"])
    d, a = ids["disciplina"], ids["aluna"]
    database.executar("INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta) VALUES (?, ?, 'O que é limite?', 'r')", (a, d))
    database.executar("INSERT INTO resultados_simulado (usuario_id, disciplina_id, arquivo, acertos, total) VALUES (?, ?, 'a.pdf', 3, 5)", (a, d))
    database.executar("INSERT INTO mensagens_turma (disciplina_id, usuario_id, texto) VALUES (?, ?, 'oi turma')", (d, a))
    database.executar("INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, publico) VALUES (?, ?, 'Lembrete', '2026-12-01', 0)", (d, a))
    atividade = database.executar("INSERT INTO atividades (disciplina_id, criado_por, titulo, prazo) VALUES (?, ?, 'Lista 1', '2026-12-10')", (d, ids["prof"]))
    database.executar("INSERT INTO entregas (atividade_id, aluno_id, resposta) VALUES (?, ?, 'minha resposta')", (atividade, a))
    database.executar("INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, publico) VALUES (?, ?, 'Prova', '2026-12-15', 1)", (d, ids["prof"]))
    database.executar("INSERT INTO chamados_suporte (usuario_id, categoria, assunto, mensagem) VALUES (?, 'Sugestão', 'a', 'b')", (a,))
    return ids


def test_toda_referencia_a_usuarios_e_tratada_na_exclusao(database):
    """Estrutural: tabela nova com FK para usuarios sem CASCADE quebraria a exclusão de conta."""
    from backend.aplicacao import conta_service

    tratadas = set(conta_service.REATRIBUIR_AO_SISTEMA + conta_service.APAGAR + conta_service.TRATADOS_A_PARTE)
    conexao = sqlite3.connect(database.ARQUIVO_DB)
    faltando = []
    for (tabela,) in conexao.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
        for fk in conexao.execute(f"PRAGMA foreign_key_list({tabela})"):
            if fk[2] == "usuarios" and fk[6] != "CASCADE" and (tabela, fk[3]) not in tratadas:
                faltando.append(f"{tabela}.{fk[3]}")
    conexao.close()
    assert faltando == []


def test_exportacao_traz_tudo_e_nenhum_segredo(client, turma):
    entrar(client, "aluna@example.test")
    resposta = client.get("/api/conta/meus-dados")
    assert resposta.status_code == 200
    assert "attachment" in resposta.headers["Content-Disposition"]
    dados = json.loads(resposta.content)
    assert dados["conta"]["email"] == "aluna@example.test"
    assert dados["perguntas_ao_assistente"][0]["pergunta"] == "O que é limite?"
    assert dados["mensagens_no_chat_da_turma"][0]["texto"] == "oi turma"
    assert dados["entregas_de_atividades"][0]["resposta"] == "minha resposta"
    assert dados["matriculas"][0]["disciplina"] == "Cálculo I"
    assert dados["sessoes_ativas"]
    texto = resposta.text
    assert "senha_hash" not in texto and "token" not in texto
    assert "colega@example.test" not in texto  # nada de dados de outras pessoas


def test_excluir_conta_de_aluno_apaga_os_dados_dela(client, database, turma):
    entrar(client, "aluna@example.test")
    assert client.request("DELETE", "/api/conta", json={"senha": "errada-123456", "confirmacao": "EXCLUIR"}).status_code == 400
    assert client.request("DELETE", "/api/conta", json={"senha": "senha-segura-123", "confirmacao": "sim"}).status_code == 400

    resposta = client.request("DELETE", "/api/conta", json={"senha": "senha-segura-123", "confirmacao": "excluir"})
    assert resposta.status_code == 200
    a = turma["aluna"]
    for tabela, coluna in [("usuarios", "id"), ("perguntas", "usuario_id"), ("resultados_simulado", "usuario_id"),
                           ("mensagens_turma", "usuario_id"), ("eventos", "usuario_id"), ("entregas", "aluno_id"),
                           ("matriculas", "aluno_id"), ("sessoes", "usuario_id"), ("chamados_suporte", "usuario_id")]:
        assert database.consultar(f"SELECT 1 FROM {tabela} WHERE {coluna} = ?", (a,)) == [], tabela
    assert client.get("/api/auth/eu").status_code == 401
    assert client.post("/api/auth/login", json={"email": "aluna@example.test", "senha": "senha-segura-123"}).status_code == 401

    from backend import config
    registro = (config.PASTA_DADOS / "exclusoes.jsonl").read_text(encoding="utf-8")
    assert json.loads(registro.splitlines()[-1])["usuario_id"] == a
    assert "aluna@example.test" not in registro


def test_excluir_conta_de_professor_mantem_a_disciplina_para_os_alunos(client, database, turma):
    entrar(client, "prof@example.test")
    assert client.request("DELETE", "/api/conta", json={"senha": "senha-segura-123", "confirmacao": "EXCLUIR"}).status_code == 200

    sistema = database.consultar_um("SELECT * FROM usuarios WHERE sistema = 1")
    assert sistema["nome"] == "Professor removido"
    assert database.consultar_um("SELECT criado_por FROM disciplinas WHERE id = ?", (turma["disciplina"],))["criado_por"] == sistema["id"]
    assert database.consultar("SELECT titulo FROM eventos WHERE usuario_id = ?", (sistema["id"],)) == [{"titulo": "Prova"}]
    assert database.consultar_um("SELECT 1 FROM entregas") is not None  # entregas dos alunos continuam

    # A aluna continua vendo a disciplina; a conta de sistema não entra
    entrar(client, "aluna@example.test")
    assert [d["id"] for d in client.get("/api/disciplinas").json()] == [turma["disciplina"]]
    assert client.post("/api/auth/login", json={"email": sistema["email"], "senha": "!"}).status_code == 401

    # O admin vê a disciplina sem professor e a transfere
    novo = criar_usuario("novo@example.test", "professor", nome="Prof. Novo")
    entrar(client, "admin@example.test")
    assert [d["nome"] for d in client.get("/api/admin/disciplinas-sem-professor").json()] == ["Cálculo I"]
    resposta = client.put(f"/api/admin/disciplinas/{turma['disciplina']}/professor",
                          json={"email_professor": "novo@example.test"})
    assert resposta.status_code == 200
    assert database.consultar_um("SELECT criado_por FROM disciplinas")["criado_por"] == novo
    assert client.get("/api/admin/disciplinas-sem-professor").json() == []


def test_unico_admin_nao_pode_excluir_a_conta(client, turma):
    entrar(client, "admin@example.test")
    corpo = {"senha": "senha-segura-123", "confirmacao": "EXCLUIR"}
    assert client.request("DELETE", "/api/conta", json=corpo).status_code == 409
    criar_usuario("admin2@example.test", "professor", administrador=True)
    assert client.request("DELETE", "/api/conta", json=corpo).status_code == 200


def test_rotas_de_admin_so_para_admin(client, turma):
    entrar(client, "prof@example.test")
    assert client.get("/api/admin/disciplinas-sem-professor").status_code == 403


def test_exclusao_e_refeita_depois_de_restaurar_backup(client, database, turma):
    from scripts import backup, restaurar_backup

    pasta = backup.fazer_backup()
    entrar(client, "aluna@example.test")
    client.request("DELETE", "/api/conta", json={"senha": "senha-segura-123", "confirmacao": "EXCLUIR"})

    restaurar_backup.restaurar(pasta)
    assert database.consultar("SELECT 1 FROM usuarios WHERE email = 'aluna@example.test'") == []
    assert database.consultar("SELECT 1 FROM perguntas") == []


def test_canal_lgpd_no_suporte_tem_prazo(client, turma):
    entrar(client, "aluna@example.test")
    categorias = client.get("/api/suporte/categorias").json()
    assert categorias["categoria_lgpd"] in categorias["categorias"]
    client.post("/api/suporte/chamados", json={
        "categoria": categorias["categoria_lgpd"], "assunto": "Meus dados", "mensagem": "Quero corrigir um dado.",
    })
    entrar(client, "admin@example.test")
    primeiro = client.get("/api/suporte/chamados").json()[0]
    assert primeiro["categoria"] == categorias["categoria_lgpd"]
    assert primeiro["prazo_resposta"] and not primeiro["prazo_vencido"]


def test_mensagem_da_turma_so_quem_escreveu_ou_o_professor_apaga(client, database, turma):
    mensagem = database.consultar_um("SELECT id FROM mensagens_turma")["id"]
    rota = f"/api/disciplinas/{turma['disciplina']}/mensagens/{mensagem}"
    entrar(client, "colega@example.test")
    assert client.delete(rota).status_code == 403
    entrar(client, "aluna@example.test")
    assert client.delete(rota).status_code == 200
    assert database.consultar("SELECT 1 FROM mensagens_turma") == []
