"""Cria uma conta administrativa de forma interativa e sem senha padrão.

Uso na pasta raiz do projeto: python -m scripts.criar_admin
"""
import getpass
import re

from backend.core.seguranca import gerar_hash_senha
from backend.infraestrutura import db


def main() -> None:
    db.criar_tabelas()
    nome = input("Nome do administrador: ").strip()
    email = input("E-mail do administrador: ").strip().lower()
    if not nome:
        raise SystemExit("Informe um nome.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SystemExit("Informe um e-mail válido.")
    if db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,)):
        raise SystemExit("Esse e-mail já está cadastrado. Use outro para a conta administrativa.")

    senha = getpass.getpass("Senha (mínimo 6 caracteres): ")
    confirmacao = getpass.getpass("Confirme a senha: ")
    if len(senha) < 6:
        raise SystemExit("A senha precisa ter pelo menos 6 caracteres.")
    if senha != confirmacao:
        raise SystemExit("As senhas não conferem.")

    db.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo, administrador) VALUES (?, ?, ?, 'professor', 1)",
        (nome, email, gerar_hash_senha(senha)),
    )
    print(f"Conta administrativa criada para {email}.")


if __name__ == "__main__":
    main()
