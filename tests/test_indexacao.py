"""Indexação em segundo plano, OCR de PDF escaneado e índice vetorial seguro."""
import io
import json

import numpy as np
import pymupdf
import pytest

from apoio import criar_disciplina, criar_pdf, criar_usuario, entrar


def _pdf_em_bytes(paginas: list[str]) -> bytes:
    documento = pymupdf.open()
    for texto in paginas:
        documento.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=12)
    dados = documento.tobytes()
    documento.close()
    return dados


@pytest.fixture
def professor(client, gemini_falso):
    prof = criar_usuario("prof@example.test", "professor")
    disciplina = criar_disciplina("Algoritmos", prof)
    entrar(client, "prof@example.test")
    return {"id": prof, "disciplina": disciplina}


def _enviar(client, disciplina, nome="Aula 1.pdf", conteudo=None):
    conteudo = conteudo or _pdf_em_bytes(["Um algoritmo é uma sequência finita de passos bem definidos."])
    return client.post(f"/api/disciplinas/{disciplina}/documentos",
                       files={"arquivo": (nome, io.BytesIO(conteudo), "application/pdf")})


def test_envio_responde_na_hora_e_termina_pronto(client, database, professor):
    resposta = _enviar(client, professor["disciplina"])
    assert resposta.status_code == 202
    assert resposta.json()["status"] == "processando"

    documentos = client.get(f"/api/disciplinas/{professor['disciplina']}/documentos").json()
    assert [(d["status"], d["progresso"]) for d in documentos] == [("pronto", 100)]
    assert documentos[0]["trechos"] >= 1
    paginas = database.consultar("SELECT pagina, texto FROM paginas_documento")
    assert paginas and "algoritmo" in paginas[0]["texto"]

    from backend.infraestrutura import rag
    assert rag.banco().tem_trechos(professor["disciplina"], "Aula 1.pdf")


def test_arquivo_que_nao_e_pdf_e_recusado(client, professor):
    resposta = _enviar(client, professor["disciplina"], conteudo=b"isto nao e um pdf")
    assert resposta.status_code == 400


def test_reenvio_durante_o_processamento_e_recusado(client, database, professor):
    _enviar(client, professor["disciplina"])
    database.executar("UPDATE documentos SET status = 'processando'")
    assert _enviar(client, professor["disciplina"]).status_code == 409


def test_falha_ao_reindexar_mantem_os_trechos_antigos(client, database, professor, monkeypatch):
    from backend.infraestrutura import rag

    _enviar(client, professor["disciplina"])

    def quebrar(textos, tipo):
        raise RuntimeError("cota esgotada")

    monkeypatch.setattr(rag, "gerar_embeddings", quebrar)
    _enviar(client, professor["disciplina"], conteudo=_pdf_em_bytes(["Versão nova do material de algoritmos."]))

    documento = database.consultar_um("SELECT status, erro FROM documentos")
    assert documento["status"] == "erro"
    assert "cota" not in documento["erro"]  # mensagem genérica, sem detalhe interno
    assert rag.banco().tem_trechos(professor["disciplina"], "Aula 1.pdf")


def test_documento_removido_durante_a_indexacao_nao_volta_ao_indice(client, database, professor):
    from backend.aplicacao import indexacao_service
    from backend.infraestrutura import rag

    _enviar(client, professor["disciplina"])
    documento_id = database.consultar_um("SELECT id FROM documentos")["id"]
    client.delete(f"/api/disciplinas/{professor['disciplina']}/documentos/Aula 1.pdf")
    indexacao_service.indexar_documento(documento_id)  # trabalho atrasado na fila
    assert not rag.banco().tem_trechos(professor["disciplina"], "Aula 1.pdf")


def test_resumo_espera_o_documento_ficar_pronto(client, database, professor):
    _enviar(client, professor["disciplina"])
    database.executar("UPDATE documentos SET status = 'processando'")
    resposta = client.post(f"/api/disciplinas/{professor['disciplina']}/resumo", json={"arquivo": "Aula 1.pdf"})
    assert resposta.status_code == 409


def test_subida_refaz_documentos_sem_trechos(client, database, professor):
    from backend.aplicacao import indexacao_service
    from backend.infraestrutura import rag

    _enviar(client, professor["disciplina"])
    rag.banco().remover(professor["disciplina"])  # como depois de restaurar um índice antigo
    assert indexacao_service.retomar_pendentes() == 1
    assert rag.banco().tem_trechos(professor["disciplina"], "Aula 1.pdf")


def test_pdf_de_texto_nao_passa_pelo_ocr(tmp_path, monkeypatch):
    from backend.infraestrutura import rag

    chamadas = []
    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", lambda *a, **k: chamadas.append(1))
    criar_pdf(tmp_path / "texto.pdf", ["Texto comum, selecionável, com bem mais de vinte caracteres."])
    assert rag.extrair_paginas(tmp_path / "texto.pdf")
    assert chamadas == []


def test_pdf_escaneado_e_lido_por_ocr(tmp_path, monkeypatch):
    from backend.infraestrutura import rag

    monkeypatch.setattr(rag, "_tessdata", False)
    if not rag.tessdata():
        pytest.skip("Tesseract não instalado")
    # Página só com imagem: renderiza um texto e cola a imagem num PDF novo
    origem = pymupdf.open()
    origem.new_page().insert_textbox(pymupdf.Rect(40, 40, 560, 300), "Algoritmo e sequencia finita de passos",
                                     fontsize=28)
    imagem = origem[0].get_pixmap(dpi=200)
    escaneado = pymupdf.open()
    escaneado.new_page().insert_image(escaneado[0].rect, pixmap=imagem)
    escaneado.save(tmp_path / "escaneado.pdf")
    paginas = rag.extrair_paginas(tmp_path / "escaneado.pdf")
    assert paginas and "sequencia" in paginas[0][1].lower()


def test_indice_grava_arquivo_unico_e_le_formato_antigo(tmp_path):
    from backend.infraestrutura.vetores import BancoVetorial

    antigo = tmp_path / "indice"
    antigo.mkdir()
    np.save(antigo / "vetores.npy", np.array([[1.0, 0.0]], dtype=np.float32))
    (antigo / "trechos.json").write_text(json.dumps([{"texto": "a", "arquivo": "x.pdf", "pagina": 1,
                                                      "disciplina_id": 1}]), encoding="utf-8")
    banco = BancoVetorial(antigo)
    assert len(banco) == 1
    banco.substituir(1, "y.pdf", [[0.0, 1.0]], [{"texto": "b", "arquivo": "y.pdf", "pagina": 1, "disciplina_id": 1}])
    assert (antigo / "indice.npz").exists() and not (antigo / "vetores.npy").exists()
    recarregado = BancoVetorial(antigo)
    assert len(recarregado) == 2
    assert recarregado.buscar([0.0, 1.0], 1, 1)[0]["arquivo"] == "y.pdf"
