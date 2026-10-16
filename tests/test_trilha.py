"""Trilha até a prova, baralho com revisão espaçada (SM-2) e dados de universidades."""
import re
from datetime import date, timedelta

import pytest

from apoio import SENHA_PADRAO, criar_disciplina, criar_documento, criar_usuario, entrar, matricular
from backend.aplicacao import trilha_service

HOJE = date(2026, 10, 16)


def _aulas(n, concluidas=()):
    return [{"id": i, "arquivo": f"Aula {i:02d}.pdf", "concluida": i in concluidas} for i in range(1, n + 1)]


def _aulas_por_semana(plano):
    return [[t["documento_id"] for t in s["tarefas"] if t["tipo"] == "aula"] for s in plano["semanas"]]


def test_plano_distribui_aulas_e_reserva_a_ultima_semana():
    plano = trilha_service.montar_plano(_aulas(6), HOJE, HOJE + timedelta(days=27), horas_semana=5)
    assert len(plano["semanas"]) == 4 and plano["dias_restantes"] == 27
    assert _aulas_por_semana(plano) == [[1, 2], [3, 4], [5, 6], []]
    assert plano["semanas"][-1]["revisao_final"]
    assert plano["semanas"][0]["inicio"] == "2026-10-16" and plano["semanas"][-1]["fim"] == "2026-11-12"


def test_plano_ignora_aulas_ja_estudadas():
    plano = trilha_service.montar_plano(_aulas(4, concluidas={1, 3}), HOJE, HOJE + timedelta(days=13), 4)
    assert _aulas_por_semana(plano) == [[2, 4], []]
    assert plano["aulas_pendentes"] == 2 and plano["aulas_total"] == 4


def test_prova_em_poucos_dias_vira_uma_semana_so():
    plano = trilha_service.montar_plano(_aulas(3), HOJE, HOJE + timedelta(days=3), 2)
    assert _aulas_por_semana(plano) == [[1, 2, 3]]
    assert not plano["semanas"][0]["revisao_final"]


def test_mais_semanas_que_aulas_deixa_semanas_de_revisao():
    plano = trilha_service.montar_plano(_aulas(1), HOJE, HOJE + timedelta(days=30), 3)
    semanas = _aulas_por_semana(plano)
    assert sum(len(s) for s in semanas) == 1 and len(semanas) == 5
    assert any(t["tipo"] == "cartoes" for t in plano["semanas"][1]["tarefas"])


def test_sm2_intervalos_crescem_e_erro_recomeca():
    f, i, r = 2.5, 0, 0
    intervalos = []
    for _ in range(4):
        f, i, r = trilha_service.sm2(f, i, r, nota=4)
        intervalos.append(i)
    assert intervalos[:2] == [1, 6] and intervalos[2] == 15 and intervalos[3] > intervalos[2]
    f2, i2, r2 = trilha_service.sm2(f, i, r, nota=1)
    assert (i2, r2) == (1, 0) and f2 < f
    assert trilha_service.sm2(1.3, 1, 0, nota=0)[0] == 1.3  # facilidade nunca fica abaixo de 1,3


@pytest.fixture
def turma(client):
    prof = criar_usuario("prof@example.test", "professor")
    aluno = criar_usuario("aluno@example.test")
    disciplina = criar_disciplina("Algoritmos", prof)
    matricular(aluno, disciplina)
    for n in (1, 2, 3):
        criar_documento(disciplina, f"Aula {n}.pdf", prof, [f"Conteúdo {n}"])
    entrar(client, "aluno@example.test")
    return {"disciplina": disciplina, "prof": prof, "aluno": aluno}


def test_salvar_e_ver_a_trilha(client, database, turma):
    rota = f"/api/disciplinas/{turma['disciplina']}/trilha"
    assert client.get(rota).json()["trilha"] is None
    alvo = (date.today() + timedelta(days=20)).isoformat()
    database.executar("INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, publico) VALUES (?, ?, ?, ?, 1)",
                      (turma["disciplina"], turma["prof"], "Prova 1", alvo))

    dados = client.put(rota, json={"objetivo": "prova", "data_alvo": alvo, "horas_semana": 6}).json()
    assert dados["trilha"]["objetivo"] == "prova"
    assert dados["plano"]["aulas_total"] == 3 and len(dados["plano"]["semanas"]) == 3
    assert dados["datas_da_turma"] == [{"titulo": "Prova 1", "data": alvo}]

    assert client.delete(rota).status_code == 200
    assert client.get(rota).json()["trilha"] is None


def test_data_alvo_no_passado_ou_longe_demais_e_recusada(client, turma):
    rota = f"/api/disciplinas/{turma['disciplina']}/trilha"
    ontem = (date.today() - timedelta(days=1)).isoformat()
    longe = (date.today() + timedelta(days=800)).isoformat()
    for data_alvo in (ontem, longe):
        assert client.put(rota, json={"objetivo": "enade", "data_alvo": data_alvo, "horas_semana": 5}).status_code == 400
    assert client.put(rota, json={"objetivo": "vestibular", "data_alvo": longe, "horas_semana": 5}).status_code == 422
    assert client.put(rota, json={"objetivo": "enade", "data_alvo": ontem, "horas_semana": 0}).status_code == 422


