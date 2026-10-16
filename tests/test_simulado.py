"""Simulado corrigido no servidor: o gabarito nunca vai ao navegador antes das respostas."""
import pytest

from apoio import criar_disciplina, criar_documento, criar_usuario, entrar, matricular


@pytest.fixture
def cenario(client, gemini_falso):
    from backend.aplicacao.estudo_service import Questao

    prof = criar_usuario("prof@example.test", "professor")
    aluna = criar_usuario("aluna@example.test")
    colega = criar_usuario("colega@example.test")
    disciplina = criar_disciplina("Algoritmos", prof)
    matricular(aluna, disciplina)
    matricular(colega, disciplina)
    criar_documento(disciplina, "Aula 1.pdf", prof, ["Um algoritmo é uma sequência finita de passos."])
    gemini_falso.parsed = [
        Questao(pergunta="O que é algoritmo?", alternativas=["a", "b", "c", "d"], correta=2, explicacao="Porque sim.", pagina=1),
        Questao(pergunta="Laço que testa no fim?", alternativas=["a", "b", "c", "d"], correta=0, explicacao="Repita-até.", pagina=1),
        Questao(pergunta="Questão malformada", alternativas=["a", "b"], correta=0, explicacao="x", pagina=1),
    ]
    entrar(client, "aluna@example.test")
    return {"disciplina": disciplina}


def _gerar(client, disciplina):
    resposta = client.post(f"/api/disciplinas/{disciplina}/simulado", json={"arquivo": "Aula 1.pdf", "quantidade": 3})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_geracao_nao_entrega_o_gabarito(client, cenario):
    simulado = _gerar(client, cenario["disciplina"])
    assert simulado["simulado_id"]
    assert len(simulado["questoes"]) == 2  # a malformada foi descartada
    for questao in simulado["questoes"]:
        assert set(questao) == {"pergunta", "alternativas"}
    assert "correta" not in str(simulado) and "explicacao" not in str(simulado)


def test_servidor_corrige_e_guarda_a_nota(client, database, cenario):
    simulado = _gerar(client, cenario["disciplina"])
    rota = f"/api/disciplinas/{cenario['disciplina']}/simulados/{simulado['simulado_id']}/respostas"
    resultado = client.post(rota, json={"respostas": [2, None]}).json()
    assert (resultado["acertos"], resultado["total"]) == (1, 2)
    assert [c["acertou"] for c in resultado["correcao"]] == [True, False]
    assert resultado["correcao"][1]["correta"] == 0
    assert database.consultar("SELECT acertos, total FROM resultados_simulado") == [{"acertos": 1, "total": 2}]

    segunda = client.post(rota, json={"respostas": [2, 0]})
    assert segunda.status_code == 409
    assert database.consultar("SELECT COUNT(*) AS n FROM resultados_simulado")[0]["n"] == 1


def test_simulado_de_outra_pessoa_nao_aparece(client, cenario):
    simulado = _gerar(client, cenario["disciplina"])
    entrar(client, "colega@example.test")
    rota = f"/api/disciplinas/{cenario['disciplina']}/simulados/{simulado['simulado_id']}/respostas"
    assert client.post(rota, json={"respostas": [2, 0]}).status_code == 404


def test_quantidade_de_respostas_precisa_bater(client, cenario):
    simulado = _gerar(client, cenario["disciplina"])
    rota = f"/api/disciplinas/{cenario['disciplina']}/simulados/{simulado['simulado_id']}/respostas"
    assert client.post(rota, json={"respostas": [2]}).status_code == 400


def test_rota_antiga_que_aceitava_a_nota_do_navegador_nao_existe_mais(client, cenario):
    rota = f"/api/disciplinas/{cenario['disciplina']}/simulado/resultado"
    resposta = client.post(rota, json={"arquivo": "Aula 1.pdf", "acertos": 10, "total": 10})
    assert resposta.status_code in (404, 405)


def test_arquivo_fora_da_disciplina_e_recusado(client, cenario):
    resposta = client.post(f"/api/disciplinas/{cenario['disciplina']}/simulado",
                           json={"arquivo": "nao-existe.pdf", "quantidade": 3})
    assert resposta.status_code == 404
