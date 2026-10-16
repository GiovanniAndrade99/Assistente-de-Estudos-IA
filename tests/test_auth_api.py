from apoio import DECLARACOES
import hashlib
import logging

from backend import config
from backend.core.seguranca import ITERACOES_SENHA


def _novo_aluno(client, email="aluna@example.test"):
    return client.post("/api/auth/cadastro", json={
        "nome": "Aluna Teste",
        "email": email,
        "senha": "senha-segura-123",
        "tipo": "aluno",
        **DECLARACOES,
    })


def test_cadastro_cria_cookie_seguro_e_persiste_apenas_hash(database, client):
    resposta = _novo_aluno(client)
    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "aluno"

    cookie_header = resposta.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "max-age=604800" in cookie_header

    token = client.cookies.get("sessao")
    sessao = database.consultar_um("SELECT token FROM sessoes")
    usuario = database.consultar_um("SELECT senha_hash FROM usuarios WHERE email = ?", ("aluna@example.test",))
    assert sessao["token"] == hashlib.sha256(token.encode()).hexdigest()
    assert usuario["senha_hash"].startswith(f"{ITERACOES_SENHA}$")
    assert "senha-segura-123" not in usuario["senha_hash"]


def test_login_logout_e_rota_protegida(client):
    resposta = _novo_aluno(client)
    assert resposta.status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/auth/eu").status_code == 401

    login = client.post("/api/auth/login", json={
        "email": "aluna@example.test",
        "senha": "senha-segura-123",
    })
    assert login.status_code == 200
    assert client.get("/api/auth/eu").json()["email"] == "aluna@example.test"


def test_hash_antigo_e_atualizado_apos_login(database, client):
    salt = b"0123456789abcdef"
    senha = "senha-antiga-valida"
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 1000).hex()
    antigo = f"1000${salt.hex()}${digest}"
    database.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
        ("Conta antiga", "antiga@example.test", antigo, "aluno"),
    )

    resposta = client.post("/api/auth/login", json={"email": "antiga@example.test", "senha": senha})
    assert resposta.status_code == 200
    atualizado = database.consultar_um(
        "SELECT senha_hash FROM usuarios WHERE email = ?", ("antiga@example.test",)
    )["senha_hash"]
    assert atualizado.startswith(f"{ITERACOES_SENHA}$")
    assert atualizado != antigo


def test_rate_limit_de_login_e_nao_registra_email_nos_logs(client, caplog):
    email = "nao-existe@example.test"
    with caplog.at_level(logging.INFO, logger="auth"):
        for _ in range(5):
            resposta = client.post("/api/auth/login", json={"email": email, "senha": "senha-incorreta"})
            assert resposta.status_code == 401
        bloqueada = client.post("/api/auth/login", json={"email": email, "senha": "senha-incorreta"})

    assert bloqueada.status_code == 429
    assert email not in caplog.text


def test_cadastro_de_professor_exige_codigo_configurado(client, monkeypatch):
    monkeypatch.setattr(config, "CODIGO_PROFESSOR", "codigo-teste")
    dados = {
        "nome": "Professor Teste",
        "email": "professor@example.test",
        "senha": "senha-segura-123",
        "tipo": "professor",
        **DECLARACOES,
        "codigo_professor": "incorreto",
    }
    assert client.post("/api/auth/cadastro", json=dados).status_code == 403

    dados["codigo_professor"] = "codigo-teste"
    assert client.post("/api/auth/cadastro", json=dados).status_code == 200


def test_resposta_de_erro_tem_request_id_e_nao_armazena_cache(client):
    resposta = client.get("/api/auth/eu", headers={"X-Request-ID": "teste-req-123"})
    assert resposta.status_code == 401
    assert resposta.json()["request_id"] == "teste-req-123"
    assert resposta.headers["X-Request-ID"] == "teste-req-123"
    assert resposta.headers["Cache-Control"] == "no-store"
