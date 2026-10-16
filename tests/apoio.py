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
    ciente: bool = True,
) -> int:
    """Cria a conta direto no banco (sem passar pelo limite de cadastro por IP).
    `ciente=True`: já confirmou o aviso de privacidade atual e a idade mínima."""
    from backend import config
    from backend.infraestrutura import db

    usuario_id = db.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo, administrador) VALUES (?, ?, ?, ?, ?)",
        (nome, email, _hash_da_senha(senha), tipo, int(administrador)),
    )
    if ciente:
        db.executar(
            """UPDATE usuarios SET aceite_privacidade_versao = ?, aceite_privacidade_em = CURRENT_TIMESTAMP,
                      maioridade_declarada_em = CURRENT_TIMESTAMP WHERE id = ?""",
            (config.POLITICA_PRIVACIDADE_VERSAO, usuario_id),
        )
    return usuario_id


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


# Campos obrigatórios do cadastro pela API (ciência do aviso e idade mínima)
DECLARACOES = {"aceite_privacidade": True, "declara_maioridade": True}



def criar_pdf(caminho, paginas: list[str]) -> None:
    """PDF de teste com uma página para cada texto."""
    import pymupdf

    caminho.parent.mkdir(parents=True, exist_ok=True)
    documento = pymupdf.open()
    for texto in paginas:
        pagina = documento.new_page()
        pagina.insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=11)
    documento.save(caminho)
    documento.close()


def criar_documento(disciplina_id: int, arquivo: str, enviado_por: int, paginas: list[str]) -> int:
    """PDF na pasta de uploads + linha em documentos (sem indexar no RAG)."""
    from backend.infraestrutura import db, rag

    criar_pdf(rag.caminho_do_pdf(disciplina_id, arquivo), paginas)
    return db.executar(
        "INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por) VALUES (?, ?, 1, ?)",
        (disciplina_id, arquivo, enviado_por),
    )
