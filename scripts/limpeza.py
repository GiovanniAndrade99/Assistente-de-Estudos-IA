"""Aplica agora a política de retenção de dados (a mesma que o servidor roda sozinho).

Uso, na pasta raiz do projeto: python -m scripts.limpeza
"""
from backend.aplicacao import retencao_service
from backend.infraestrutura import db


def main() -> None:
    db.criar_tabelas()
    for nome, quantidade in retencao_service.executar_limpeza().items():
        print(f"{nome}: {quantidade} registro(s) apagado(s)")


if __name__ == "__main__":
    main()
