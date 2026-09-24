"""Dados fictícios persistentes para demonstrar o chat e o calendário."""
import secrets
from datetime import date, timedelta

from . import db
from .auth import gerar_hash

CONTAS = [
    ("Marina Costa", "demo-marina@exemplo.local", "aluno"),
    ("Rafael Mendes", "demo-rafael@exemplo.local", "aluno"),
    ("Luiza Ferreira", "demo-luiza@exemplo.local", "aluno"),
    ("Prof. André (exemplo)", "demo-professor@exemplo.local", "professor"),
]


def popular_dados_demo(disciplina_id: int) -> None:
    """Cria mensagens e compromissos uma única vez para cada disciplina."""
    ids = {}
    for nome, email, tipo in CONTAS:
        conta = db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,))
        if not conta:
            db.executar(
                "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, gerar_hash(secrets.token_urlsafe(32)), tipo),
            )
            conta = db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,))
        ids[email] = conta["id"]

    if not db.consultar_um(
        "SELECT id FROM mensagens_turma WHERE disciplina_id = ? AND usuario_id IN (?, ?, ?, ?) LIMIT 1",
        (disciplina_id, *ids.values()),
    ):
        mensagens = [
            (ids["demo-marina@exemplo.local"], "Pessoal, alguém entendeu como calcular a derivada pela regra da cadeia?"),
            (ids["demo-rafael@exemplo.local"], "Sim! Primeiro deriva a função de fora e depois multiplica pela derivada da função de dentro."),
            (ids["demo-luiza@exemplo.local"], "Valeu! Podemos revisar um exemplo juntos antes da prova?"),
            (ids["demo-professor@exemplo.local"], "Boa ideia. Vamos fazer uma revisão em grupo na quinta-feira!"),
        ]
        with db.conectar() as c:
            c.executemany(
                "INSERT INTO mensagens_turma (disciplina_id, usuario_id, texto) VALUES (?, ?, ?)",
                [(disciplina_id, autor_id, texto) for autor_id, texto in mensagens],
            )

    eventos = [
        ("Revisão de cálculo em grupo", 2, "14:00", "Revisão de regra da cadeia e derivadas."),
        ("Grupo de estudos: limites", 4, "16:30", "Sessão de estudo na biblioteca."),
        ("Tira-dúvidas com o professor", 7, "10:00", "Atendimento para dúvidas da lista."),
    ]
    with db.conectar() as c:
        for titulo, dias, hora, descricao in eventos:
            data = (date.today() + timedelta(days=dias)).isoformat()
            existente = c.execute(
                "SELECT id FROM eventos WHERE disciplina_id = ? AND usuario_id = ? AND titulo = ? AND data = ?",
                (disciplina_id, ids["demo-professor@exemplo.local"], titulo, data),
            ).fetchone()
            if not existente:
                c.execute(
                    "INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, hora, descricao, publico) VALUES (?, ?, ?, ?, ?, ?, 1)",
                    (disciplina_id, ids["demo-professor@exemplo.local"], titulo, data, hora, descricao),
                )
