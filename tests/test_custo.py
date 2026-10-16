"""Controle de custo da IA: cache de respostas, cota diária e teto do sistema."""
import io
import logging
from types import SimpleNamespace

import pymupdf
import pytest

from apoio import criar_disciplina, criar_documento, criar_usuario, entrar, matricular


def _pdf(texto: str) -> bytes:
    documento = pymupdf.open()
    documento.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=12)
    dados = documento.tobytes()
    documento.close()
    return dados


@pytest.fixture
def turma(client, gemini_falso):
    prof = criar_usuario("prof@example.test", "professor")
    aluno = criar_usuario("aluno@example.test")
    disciplina = criar_disciplina("Algoritmos", prof)
    matricular(aluno, disciplina)
    entrar(client, "prof@example.test")
    _enviar(client, disciplina, "Aula 1.pdf", "Um algoritmo é uma sequência finita de passos.")
    entrar(client, "aluno@example.test")
    return {"disciplina": disciplina, "prof": prof, "aluno": aluno}


def _enviar(client, disciplina, nome, texto):
    resposta = client.post(f"/api/disciplinas/{disciplina}/documentos",
                           files={"arquivo": (nome, io.BytesIO(_pdf(texto)), "application/pdf")})
    assert resposta.status_code == 202, resposta.text


def _perguntar(client, turma, pergunta):
    return client.post(f"/api/disciplinas/{turma['disciplina']}/chat", json={"pergunta": pergunta})


def test_pergunta_repetida_volta_do_cache_sem_chamar_o_gemini(client, database, turma, gemini_falso):
    primeira = _perguntar(client, turma, "O que é um algoritmo?").json()
    segunda = _perguntar(client, turma, "  o que É um   algoritmo  ").json()

    assert len(gemini_falso.chamadas_geracao) == 1
    assert segunda["cache"] is True and "cache" not in primeira
    assert segunda["resposta"] == primeira["resposta"]
    assert segunda["fontes"][0]["documento_id"] == primeira["fontes"][0]["documento_id"]
    # o histórico do professor registra as duas perguntas
    assert database.consultar_um("SELECT COUNT(*) AS n FROM perguntas")["n"] == 2
    assert database.consultar_um(
        "SELECT total FROM metricas_diarias WHERE evento = 'respostas_do_cache'")["total"] == 1


def test_cache_nao_guarda_quem_perguntou_nem_a_pergunta(client, database, turma):
    _perguntar(client, turma, "Pergunta com um nome próprio: Joana Exemplo")
    colunas = {c["name"] for c in database.consultar("PRAGMA table_info(cache_respostas)")}
    assert colunas == {"chave", "disciplina_id", "dados_json", "criado_em"}
    linhas = database.consultar("SELECT chave, dados_json FROM cache_respostas")
    assert linhas and all("Joana" not in l["dados_json"] and "Joana" not in l["chave"] for l in linhas)


def test_stream_tambem_usa_o_cache(client, database, turma, gemini_falso):
    _perguntar(client, turma, "O que é um algoritmo?")
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat/stream",
                           json={"pergunta": "O que é um algoritmo?"})
    assert resposta.status_code == 200
    assert '"cache": true' in resposta.text
    assert len(gemini_falso.chamadas_geracao) == 1
    assert database.consultar_um("SELECT COUNT(*) AS n FROM perguntas")["n"] == 2


def test_pdf_novo_ou_removido_invalida_o_cache(client, turma, gemini_falso):
    _perguntar(client, turma, "O que é um algoritmo?")
    entrar(client, "prof@example.test")
    _enviar(client, turma["disciplina"], "Aula 2.pdf", "Laços repetem um bloco de código.")
    entrar(client, "aluno@example.test")
    assert "cache" not in _perguntar(client, turma, "O que é um algoritmo?").json()
    assert len(gemini_falso.chamadas_geracao) == 2

    entrar(client, "prof@example.test")
    client.delete(f"/api/disciplinas/{turma['disciplina']}/documentos/Aula 2.pdf")
    entrar(client, "aluno@example.test")
    assert "cache" not in _perguntar(client, turma, "O que é um algoritmo?").json()
    assert len(gemini_falso.chamadas_geracao) == 3


