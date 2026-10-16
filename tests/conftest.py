"""Fixtures compartilhadas.

Todo teste roda isolado: banco SQLite, uploads e índice vetorial ficam em
`tmp_path`, a configuração é previsível (não depende do .env local) e o Gemini
real nunca é chamado — quem precisa de IA usa a fixture `gemini_falso`.
"""
import os

# Antes de qualquer import do backend: o config.py não deve ler o .env real.
os.environ["CARREGAR_DOTENV"] = "0"
os.environ["GEMINI_API_KEY"] = ""

from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apoio import vetor_do_texto  # noqa: E402


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    from backend import config
    from backend.infraestrutura import db, rag
    from backend.infraestrutura.vetores import BancoVetorial

    # Toda pasta de dados aponta para tmp_path: nenhum teste toca em data/ do projeto
    dados = tmp_path / "data"
    (dados / "uploads").mkdir(parents=True)
    monkeypatch.setattr(config, "PASTA_DADOS", dados)
    monkeypatch.setattr(config, "PASTA_UPLOADS", dados / "uploads")
    monkeypatch.setattr(config, "PASTA_INDICE", dados / "indice")
    monkeypatch.setattr(config, "PASTA_BACKUPS", tmp_path / "backups")
    monkeypatch.setattr(db, "ARQUIVO_DB", dados / "app.db")
    monkeypatch.setattr(rag, "_banco", BancoVetorial(dados / "indice"))
    monkeypatch.setattr(rag, "_cliente_gemini", None)

    monkeypatch.setattr(config, "APP_ENV", "development")
    monkeypatch.setattr(config, "CODIGO_PROFESSOR", "codigo-teste")
    monkeypatch.setattr(config, "DADOS_DEMO", False)
    monkeypatch.setattr(config, "SEGREDO_APP", "segredo-de-teste")
    monkeypatch.setattr(config, "CONTROLADOR_NOME", "Escola de Teste")
    monkeypatch.setattr(config, "CONTROLADOR_CONTATO", "privacidade@escola.test")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    db.criar_tabelas()


@pytest.fixture
def client():
    """API completa (todos os routers e middlewares), sem tarefas de fundo."""
    from backend.main import criar_app

    with TestClient(criar_app(iniciar_tarefas=False)) as test_client:
        yield test_client


@pytest.fixture
def database():
    from backend.infraestrutura import db

    return db


class GeminiFalso:
    """Substitui as chamadas ao Gemini. Ajuste `texto` e `parsed` no teste."""

    def __init__(self):
        self.texto = "Resposta de teste baseada no material [1]."
        self.parsed = None
        self.chamadas_geracao = []
        self.chamadas_embedding = 0

    def resposta(self):
        return SimpleNamespace(
            text=self.texto,
            parsed=self.parsed,
            usage_metadata=SimpleNamespace(
                prompt_token_count=100, candidates_token_count=20, thoughts_token_count=0,
            ),
        )


@pytest.fixture
def gemini_falso(monkeypatch):
    from backend.infraestrutura import rag

    falso = GeminiFalso()

    def gerar_embeddings(textos, tipo):
        falso.chamadas_embedding += 1
        return [vetor_do_texto(t) for t in textos]

    def gerar_conteudo(contents, configuracao):
        falso.chamadas_geracao.append(contents)
        return falso.resposta(), "modelo-de-teste"

    monkeypatch.setattr(rag, "gerar_embeddings", gerar_embeddings)
    monkeypatch.setattr(rag, "gerar_conteudo", gerar_conteudo)
    return falso


@pytest.fixture
def caixa_de_email(monkeypatch):
    """SMTP "configurado", mas as mensagens ficam numa lista em vez de sair."""
    from backend import config
    from backend.infraestrutura import correio

    enviados = []
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.teste")
    monkeypatch.setattr(config, "SMTP_REMETENTE", "nao-responda@escola.test")
    monkeypatch.setattr(correio, "_enviar_smtp", enviados.append)
    return enviados
