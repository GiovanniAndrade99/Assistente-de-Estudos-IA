from fastapi.testclient import TestClient


def test_documentacao_da_api_so_fora_de_producao(monkeypatch):
    from backend import config
    from backend.main import criar_app

    with TestClient(criar_app(iniciar_tarefas=False)) as cliente:
        assert cliente.get("/openapi.json").status_code == 200

    monkeypatch.setattr(config, "APP_ENV", "production")
    with TestClient(criar_app(iniciar_tarefas=False)) as cliente:
        assert cliente.get("/docs").status_code == 404
        assert cliente.get("/openapi.json").status_code == 404


def test_app_completa_responde_saude_e_frontend(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 200
