"""Funções de apoio para os testes (importadas com `from apoio import ...`)."""
import hashlib
from functools import lru_cache

import numpy as np
from fastapi.testclient import TestClient

SENHA_PADRAO = "senha-segura-123"


@lru_cache(maxsize=None)
def _hash_da_senha(senha: str) -> str:
    """O PBKDF2 é lento de propósito; nos testes cada senha é derivada uma vez só."""
    from backend.core.seguranca import gerar_hash_senha

    return gerar_hash_senha(senha)


def criar_usuario(
    email: str,
    tipo: str = "aluno",
    nome: str = "Pessoa de Teste",
    senha: str = SENHA_PADRAO,
    administrador: bool = False,
) -> int:
    """Cria a conta direto no banco (sem passar pelo limite de cadastro por IP)."""
    from backend.infraestrutura import db

    return db.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo, administrador) VALUES (?, ?, ?, ?, ?)",
        (nome, email, _hash_da_senha(senha), tipo, int(administrador)),
    )


def entrar(client: TestClient, email: str, senha: str = SENHA_PADRAO):
    resposta = client.post("/api/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return resposta


def criar_disciplina(nome: str, professor_id: int) -> int:
    from backend.infraestrutura import db

    return db.executar("INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", (nome, professor_id))


def matricular(aluno_id: int, disciplina_id: int) -> None:
    from backend.infraestrutura import db

    db.executar("INSERT INTO matriculas (aluno_id, disciplina_id) VALUES (?, ?)", (aluno_id, disciplina_id))


def vetor_do_texto(texto: str, dimensoes: int = 64) -> list[float]:
    """Embedding determinístico: saco de palavras espalhado por hash.
    Textos com palavras em comum ficam próximos, o que basta para testar a busca."""
    vetor = np.zeros(dimensoes, dtype=np.float32)
    for palavra in texto.lower().split():
        indice = int(hashlib.md5(palavra.encode()).hexdigest(), 16) % dimensoes
        vetor[indice] += 1.0
    if not vetor.any():
        vetor[0] = 1.0
    return vetor.tolist()
