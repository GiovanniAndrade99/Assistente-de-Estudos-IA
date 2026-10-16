"""Métricas de uso: só contagens diárias, sem identificar ninguém."""
from types import SimpleNamespace

from apoio import DECLARACOES, criar_disciplina, criar_usuario, entrar, matricular


def _totais(client):
    return client.get("/api/admin/metricas?dias=7").json()["totais"]


def test_tabela_de_metricas_nao_tem_dado_pessoal(database):
    colunas = {linha["name"] for linha in database.consultar("PRAGMA table_info(metricas_diarias)")}
    assert colunas == {"dia", "evento", "total"}


def test_eventos_sao_contados(client):
    criar_usuario("admin@example.test", "professor", administrador=True)
    prof = criar_usuario("prof@example.test", "professor")
    disciplina = criar_disciplina("Cálculo", prof)
    client.post("/api/auth/cadastro", json={
        "nome": "Nova", "email": "nova@example.test", "senha": "senha-segura-123", "tipo": "aluno", **DECLARACOES,
    })
    nova = client.get("/api/auth/eu").json()["id"]
    matricular(nova, disciplina)
    for pergunta in ("O que é limite?", "E derivada?"):
        client.post(f"/api/disciplinas/{disciplina}/chat", json={"pergunta": pergunta})

    entrar(client, "admin@example.test")
    totais = _totais(client)
    assert totais["cadastro_aluno"] == 1
    assert totais["login"] == 1
    assert totais["pergunta_chat"] == 2
    assert totais["primeira_pergunta"] == 1


def test_chamadas_e_tokens_da_ia_entram_nas_metricas(client):
    from backend.infraestrutura import rag

    uso = SimpleNamespace(prompt_token_count=120, candidates_token_count=30, thoughts_token_count=10)
    rag.registrar_uso(SimpleNamespace(usage_metadata=uso))
    criar_usuario("admin@example.test", "professor", administrador=True)
    entrar(client, "admin@example.test")
    totais = _totais(client)
    assert (totais["chamadas_ia"], totais["tokens_entrada"], totais["tokens_saida"]) == (1, 120, 40)


def test_metricas_so_para_admin(client):
    criar_usuario("prof@example.test", "professor")
    entrar(client, "prof@example.test")
    assert client.get("/api/admin/metricas").status_code == 403
