"""Ciência do aviso de privacidade, declaração de idade mínima e dados públicos do aviso."""
import pytest
from fastapi.testclient import TestClient

from apoio import DECLARACOES, criar_usuario, entrar

CADASTRO = {"nome": "Aluna", "email": "aluna@example.test", "senha": "senha-segura-123", "tipo": "aluno"}


@pytest.mark.parametrize("faltando, trecho", [
    ("aceite_privacidade", "aviso de privacidade"),
    ("declara_maioridade", "18 anos"),
])
def test_cadastro_exige_as_duas_declaracoes(client, faltando, trecho):
    corpo = {**CADASTRO, **DECLARACOES, faltando: False}
    resposta = client.post("/api/auth/cadastro", json=corpo)
    assert resposta.status_code == 400
    assert trecho in resposta.json()["detail"]


def test_cadastro_registra_versao_e_datas(client, database):
    from backend import config

    resposta = client.post("/api/auth/cadastro", json={**CADASTRO, **DECLARACOES})
    assert resposta.status_code == 200
    assert resposta.json()["ciencia_pendente"] is False
    linha = database.consultar_um("SELECT * FROM usuarios WHERE email = ?", ("aluna@example.test",))
    assert linha["aceite_privacidade_versao"] == config.POLITICA_PRIVACIDADE_VERSAO
    assert linha["aceite_privacidade_em"] and linha["maioridade_declarada_em"]


def test_conta_antiga_fica_bloqueada_ate_confirmar(client):
    criar_usuario("antiga@example.test", ciente=False)
    entrar(client, "antiga@example.test")

    assert client.get("/api/auth/eu").json()["ciencia_pendente"] is True
    bloqueada = client.get("/api/disciplinas")
    assert bloqueada.status_code == 403
    assert bloqueada.headers["X-Acao-Necessaria"] == "ciencia-privacidade"
    assert client.get("/api/suporte/chamados").status_code == 200  # canal de contato continua aberto

    sem_idade = client.post("/api/conta/ciencia-privacidade", json={"aceite_privacidade": True})
    assert sem_idade.status_code == 400

    assert client.post("/api/conta/ciencia-privacidade", json=DECLARACOES).status_code == 200
    assert client.get("/api/auth/eu").json()["ciencia_pendente"] is False
    assert client.get("/api/disciplinas").status_code == 200


def test_nova_versao_do_aviso_pede_confirmacao_de_novo(client, monkeypatch):
    from backend import config

    criar_usuario("pessoa@example.test")
    entrar(client, "pessoa@example.test")
    assert client.get("/api/disciplinas").status_code == 200
    monkeypatch.setattr(config, "POLITICA_PRIVACIDADE_VERSAO", "2099-01-01")
    assert client.get("/api/disciplinas").status_code == 403


def test_ultimo_acesso_e_registrado(client, database):
    criar_usuario("acesso@example.test")
    entrar(client, "acesso@example.test")
    client.get("/api/auth/eu")
    linha = database.consultar_um("SELECT ultimo_acesso FROM usuarios WHERE email = ?", ("acesso@example.test",))
    assert linha["ultimo_acesso"]


def test_dados_do_aviso_sao_publicos(client):
    dados = client.get("/api/privacidade").json()
    assert dados["controlador"]["nome"] == "Escola de Teste"
    assert dados["idade_minima"] == 18
    assert dados["prazo_resposta_dias"] == 15
    assert dados["provedor_ia"]["plano_pago"] is False
    assert dados["retencao"]["historico_meses"] == 12


def test_producao_sem_controlador_nao_sobe(monkeypatch):
    from backend import config
    from backend.main import criar_app

    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "CONTROLADOR_NOME", "")
    with pytest.raises(RuntimeError, match="CONTROLADOR"):
        with TestClient(criar_app(iniciar_tarefas=False)):
            pass
