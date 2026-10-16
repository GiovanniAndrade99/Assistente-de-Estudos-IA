"""Resposta do chat em streaming (SSE) e citação que abre o PDF na página."""
import io
import json
from types import SimpleNamespace

import pymupdf
import pytest
from google.genai.errors import APIError

from apoio import criar_disciplina, criar_usuario, entrar, matricular


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
    resposta = client.post(f"/api/disciplinas/{disciplina}/documentos", files={
        "arquivo": ("Aula 1.pdf", io.BytesIO(_pdf("Um algoritmo é uma sequência finita de passos.")),
                    "application/pdf")})
    assert resposta.status_code == 202
    entrar(client, "aluno@example.test")
    return {"disciplina": disciplina, "aluno": aluno}


def _eventos(resposta) -> list[tuple[str, object]]:
    eventos = []
    for bloco in resposta.text.strip().split("\n\n"):
        linhas = dict(linha.split(": ", 1) for linha in bloco.splitlines())
        eventos.append((linhas["event"], json.loads(linhas["data"])))
    return eventos


def test_stream_envia_fontes_texto_e_fim(client, database, turma, gemini_falso):
    with client.stream("POST", f"/api/disciplinas/{turma['disciplina']}/chat/stream",
                       json={"pergunta": "O que é um algoritmo?"}) as resposta:
        assert resposta.status_code == 200
        assert resposta.headers["content-type"].startswith("text/event-stream")
        assert resposta.headers["cache-control"] == "no-store"
        resposta.read()
    eventos = _eventos(resposta)

    nomes = [nome for nome, _ in eventos]
    assert nomes[0] == "fontes" and nomes[-1] == "fim"
    assert nomes.count("texto") > 1  # chegou em pedaços
    fontes = eventos[0][1]
    documento_id = database.consultar_um("SELECT id FROM documentos")["id"]
    assert fontes[0]["arquivo"] == "Aula 1.pdf" and fontes[0]["documento_id"] == documento_id
    texto = "".join(dados for nome, dados in eventos if nome == "texto")
    assert texto == gemini_falso.texto == eventos[-1][1]["resposta"]

    guardada = database.consultar("SELECT usuario_id, pergunta, resposta FROM perguntas")
    assert [(p["usuario_id"], p["pergunta"], p["resposta"]) for p in guardada] == [
        (turma["aluno"], "O que é um algoritmo?", gemini_falso.texto)]


def test_falha_da_ia_vira_evento_de_erro_e_nada_e_guardado(client, database, turma, monkeypatch):
    from backend.infraestrutura import rag

    def quebra_no_meio(contents, configuracao):
        def pedacos():
            yield "Começo da "
            raise RuntimeError("conexão caiu")
        return pedacos(), "modelo-de-teste"

    monkeypatch.setattr(rag, "gerar_conteudo_stream", quebra_no_meio)
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat/stream", json={"pergunta": "Algoritmo?"})
    eventos = _eventos(resposta)
    assert eventos[-1][0] == "erro"
    assert "conexão caiu" not in resposta.text  # detalhe interno não vai para a tela
    assert database.consultar("SELECT id FROM perguntas") == []


def test_stream_negado_para_quem_nao_participa(client, turma):
    criar_usuario("outro@example.test")
    entrar(client, "outro@example.test")
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat/stream", json={"pergunta": "Algoritmo?"})
    assert resposta.status_code == 403


def test_pergunta_vazia_e_recusada_antes_do_stream(client, turma):
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat/stream", json={"pergunta": "   "})
    assert resposta.status_code == 400


def test_chat_normal_tambem_leva_o_documento_das_fontes(client, database, turma):
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat", json={"pergunta": "Algoritmo?"})
    documento_id = database.consultar_um("SELECT id FROM documentos")["id"]
    assert resposta.json()["fontes"][0]["documento_id"] == documento_id


def test_pdf_da_citacao_abre_para_participante(client, database, turma):
    documento_id = database.consultar_um("SELECT id FROM documentos")["id"]
    resposta = client.get(f"/api/disciplinas/{turma['disciplina']}/documentos/{documento_id}/arquivo")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/pdf"
    assert resposta.headers["content-disposition"].startswith("inline")
    assert resposta.content.startswith(b"%PDF")


def test_pdf_da_citacao_negado_para_quem_nao_participa(client, database, turma):
    documento_id = database.consultar_um("SELECT id FROM documentos")["id"]
    criar_usuario("outro@example.test")
    entrar(client, "outro@example.test")
    assert client.get(f"/api/disciplinas/{turma['disciplina']}/documentos/{documento_id}/arquivo").status_code == 403


def test_pdf_de_outra_disciplina_nao_abre_pelo_id(client, database, turma):
    """O id do documento só vale dentro da disciplina dele."""
    documento_id = database.consultar_um("SELECT id FROM documentos")["id"]
    outra = criar_disciplina("Outra", criar_usuario("prof2@example.test", "professor"))
    matricular(turma["aluno"], outra)
    assert client.get(f"/api/disciplinas/{outra}/documentos/{documento_id}/arquivo").status_code == 404


# ---------------------------------------------------------------- troca de modelo no streaming

class _ModelosFalsos:
    def __init__(self, comportamento):
        self.comportamento = comportamento
        self.tentados = []

    def generate_content_stream(self, model, contents, config):
        self.tentados.append(model)
        return self.comportamento(model)


def _parte(texto, tokens=None):
    uso = SimpleNamespace(prompt_token_count=tokens, candidates_token_count=5, thoughts_token_count=0) if tokens else None
    return SimpleNamespace(text=texto, usage_metadata=uso)


def test_stream_troca_de_modelo_antes_do_primeiro_pedaco(monkeypatch, database):
    from backend import config
    from backend.infraestrutura import rag

    def comportamento(modelo):
        if modelo == "principal":
            raise APIError(429, {"error": {"message": "sem cota"}})
        return iter([_parte("Olá, "), _parte("mundo", tokens=50)])

    modelos = _ModelosFalsos(comportamento)
    monkeypatch.setattr(config, "GEMINI_MODEL", "principal")
    monkeypatch.setattr(config, "GEMINI_MODELOS_RESERVA", ["reserva"])
    monkeypatch.setattr(rag, "_gemini", lambda: SimpleNamespace(models=modelos))

    pedacos, modelo = rag.gerar_conteudo_stream("pergunta", None)
    assert modelo == "reserva"
    assert "".join(pedacos) == "Olá, mundo"
    assert modelos.tentados == ["principal", "reserva"]
    totais = {l["evento"]: l["total"] for l in database.consultar("SELECT evento, total FROM metricas_diarias")}
    assert totais["chamadas_ia"] == 1 and totais["tokens_entrada"] == 50
