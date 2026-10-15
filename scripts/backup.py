"""Backup do banco, dos PDFs e do índice vetorial.

Uso, na pasta raiz do projeto:
    python -m scripts.backup

Cria backups/<AAAA-MM-DD_HHMMSS>/ (ou na pasta de PASTA_BACKUPS) com uma cópia
consistente do SQLite (API de backup, funciona com o servidor no ar), os PDFs e o
índice. Depois apaga os backups com mais de RETENCAO_BACKUP_DIAS dias: o aviso de
privacidade informa esse prazo, porque dados de uma conta excluída continuam nos
backups até eles vencerem. Guarde a pasta de backups em local protegido.

Para rodar todo dia: Agendador de Tarefas do Windows ou cron (veja o README).
"""
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from backend import config
from backend.infraestrutura import db

FORMATO_PASTA = "%Y-%m-%d_%H%M%S"


def _sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def fazer_backup(base: Path | None = None) -> Path:
    base = base or config.PASTA_BACKUPS
    pasta = base / datetime.now().strftime(FORMATO_PASTA)
    pasta.mkdir(parents=True)

    origem = sqlite3.connect(db.ARQUIVO_DB)
    copia = sqlite3.connect(pasta / "app.db")
    try:
        origem.backup(copia)
        integridade = copia.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        copia.close()
        origem.close()
    if integridade != "ok":
        raise RuntimeError(f"A cópia do banco falhou na verificação de integridade: {integridade}")

    for nome in ("uploads", "indice"):
        fonte = config.PASTA_DADOS / nome
        if fonte.exists():
            shutil.copytree(fonte, pasta / nome)

    manifesto = {
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "sha256_app_db": _sha256(pasta / "app.db"),
        "integridade": integridade,
        "pastas": [nome for nome in ("uploads", "indice") if (pasta / nome).exists()],
    }
    (pasta / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return pasta


def apagar_vencidos(base: Path | None = None, dias: int | None = None) -> list[Path]:
    base = base or config.PASTA_BACKUPS
    dias = config.RETENCAO_BACKUP_DIAS if dias is None else dias
    limite = datetime.now() - timedelta(days=dias)
    apagados = []
    for pasta in sorted(base.iterdir()) if base.exists() else []:
        try:
            criado = datetime.strptime(pasta.name, FORMATO_PASTA)
        except ValueError:
            continue  # não é uma pasta criada por este script
        if criado < limite:
            shutil.rmtree(pasta)
            apagados.append(pasta)
    return apagados


def main() -> None:
    pasta = fazer_backup()
    print(f"Backup criado em {pasta}")
    for vencido in apagar_vencidos():
        print(f"Backup vencido apagado: {vencido.name}")


if __name__ == "__main__":
    main()
