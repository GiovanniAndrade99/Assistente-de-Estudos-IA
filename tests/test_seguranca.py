import hashlib

from backend.core.seguranca import (
    ITERACOES_SENHA,
    conferir_senha,
    gerar_hash_senha,
    gerar_token_sessao,
    hash_token,
)


def test_hash_de_senha_tem_salt_e_verifica_senha():
    senha = "senha-forte-de-teste"
    salvo = gerar_hash_senha(senha)

    iteracoes, salt, _digest = salvo.split("$")
    assert int(iteracoes) == ITERACOES_SENHA
    assert conferir_senha(senha, salvo)
    assert not conferir_senha("senha-errada", salvo)
    assert gerar_hash_senha(senha) != salvo  # salt individual por geração
    assert len(bytes.fromhex(salt)) == 16


def test_hash_corrompido_e_rejeitado_sem_excecao():
    for salvo in ("", "abc", "999999999999$00$00", "600000$xyz$xyz"):
        assert not conferir_senha("senha", salvo)


def test_token_de_sessao_e_aleatorio_e_banco_guarda_seu_hash():
    token = gerar_token_sessao()
    assert len(token) >= 40
    assert hash_token(token) == hashlib.sha256(token.encode()).hexdigest()
    assert hash_token(token) != token
