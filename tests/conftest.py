import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Monta a API com SQLite temporário; não importa backend.main nem toca data/app.db."""
    from backend.infraestrutura import db

    monkeypatch.setattr(db, "ARQUIVO_DB", tmp_path / "teste.sqlite3")
    db.criar_tabelas()

    from backend.api import auth_router, disciplinas_router, progresso_router, saude_router
    from backend.excecoes import registrar_handlers
    from backend.middlewares.observabilidade import ObservabilidadeMiddleware

    app = FastAPI(title="API de teste")
    app.add_middleware(ObservabilidadeMiddleware)
    registrar_handlers(app)
    for router in (saude_router.router, auth_router.router, disciplinas_router.router, progresso_router.router):
        app.include_router(router)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def database(tmp_path, monkeypatch):
    from backend.infraestrutura import db

    monkeypatch.setattr(db, "ARQUIVO_DB", tmp_path / "teste.sqlite3")
    db.criar_tabelas()
    return db