def test_cota_diaria_do_aluno(client, turma, monkeypatch):
    from backend import config

    monkeypatch.setattr(config, "COTA_IA_DIA_ALUNO", 2)
    assert _perguntar(client, turma, "Pergunta 1").status_code == 200
    assert _perguntar(client, turma, "Pergunta 2").status_code == 200
    estourou = _perguntar(client, turma, "Pergunta 3")
    assert estourou.status_code == 429 and "limite de 2 pedidos" in estourou.json()["detail"]
    # resposta já guardada continua saindo, sem gastar cota
    assert _perguntar(client, turma, "Pergunta 1").status_code == 200
    # a cota é por pessoa
    entrar(client, "prof@example.test")
    assert _perguntar(client, turma, "Pergunta 3").status_code == 200


def test_cota_vale_para_o_stream_antes_de_abrir_a_resposta(client, turma, monkeypatch):
    from backend import config

    monkeypatch.setattr(config, "COTA_IA_DIA_ALUNO", 1)
    _perguntar(client, turma, "Pergunta 1")
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat/stream", json={"pergunta": "Outra"})
    assert resposta.status_code == 429


def test_teto_diario_de_tokens_pausa_a_ia(client, turma, monkeypatch):
    from backend import config
    from backend.infraestrutura import metricas

    monkeypatch.setattr(config, "TETO_TOKENS_DIA", 50)
    metricas.registrar("tokens_entrada", 60)
    resposta = _perguntar(client, turma, "O que é um algoritmo?")
    assert resposta.status_code == 503 and "limite diário" in resposta.json()["detail"]


def test_resumo_repetido_vem_do_cache(client, turma, gemini_falso):
    gemini_falso.texto = "## Visão geral\nResumo."
    corpo = {"arquivo": "Aula 1.pdf"}
    primeiro = client.post(f"/api/disciplinas/{turma['disciplina']}/resumo", json=corpo).json()
    segundo = client.post(f"/api/disciplinas/{turma['disciplina']}/resumo", json=corpo).json()
    assert len(gemini_falso.chamadas_geracao) == 1
    assert segundo["resumo"] == primeiro["resumo"] and segundo["cache"] is True


def test_retencao_apaga_cache_vencido(client, database, turma):
    from backend.aplicacao import retencao_service

    _perguntar(client, turma, "O que é um algoritmo?")
    database.executar("UPDATE cache_respostas SET criado_em = datetime('now', '-8 days')")
    assert retencao_service.executar_limpeza()["cache_de_respostas"] == 1


def test_alerta_de_tokens_no_log_uma_vez(database, monkeypatch, caplog):
    from backend import config
    from backend.infraestrutura import rag

    monkeypatch.setattr(config, "ALERTA_TOKENS_DIA", 150)
    uso = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=80, candidates_token_count=0,
                                                         thoughts_token_count=0))
    with caplog.at_level(logging.WARNING, logger="rag"):
        for _ in range(3):
            rag.registrar_uso(uso)
    assert [r.message for r in caplog.records].count("alerta_tokens_dia") == 1


def test_metricas_mostram_consumo_do_dia(client, database):
    criar_usuario("admin@example.test", "professor", administrador=True)
    entrar(client, "admin@example.test")
    dados = client.get("/api/admin/metricas").json()
    assert set(dados["ia_hoje"]) == {"tokens", "alerta", "teto", "cota_aluno", "cota_professor"}


def test_documento_antigo_sem_paginas_continua_resumindo(client, database, gemini_falso):
    """Resumo de PDF indexado antes de o texto ser guardado: chave do cache também funciona."""
    prof = criar_usuario("p2@example.test", "professor")
    disciplina = criar_disciplina("Outra", prof)
    criar_documento(disciplina, "antigo.pdf", prof, ["Texto antigo."])
    entrar(client, "p2@example.test")
    assert client.post(f"/api/disciplinas/{disciplina}/resumo", json={"arquivo": "antigo.pdf"}).status_code == 200
