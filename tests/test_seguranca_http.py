"""Cabeçalhos de segurança, checagem de origem e respostas de erro."""
import re
from pathlib import Path

from apoio import criar_usuario

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def test_csp_so_nas_paginas_html(client):
    pagina = client.get("/")
    csp = pagina.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "frame-ancestors 'none'" in csp
    assert "camera=()" in pagina.headers["Permissions-Policy"]

    api = client.get("/api/health")
    assert "Content-Security-Policy" not in api.headers
    assert api.headers["Cache-Control"] == "no-store"


def test_documentacao_fora_de_producao_nao_recebe_csp(client):
    assert "Content-Security-Policy" not in client.get("/docs").headers


def test_requisicao_de_outro_site_e_recusada(client):
    criar_usuario("aluna@example.test")
    corpo = {"email": "aluna@example.test", "senha": "senha-segura-123"}

    de_fora = client.post("/api/auth/login", json=corpo, headers={"Origin": "https://evil.example"})
    assert de_fora.status_code == 403
    assert de_fora.json()["request_id"]

    cross_site = client.post("/api/auth/login", json=corpo, headers={"Sec-Fetch-Site": "cross-site"})
    assert cross_site.status_code == 403

    mesma_origem = client.post("/api/auth/login", json=corpo, headers={"Origin": "http://testserver"})
    assert mesma_origem.status_code == 200


def test_origem_extra_configurada_e_aceita(client, monkeypatch):
    from backend import config

    monkeypatch.setattr(config, "ORIGENS_PERMITIDAS", ["https://app.example"])
    resposta = client.post("/api/auth/logout", headers={"Origin": "https://app.example"})
    assert resposta.status_code == 200


def test_erro_de_validacao_nao_devolve_o_valor_enviado(client):
    resposta = client.post("/api/auth/cadastro", json={
        "nome": "Teste", "email": "teste@example.test", "senha": "Curta#123", "tipo": "aluno",
    })
    assert resposta.status_code == 422
    assert "Curta#123" not in resposta.text
    corpo = resposta.json()
    assert corpo["request_id"]
    assert "senha" in corpo["detail"]
    assert {"campo": "senha", "mensagem": "muito curto (mínimo de 10 caracteres)"} in corpo["erros"]


def test_rota_inexistente_tem_request_id_em_portugues(client):
    resposta = client.get("/api/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Não encontrado."
    assert resposta.json()["request_id"]


def test_erro_interno_tem_cabecalhos_de_seguranca(client, monkeypatch):
    from backend.aplicacao import disciplinas_service

    def quebrar():
        raise KeyError("detalhe interno")

    monkeypatch.setattr(disciplinas_service, "listar_disciplinas_publico", quebrar)
    from fastapi.testclient import TestClient
    from backend.main import criar_app

    with TestClient(criar_app(iniciar_tarefas=False), raise_server_exceptions=False) as cliente:
        resposta = cliente.get("/api/disciplinas/publico")
    assert resposta.status_code == 500
    assert "detalhe interno" not in resposta.text
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["Cache-Control"] == "no-store"


def test_value_error_inesperado_nao_vaza_mensagem(client, monkeypatch):
    from backend.aplicacao import disciplinas_service

    def quebrar():
        raise ValueError(r"C:\servidor\caminho\secreto.pdf")

    monkeypatch.setattr(disciplinas_service, "listar_disciplinas_publico", quebrar)
    resposta = client.get("/api/disciplinas/publico")
    assert resposta.status_code == 400
    assert "secreto" not in resposta.text


def test_limite_de_login_informa_quando_tentar_de_novo(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "x@example.test", "senha": "senha-errada-123"})
    bloqueada = client.post("/api/auth/login", json={"email": "x@example.test", "senha": "senha-errada-123"})
    assert bloqueada.status_code == 429
    assert int(bloqueada.headers["Retry-After"]) > 0


def test_frontend_sem_script_inline_estilo_inline_ou_recurso_de_terceiros():
    """Regressão da CSP: nada de <script> sem src, style="...", on*= nem fontes/CDNs externos."""
    problemas = []
    for arquivo in sorted(FRONTEND.rglob("*")):
        if arquivo.suffix not in (".html", ".js", ".css"):
            continue
        texto = arquivo.read_text(encoding="utf-8")
        nome = arquivo.relative_to(FRONTEND)
        if arquivo.suffix == ".html" and re.search(r"<script(?![^>]*\bsrc=)[^>]*>", texto):
            problemas.append(f"{nome}: <script> inline")
        if re.search(r"""\sstyle=["']""", texto):
            problemas.append(f"{nome}: atributo style=")
        if re.search(r"""\son[a-z]+=["']""", texto):
            problemas.append(f"{nome}: atributo de evento on*=")
        for externo in ("fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net", "unpkg.com"):
            if externo in texto:
                problemas.append(f"{nome}: carrega {externo}")
    assert problemas == []
