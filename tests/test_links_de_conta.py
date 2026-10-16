"""Recuperação de senha, confirmação de e-mail e troca de e-mail."""
import logging
import re

from apoio import DECLARACOES, criar_usuario, entrar


def _token(mensagem) -> str:
    return re.search(r"#t=([\w-]+)", mensagem.get_content()).group(1)


def test_redefinir_senha_de_ponta_a_ponta(client, database, caixa_de_email):
    criar_usuario("pessoa@example.test")
    entrar(client, "pessoa@example.test")  # sessão antiga, que deve cair

    resposta = client.post("/api/auth/esqueci-senha", json={"email": "Pessoa@example.test"})
    assert resposta.status_code == 200
    assert len(caixa_de_email) == 1
    mensagem = caixa_de_email[0]
    assert mensagem["To"] == "pessoa@example.test"
    token = _token(mensagem)
    assert database.consultar("SELECT 1 FROM tokens_conta WHERE token_hash = ?", (token,)) == []  # só o hash

    assert client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "senha-nova-456"}).status_code == 200
    assert client.get("/api/auth/eu").status_code == 401  # todas as sessões encerradas
    assert client.post("/api/auth/login", json={"email": "pessoa@example.test", "senha": "senha-segura-123"}).status_code == 401
    entrar(client, "pessoa@example.test", "senha-nova-456")

    reuso = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "outra-senha-789"})
    assert reuso.status_code == 400


def test_link_vencido_nao_vale(client, database, caixa_de_email):
    criar_usuario("pessoa@example.test")
    client.post("/api/auth/esqueci-senha", json={"email": "pessoa@example.test"})
    database.executar("UPDATE tokens_conta SET expires_at = datetime('now', '-1 minute')")
    token = _token(caixa_de_email[0])
    assert client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "senha-nova-456"}).status_code == 400


def test_email_inexistente_tem_a_mesma_resposta(client, caixa_de_email):
    criar_usuario("existe@example.test")
    existe = client.post("/api/auth/esqueci-senha", json={"email": "existe@example.test"})
    nao_existe = client.post("/api/auth/esqueci-senha", json={"email": "nao-existe@example.test"})
    assert existe.status_code == nao_existe.status_code == 200
    assert existe.json() == nao_existe.json()
    assert [m["To"] for m in caixa_de_email] == ["existe@example.test"]


def test_sem_smtp_em_producao_responde_503(client, monkeypatch):
    from backend import config

    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "SMTP_HOST", "")
    assert client.post("/api/auth/esqueci-senha", json={"email": "x@example.test"}).status_code == 503


def test_sem_smtp_em_desenvolvimento_o_link_vai_para_o_log_sem_o_email(client, caplog):
    criar_usuario("dev@example.test")
    with caplog.at_level(logging.WARNING, logger="correio"):
        client.post("/api/auth/esqueci-senha", json={"email": "dev@example.test"})
    registro = [r for r in caplog.records if r.getMessage() == "email_so_no_log_desenvolvimento"][0]
    assert "#t=" in registro.link
    assert "dev@example.test" not in caplog.text


def test_cadastro_envia_confirmacao_de_email(client, caixa_de_email):
    resposta = client.post("/api/auth/cadastro", json={
        "nome": "Nova", "email": "nova@example.test", "senha": "senha-segura-123", "tipo": "aluno", **DECLARACOES,
    })
    assert resposta.json()["email_verificado"] is False
    token = _token(caixa_de_email[0])
    assert client.post("/api/auth/confirmar-email", json={"token": token}).json()["resultado"] == "verificado"
    assert client.get("/api/auth/eu").json()["email_verificado"] is True


def test_troca_de_email_so_vale_depois_de_confirmar_no_endereco_novo(client, database, caixa_de_email):
    criar_usuario("antigo@example.test")
    criar_usuario("ocupado@example.test")
    entrar(client, "antigo@example.test")

    assert client.put("/api/conta/email", json={"novo_email": "novo@example.test", "senha": "errada-12345"}).status_code == 400
    assert client.put("/api/conta/email", json={"novo_email": "ocupado@example.test", "senha": "senha-segura-123"}).status_code == 400

    assert client.put("/api/conta/email", json={"novo_email": "novo@example.test", "senha": "senha-segura-123"}).status_code == 200
    assert {m["To"] for m in caixa_de_email} == {"novo@example.test", "antigo@example.test"}
    assert client.get("/api/auth/eu").json()["email"] == "antigo@example.test"  # ainda não mudou

    para_o_novo = next(m for m in caixa_de_email if m["To"] == "novo@example.test")
    assert client.post("/api/auth/confirmar-email", json={"token": _token(para_o_novo)}).json()["resultado"] == "trocado"
    assert client.get("/api/auth/eu").json()["email"] == "novo@example.test"