def test_trilha_e_de_cada_pessoa(client, turma):
    rota = f"/api/disciplinas/{turma['disciplina']}/trilha"
    alvo = (date.today() + timedelta(days=10)).isoformat()
    client.put(rota, json={"objetivo": "prova", "data_alvo": alvo, "horas_semana": 4})
    entrar(client, "prof@example.test")
    assert client.get(rota).json()["trilha"] is None


def _salvar(client, turma, cartoes):
    return client.post(f"/api/disciplinas/{turma['disciplina']}/baralho",
                       json={"arquivo": "Aula 1.pdf", "cartoes": cartoes})


def test_baralho_salva_sem_repetir_e_revisa(client, database, turma):
    cartoes = [{"frente": "O que é um algoritmo?", "verso": "Sequência finita de passos.", "pagina": 1},
               {"frente": "O que é uma variável?", "verso": "Espaço nomeado na memória.", "pagina": 2}]
    assert _salvar(client, turma, cartoes).json()["salvos"] == 2
    repetido = _salvar(client, turma, cartoes[:1]).json()
    assert repetido["salvos"] == 0 and repetido["repetidos"] == 1 and repetido["total"] == 2

    hoje = client.get(f"/api/disciplinas/{turma['disciplina']}/baralho/hoje").json()
    assert hoje["para_hoje"] == 2 and len(hoje["cartoes"]) == 2
    cartao = hoje["cartoes"][0]["id"]
    revisao = client.post(f"/api/baralho/{cartao}/revisao", json={"nota": 5}).json()
    assert revisao["intervalo_dias"] == 1 and revisao["proxima_revisao"] > date.today().isoformat()
    assert client.get(f"/api/disciplinas/{turma['disciplina']}/baralho/hoje").json()["para_hoje"] == 1


def test_cartao_de_outra_pessoa_nao_e_revisado_nem_apagado(client, turma):
    _salvar(client, turma, [{"frente": "F", "verso": "V"}])
    cartao = client.get(f"/api/disciplinas/{turma['disciplina']}/baralho/hoje").json()["cartoes"][0]["id"]
    entrar(client, "prof@example.test")
    assert client.post(f"/api/baralho/{cartao}/revisao", json={"nota": 5}).status_code == 404
    assert client.delete(f"/api/baralho/{cartao}").status_code == 404


def test_baralho_limita_tamanho_dos_campos(client, turma):
    assert _salvar(client, turma, [{"frente": "x" * 301, "verso": "v"}]).status_code == 422
    assert _salvar(client, turma, [{"frente": "f", "verso": "v"}] * 51).status_code == 422


def test_trilha_e_baralho_entram_na_exportacao_e_saem_na_exclusao(client, database, turma):
    alvo = (date.today() + timedelta(days=10)).isoformat()
    client.put(f"/api/disciplinas/{turma['disciplina']}/trilha",
               json={"objetivo": "transferencia", "data_alvo": alvo, "horas_semana": 3})
    _salvar(client, turma, [{"frente": "F", "verso": "V"}])
    dados = client.get("/api/conta/meus-dados").json()
    assert dados["trilhas_de_estudo"][0]["objetivo"] == "transferencia"
    assert dados["baralho_de_flashcards"][0]["frente"] == "F"

    resposta = client.request("DELETE", "/api/conta", json={"senha": SENHA_PADRAO, "confirmacao": "EXCLUIR"})
    assert resposta.status_code == 200, resposta.text
    assert database.consultar("SELECT * FROM trilhas") == []
    assert database.consultar("SELECT * FROM flashcards") == []


def test_toda_tabela_com_dado_de_usuario_entra_na_exportacao(database):
    """Estrutural: tabela nova que referencia usuarios precisa aparecer em meus-dados."""
    from backend.aplicacao import conta_service

    sql_exportado = " ".join(sql for sql, _ in conta_service._consultas_de_exportacao(1).values())
    fora_de_proposito = {"tokens_conta"}  # segredos de segurança (hash de token de link)
    with database.conectar() as conexao:
        tabelas = [l["name"] for l in conexao.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        com_usuario = {t for t in tabelas
                       if any(fk["table"] == "usuarios" for fk in conexao.execute(f"PRAGMA foreign_key_list({t})"))}
    faltando = {t for t in com_usuario - fora_de_proposito if not re.search(rf"\b{t}\b", sql_exportado)}
    assert not faltando, f"tabelas com dados de usuário fora da exportação: {faltando}"


def test_universidades_vem_do_servidor_com_fontes(client):
    criar_usuario("x@example.test")
    entrar(client, "x@example.test")
    dados = client.get("/api/universidades").json()
    assert len(dados["universidades"]) == 10 and dados["fontes"]
    assert all({"sigla", "inscricoes", "site"} <= set(u) for u in dados["universidades"])
