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
        "codigo_professor": "incorreto",
    }
    assert client.post("/api/auth/cadastro", json=dados).status_code == 403

    dados["codigo_professor"] = "codigo-teste"
    assert client.post("/api/auth/cadastro", json=dados).status_code == 400  # falta escolher a matéria


def test_professor_escolhe_materia_e_confirma_email(client, database, monkeypatch):
    from backend.aplicacao import auth_service

    monkeypatch.setattr(config, "CODIGO_PROFESSOR", "codigo-teste")
    monkeypatch.setattr(config, "SMTP_HOST", "")
    enviados = []
    monkeypatch.setattr(auth_service, "enviar_email", lambda destino, assunto, corpo: enviados.append(corpo))

    dono = database.executar("INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES ('Dono', 'd@x.test', 'x', 'professor')")
    minha = database.executar("INSERT INTO disciplinas (nome, criado_por) VALUES ('Minha', ?)", (dono,))
    outra = database.executar("INSERT INTO disciplinas (nome, criado_por) VALUES ('Outra', ?)", (dono,))

    dados = {"nome": "Prof", "email": "prof@example.test", "senha": "senha-segura-123", "tipo": "professor",
             "codigo_professor": "codigo-teste", "disciplinas": [minha]}
    resposta = client.post("/api/auth/cadastro", json=dados)
    assert resposta.json() == {"verificacao_pendente": True, "email": "prof@example.test"}
    assert "sessao" not in resposta.cookies

    # sem confirmar o e-mail não há sessão: o login só reenvia o código
    login = {"email": "prof@example.test", "senha": "senha-segura-123"}
    assert client.post("/api/auth/login", json=login).json()["verificacao_pendente"] is True

    codigo = enviados[0].split("é: ")[1][:6]
    assert client.post("/api/auth/verificar-email", json={"email": "prof@example.test", "codigo": "x" * 6}).status_code == 400
    assert client.post("/api/auth/verificar-email", json={"email": "prof@example.test", "codigo": codigo}).status_code == 200

    # só enxerga a matéria que escolheu
    assert [d["nome"] for d in client.get("/api/disciplinas").json()] == ["Minha"]


def test_resposta_de_erro_tem_request_id_e_nao_armazena_cache(client):
    resposta = client.get("/api/auth/eu", headers={"X-Request-ID": "teste-req-123"})
    assert resposta.status_code == 401
    assert resposta.json()["request_id"] == "teste-req-123"
    assert resposta.headers["X-Request-ID"] == "teste-req-123"
    assert resposta.headers["Cache-Control"] == "no-store"
