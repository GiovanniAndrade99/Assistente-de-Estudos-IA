"""Autorização por participação: só admin, professor dono e aluno matriculado
acessam os dados de uma disciplina."""
from datetime import date

import pytest
from fastapi.routing import APIRoute

from apoio import criar_disciplina, criar_usuario, entrar, matricular


@pytest.fixture
def turma(client):
    """Duas disciplinas de professores diferentes; uma aluna matriculada só na primeira."""
    from backend.infraestrutura import db

    ids = {
        "dono": criar_usuario("dono@example.test", "professor"),
        "outro_prof": criar_usuario("outro@example.test", "professor"),
        "aluna": criar_usuario("aluna@example.test"),
        "estranha": criar_usuario("estranha@example.test"),
        "admin": criar_usuario("admin@example.test", "professor", administrador=True),
    }
    ids["disciplina"] = criar_disciplina("Cálculo I", ids["dono"])
    ids["outra_disciplina"] = criar_disciplina("Física I", ids["outro_prof"])
    matricular(ids["aluna"], ids["disciplina"])
    db.executar("INSERT INTO mensagens_turma (disciplina_id, usuario_id, texto) VALUES (?, ?, ?)",
                (ids["disciplina"], ids["aluna"], "Mensagem só da turma"))
    ids["documento"] = db.executar(
        "INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por) VALUES (?, ?, ?, ?)",
        (ids["disciplina"], "Aula 1.pdf", 1, ids["dono"]),
    )
    return ids


EMAILS = {
    "dono": "dono@example.test", "outro_prof": "outro@example.test", "aluna": "aluna@example.test",
    "estranha": "estranha@example.test", "admin": "admin@example.test",
}
ROTAS_DE_LEITURA = ["/mensagens", "/eventos", "/atividades", "/videos", "/documentos", "/simulado/meus"]
ESPERADO = {"dono": 200, "aluna": 200, "admin": 200, "outro_prof": 403, "estranha": 403}


@pytest.mark.parametrize("pessoa", list(ESPERADO))
def test_leitura_da_turma_so_para_quem_participa(client, turma, pessoa):
    entrar(client, EMAILS[pessoa])
    for rota in ROTAS_DE_LEITURA:
        resposta = client.get(f"/api/disciplinas/{turma['disciplina']}{rota}")
        assert resposta.status_code == ESPERADO[pessoa], (pessoa, rota, resposta.text)


def test_disciplina_inexistente_responde_404(client, turma):
    entrar(client, EMAILS["aluna"])
    assert client.get("/api/disciplinas/9999/mensagens").status_code == 404


def test_chat_com_ia_exige_participacao(client, turma, gemini_falso):
    entrar(client, EMAILS["estranha"])
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat", json={"pergunta": "O que é limite?"})
    assert resposta.status_code == 403
    assert gemini_falso.chamadas_geracao == []

    entrar(client, EMAILS["aluna"])
    resposta = client.post(f"/api/disciplinas/{turma['disciplina']}/chat", json={"pergunta": "O que é limite?"})
    assert resposta.status_code == 200


def test_marcar_aula_exige_participacao(client, turma):
    entrar(client, EMAILS["estranha"])
    rota = f"/api/aulas/{turma['documento']}/concluida"
    assert client.put(rota, json={"concluida": True}).status_code == 403
    entrar(client, EMAILS["aluna"])
    assert client.put(rota, json={"concluida": True}).status_code == 200


def test_listagens_mostram_so_as_disciplinas_da_pessoa(client, turma):
    entrar(client, EMAILS["outro_prof"])
    assert [d["id"] for d in client.get("/api/disciplinas").json()] == [turma["outra_disciplina"]]
    assert [d["id"] for d in client.get("/api/visao-geral").json()] == [turma["outra_disciplina"]]

    entrar(client, EMAILS["aluna"])
    assert [d["id"] for d in client.get("/api/disciplinas").json()] == [turma["disciplina"]]

    entrar(client, EMAILS["admin"])
    assert {d["id"] for d in client.get("/api/disciplinas").json()} == {turma["disciplina"], turma["outra_disciplina"]}


def test_lembretes_so_das_disciplinas_da_pessoa(client, turma):
    from backend.infraestrutura import db

    hoje = date.today().isoformat()
    db.executar(
        "INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, hora, publico) VALUES (?, ?, ?, ?, ?, 1)",
        (turma["outra_disciplina"], turma["outro_prof"], "Prova de Física", hoje, "10:00"),
    )
    entrar(client, EMAILS["aluna"])
    assert client.get(f"/api/lembretes?data={hoje}").json() == []
    entrar(client, EMAILS["outro_prof"])
    assert [e["titulo"] for e in client.get(f"/api/lembretes?data={hoje}").json()] == ["Prova de Física"]


def test_matricula_so_para_aluno_e_admin_remove_qualquer_disciplina(client, turma):
    entrar(client, EMAILS["dono"])
    resposta = client.post("/api/disciplinas/matricular", json={"disciplina_ids": [turma["outra_disciplina"]]})
    assert resposta.status_code == 403

    entrar(client, EMAILS["outro_prof"])
    assert client.delete(f"/api/disciplinas/{turma['disciplina']}").status_code == 403
    entrar(client, EMAILS["admin"])
    assert client.delete(f"/api/disciplinas/{turma['disciplina']}").status_code == 200


def _chamadas(dependant):
    for dependencia in dependant.dependencies:
        yield dependencia.call
        yield from _chamadas(dependencia)


def test_toda_rota_por_disciplina_confere_participacao():
    """Estrutural: uma rota nova com {disciplina_id} (ou ?disciplina_id=) sem a checagem quebra este teste."""
    from backend.api.dependencias import participante_da_disciplina, professor_da_disciplina
    from backend.main import ROUTERS

    protegidas = {participante_da_disciplina, professor_da_disciplina}
    verificadas, sem_checagem = 0, []
    # Percorre os routers (o FastAPI recente não achata as rotas incluídas em app.routes)
    for router in ROUTERS:
        do_router = {d.dependency for d in router.dependencies}
        for rota in router.routes:
            if not isinstance(rota, APIRoute):
                continue
            usa_disciplina = "{disciplina_id}" in rota.path or any(
                p.name == "disciplina_id" for p in rota.dependant.query_params
            )
            # A remoção da disciplina confere dono/admin dentro do serviço
            if not usa_disciplina or rota.path == "/api/disciplinas/{disciplina_id}":
                continue
            verificadas += 1
            if not protegidas & (set(_chamadas(rota.dependant)) | do_router):
                sem_checagem.append(f"{sorted(rota.methods)} {rota.path}")
    assert verificadas >= 20
    assert sem_checagem == []
