from apoio import DECLARACOES
def test_catalogo_publico_e_matricula_do_aluno(database, client):
    professor_id = database.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
        ("Professora", "professora@example.test", "hash-de-fixture", "professor"),
    )
    primeira = database.executar(
        "INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", ("Cálculo I", professor_id)
    )
    segunda = database.executar(
        "INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", ("Álgebra", professor_id)
    )

    catalogo = client.get("/api/disciplinas/publico")
    assert catalogo.status_code == 200
    assert {disciplina["id"] for disciplina in catalogo.json()} == {primeira, segunda}
    assert all(set(disciplina) == {"id", "nome"} for disciplina in catalogo.json())

    cadastro = client.post("/api/auth/cadastro", json={
        "nome": "Estudante",
        "email": "estudante@example.test",
        "senha": "senha-segura-123",
        "tipo": "aluno",
        **DECLARACOES,
        "disciplinas": [primeira],
    })
    assert cadastro.status_code == 200
    assert [d["id"] for d in client.get("/api/disciplinas").json()] == [primeira]

    assert client.post("/api/disciplinas/matricular", json={"disciplina_ids": [segunda]}).status_code == 200
    assert {d["id"] for d in client.get("/api/disciplinas").json()} == {primeira, segunda}


def test_aluno_nao_pode_criar_disciplina(client):
    cadastro = client.post("/api/auth/cadastro", json={
        "nome": "Estudante",
        "email": "estudante@example.test",
        "senha": "senha-segura-123",
        "tipo": "aluno",
        **DECLARACOES,
    })
    assert cadastro.status_code == 200
    resposta = client.post("/api/disciplinas", json={"nome": "Disciplina restrita"})
    assert resposta.status_code == 403
