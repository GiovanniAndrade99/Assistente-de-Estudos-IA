"""Restaura um backup criado por scripts/backup.py.

Uso, na pasta raiz do projeto, com o servidor PARADO:
    python -m scripts.restaurar_backup backups/2026-10-15_120000 --confirmar

Nada é apagado: a pasta de dados atual é renomeada para
data.antes-da-restauracao-<data> antes de copiar o backup. Contas excluídas
depois do backup são excluídas de novo no banco restaurado (LGPD: um pedido de
exclusão atendido não pode ser desfeito por uma restauração).
"""
import argparse
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path

from backend import config


def servidor_rodando(portas: tuple[int, ...] = (8000, 8002)) -> int | None:
    for porta in portas:
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                return porta
    return None


def restaurar(pasta_backup: Path) -> Path | None:
    """Copia o backup para PASTA_DADOS. Retorna para onde foram os dados anteriores."""
    if not (pasta_backup / "app.db").exists():
        raise SystemExit(f"{pasta_backup} não parece um backup (falta app.db).")
    dados = config.PASTA_DADOS
    reserva = None
    if dados.exists():
        reserva = dados.with_name(f"{dados.name}.antes-da-restauracao-{datetime.now():%Y-%m-%d_%H%M%S}")
        dados.rename(reserva)
    dados.mkdir(parents=True)
    shutil.copy2(pasta_backup / "app.db", dados / "app.db")
    for nome in ("uploads", "indice"):
        if (pasta_backup / nome).exists():
            shutil.copytree(pasta_backup / nome, dados / nome)
    _reaplicar_exclusoes(reserva)
    return reserva


def _reaplicar_exclusoes(reserva: Path | None) -> None:
    """Exclui de novo as contas apagadas depois do backup (registro em exclusoes.jsonl)."""
    if reserva is None or not (reserva / "exclusoes.jsonl").exists():
        return
    shutil.copy2(reserva / "exclusoes.jsonl", config.PASTA_DADOS / "exclusoes.jsonl")
    from backend.aplicacao import conta_service

    total = conta_service.reaplicar_exclusoes(config.PASTA_DADOS / "exclusoes.jsonl")
    print(f"Exclusões de conta reaplicadas: {total}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pasta", type=Path, help="pasta do backup (ex.: backups/2026-10-15_120000)")
    parser.add_argument("--confirmar", action="store_true", help="confirma que quer substituir os dados atuais")
    parser.add_argument("--porta", type=int, action="append", help="porta do servidor a conferir (padrão: 8000 e 8002)")
    args = parser.parse_args()

    porta = servidor_rodando(tuple(args.porta) if args.porta else (8000, 8002))
    if porta:
        sys.exit(f"O servidor está rodando na porta {porta}. Pare-o antes de restaurar.")
    if not args.confirmar:
        sys.exit("Isto substitui os dados atuais (eles são guardados ao lado). Rode de novo com --confirmar.")
    reserva = restaurar(args.pasta)
    print(f"Backup restaurado em {config.PASTA_DADOS}.")
    if reserva:
        print(f"Os dados anteriores ficaram em {reserva}.")


if __name__ == "__main__":
    main()
