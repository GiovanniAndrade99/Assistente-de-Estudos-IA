"""Dados fictícios persistentes para demonstrar o chat e o calendário."""
import secrets
from datetime import date, timedelta

from ..core.seguranca import gerar_hash_senha
from ..infraestrutura import db

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
                (nome, email, gerar_hash_senha(secrets.token_urlsafe(32)), tipo),
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

    _popular_atividade_demo(disciplina_id, ids)


# Respostas de exemplo que os alunos fictícios já entregaram e aguardam correção
ENTREGAS_DEMO = {
    "demo-marina@exemplo.local": "Resolvi os exercícios 1 a 5. No exercício 3 usei a regra da cadeia, "
                                 "mas fiquei em dúvida no sinal do resultado final.",
    "demo-rafael@exemplo.local": "Segue minha resolução completa da lista, com o passo a passo de cada questão.",
    "demo-luiza@exemplo.local": "Fiz as questões 1 a 4; a 5 não consegui terminar e gostaria de revisar em aula.",
}


def _popular_atividade_demo(disciplina_id: int, ids: dict) -> None:
    """Matricula os alunos fictícios e cria uma atividade com entregas já enviadas, sem nota."""
    professor_id = ids["demo-professor@exemplo.local"]
    for email, aluno_id in ids.items():
        if email != "demo-professor@exemplo.local":
            db.executar("INSERT OR IGNORE INTO matriculas (aluno_id, disciplina_id) VALUES (?, ?)",
                        (aluno_id, disciplina_id))

    atividade = db.consultar_um(
        "SELECT id FROM atividades WHERE disciplina_id = ? AND criado_por = ? LIMIT 1",
        (disciplina_id, professor_id),
    )
    if atividade:
        return
    prazo = (date.today() + timedelta(days=3)).isoformat()
    atividade_id = db.executar(
        "INSERT INTO atividades (disciplina_id, criado_por, titulo, descricao, prazo) VALUES (?, ?, ?, ?, ?)",
        (disciplina_id, professor_id, "Lista de exercícios 1 (exemplo)",
         "Resolva os exercícios da lista e descreva o raciocínio de cada questão.", prazo),
    )
    with db.conectar() as c:
        c.executemany(
            "INSERT OR IGNORE INTO entregas (atividade_id, aluno_id, resposta) VALUES (?, ?, ?)",
            [(atividade_id, ids[email], texto) for email, texto in ENTREGAS_DEMO.items()],
        )
