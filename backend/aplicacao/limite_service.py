"""Limite de requisições por usuário (ou IP) numa janela de tempo.

Protege rotas que custam dinheiro (chamam a API do Gemini) ou são alvo fácil
de automação (cadastro) contra abuso por bot/script. Mesmo padrão do rate
limit de login em auth_service.py: fica no banco, não em memória, para
sobreviver ao `--reload` do uvicorn e valer para múltiplos processos/workers.
"""
from fastapi import HTTPException

from ..infraestrutura import db


def limitar(chave: str, rota: str, limite: int, janela_minutos: int) -> None:
    """Levanta 429 se `chave` (usuário ou IP) já fez `limite` requisições a
    `rota` nos últimos `janela_minutos`. Senão, registra esta requisição.
    """
    with db.conectar() as c:
        c.execute(
            "DELETE FROM limite_uso WHERE rota = ? AND criado_em <= datetime('now', ?)",
            (rota, f"-{janela_minutos} minutes"),
        )
        total = c.execute(
            "SELECT COUNT(*) AS n FROM limite_uso WHERE chave = ? AND rota = ? AND criado_em > datetime('now', ?)",
            (chave, rota, f"-{janela_minutos} minutes"),
        ).fetchone()["n"]
        if total >= limite:
            raise HTTPException(
                429, "Muitas requisições. Tente novamente em alguns minutos.",
                headers={"Retry-After": str(janela_minutos * 60)},
            )
        c.execute("INSERT INTO limite_uso (chave, rota) VALUES (?, ?)", (chave, rota))
