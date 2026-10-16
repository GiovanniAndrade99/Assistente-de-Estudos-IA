"""Painel do professor v2: temas das dúvidas, o que reforçar e CSV de notas."""
import csv
import io
import json

import pytest

from apoio import criar_disciplina, criar_documento, criar_usuario, entrar, matricular
from backend.aplicacao import professor_service


def _p(texto, aluno):
    return {"pergunta": texto, "usuario_id": aluno}


def test_agrupa_duvidas_parecidas_e_protege_aluno_sozinho():
    perguntas = [
        _p("Qual a diferença entre o laço enquanto e o repita-até?", 1),
        _p("Quando o laço enquanto não executa nenhuma vez?", 2),
        _p("O laço repita-até sempre executa uma vez?", 3),
        _p("O que é recursão?", 1),
        _p("Recursão precisa de caso base?", 1),
        _p("Como declarar um ponteiro?", 4),
    ]
    temas = professor_service.agrupar_duvidas(perguntas)
    laco = next(t for t in temas if "laco" in t["tema"])
    assert laco["perguntas"] == 3 and laco["alunos"] == 3 and len(laco["exemplos"]) == 3
    recursao = next(t for t in temas if "recursao" in t["tema"])
    assert recursao["perguntas"] == 2 and recursao["alunos"] == 1
    assert recursao["exemplos"] == []  # um aluno só: o texto poderia identificá-lo
    assert temas[0] is laco  # temas com mais alunos primeiro
    assert professor_service.agrupar_duvidas(perguntas) == temas  # determinístico


def test_perguntas_so_com_palavras_vazias_nao_viram_tema():
    assert professor_service.agrupar_duvidas([_p("O que é isso?", 1), _p("Explique, por favor", 2)]) == []


@pytest.fixture
def turma(client, database, gemini_falso):
    prof = criar_usuario("prof@example.test", "professor")
    alunos = [criar_usuario(f"aluno{i}@example.test", nome=f"Aluno {i}") for i in (1, 2)]
    disciplina = criar_disciplina("Algoritmos", prof)
    for aluno in alunos:
        matricular(aluno, disciplina)
    for nome in ("Aula 1.pdf", "Aula 2.pdf"):
        criar_documento(disciplina, nome, prof, ["conteúdo"])
    return {"prof": prof, "alunos": alunos, "disciplina": disciplina}


def _resultado(database, turma, aluno, arquivo, acertos, total=10):
    database.executar(
        "INSERT INTO resultados_simulado (usuario_id, disciplina_id, arquivo, acertos, total) VALUES (?, ?, ?, ?, ?)",
        (aluno, turma["disciplina"], arquivo, acertos, total))


def test_o_que_reforcar_prioriza_erro_e_duvidas(client, database, turma):
    a1, a2 = turma["alunos"]
    _resultado(database, turma, a1, "Aula 1.pdf", 9)
    _resultado(database, turma, a2, "Aula 2.pdf", 3)
    for aluno in (a1, a2):
        database.executar(
            "INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta, fontes_arquivos) VALUES (?, ?, ?, ?, ?)",
            (aluno, turma["disciplina"], "dúvida", "resposta", json.dumps(["Aula 2.pdf"])))
    entrar(client, "prof@example.test")
    ranking = client.get(f"/api/professor/reforcar?disciplina_id={turma['disciplina']}").json()
    assert [r["arquivo"] for r in ranking] == ["Aula 2.pdf", "Aula 1.pdf"]
    assert ranking[0]["acerto"] == 30 and ranking[0]["duvidas"] == 2
    assert ranking[1]["acerto"] == 90 and ranking[1]["duvidas"] == 0


def test_pergunta_ao_assistente_guarda_os_pdfs_usados(client, database, gemini_falso):
    import io as _io

    import pymupdf

    prof = criar_usuario("p@example.test", "professor")
    disciplina = criar_disciplina("Outra", prof)
    entrar(client, "p@example.test")
    documento = pymupdf.open()
    documento.new_page().insert_text((50, 72), "Um algoritmo é uma sequência finita de passos.")
    client.post(f"/api/disciplinas/{disciplina}/documentos",
                files={"arquivo": ("Aula 9.pdf", _io.BytesIO(documento.tobytes()), "application/pdf")})
    client.post(f"/api/disciplinas/{disciplina}/chat", json={"pergunta": "O que é um algoritmo?"})
    assert json.loads(database.consultar_um("SELECT fontes_arquivos FROM perguntas")["fontes_arquivos"]) == ["Aula 9.pdf"]


def test_temas_pela_api(client, database, turma):
    a1, a2 = turma["alunos"]
    for aluno, texto in ((a1, "Como funciona o laço enquanto?"), (a2, "Laço enquanto pode não executar?")):
        database.executar("INSERT INTO perguntas (usuario_id, disciplina_id, pergunta, resposta) VALUES (?, ?, ?, ?)",
                          (aluno, turma["disciplina"], texto, "r"))
    entrar(client, "prof@example.test")
    dados = client.get(f"/api/professor/temas?disciplina_id={turma['disciplina']}").json()
    assert dados["total_perguntas"] == 2
    assert dados["temas"][0]["alunos"] == 2
    assert "Aluno" not in json.dumps(dados)  # nenhum nome de aluno nos temas


def test_csv_de_notas_abre_no_excel_e_nao_executa_formula(client, database, turma):
    database.executar("UPDATE usuarios SET nome = ? WHERE id = ?", ("=HYPERLINK(\"http://x\")", turma["alunos"][0]))
    _resultado(database, turma, turma["alunos"][0], "Aula 1.pdf", 7)
    _resultado(database, turma, turma["alunos"][1], "+Aula 2.pdf", 5)
    entrar(client, "prof@example.test")
    resposta = client.get(f"/api/professor/notas.csv?disciplina_id={turma['disciplina']}")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/csv")
    assert resposta.headers["content-disposition"].startswith("attachment")
    assert resposta.content.startswith("﻿".encode("utf-8"))
    linhas = list(csv.reader(io.StringIO(resposta.text.lstrip("﻿")), delimiter=";"))
    assert linhas[0][:3] == ["Aluno", "Material", "Acertos"]
    celulas = [c for linha in linhas[1:] for c in linha]
    assert "'=HYPERLINK(\"http://x\")" in celulas and "'+Aula 2.pdf" in celulas
    assert "70%" in celulas


def test_painel_so_para_o_professor_da_disciplina(client, turma):
    criar_usuario("outro@example.test", "professor")
    for email in ("outro@example.test", "aluno1@example.test"):
        entrar(client, email)
        for rota in ("temas", "reforcar", "notas.csv"):
            assert client.get(f"/api/professor/{rota}?disciplina_id={turma['disciplina']}").status_code == 403
