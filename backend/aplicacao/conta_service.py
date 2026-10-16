"""Direitos do titular sobre a própria conta (LGPD, arts. 18 e 19): exportar e excluir.

Exclusão: os dados pessoais da pessoa são apagados. O que pertence à turma e não
à pessoa (disciplinas, materiais, atividades, vídeos e eventos públicos criados
por um professor) passa para a conta de sistema "Professor removido", para os
alunos não perderem a disciplina; um administrador decide depois o destino.

Cada exclusão fica registrada em PASTA_DADOS/exclusoes.jsonl (só o número da
conta e a data), para ser refeita se um backup antigo for restaurado.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from .. import config
from ..core.seguranca import conferir_senha
from ..infraestrutura import db, metricas
from . import pseudonimo

logger = logging.getLogger("conta")

EMAIL_CONTA_SISTEMA = "professor-removido@sistema.invalid"

# Toda (tabela, coluna) que referencia usuarios SEM "ON DELETE CASCADE" precisa estar
# numa destas listas; o teste estrutural (tests/test_conta.py) confere isso.
REATRIBUIR_AO_SISTEMA = [
    ("disciplinas", "criado_por"),
    ("documentos", "enviado_por"),
    ("atividades", "criado_por"),
    ("videos", "adicionado_por"),
]
APAGAR = [
    ("perguntas", "usuario_id"),
    ("resultados_simulado", "usuario_id"),
    ("entregas", "aluno_id"),
    ("mensagens_turma", "usuario_id"),
]
# eventos.usuario_id: públicos (da turma) vão para o sistema; lembretes pessoais são apagados
TRATADOS_A_PARTE = [("eventos", "usuario_id")]


# ---------------------------------------------------------------- exportação

def _consultas_de_exportacao(usuario_id: int) -> dict[str, tuple[str, tuple]]:
    u = (usuario_id,)
    return {
        "matriculas": ("""SELECT d.nome AS disciplina, m.criado_em FROM matriculas m
                          JOIN disciplinas d ON d.id = m.disciplina_id WHERE m.aluno_id = ?""", u),
        "perguntas_ao_assistente": ("""SELECT d.nome AS disciplina, p.pergunta, p.resposta, p.criado_em
                                       FROM perguntas p JOIN disciplinas d ON d.id = p.disciplina_id
                                       WHERE p.usuario_id = ? ORDER BY p.criado_em""", u),
        "resultados_de_simulados": ("""SELECT d.nome AS disciplina, r.arquivo, r.acertos, r.total, r.criado_em
                                       FROM resultados_simulado r JOIN disciplinas d ON d.id = r.disciplina_id
                                       WHERE r.usuario_id = ? ORDER BY r.criado_em""", u),
        "simulados": ("""SELECT d.nome AS disciplina, s.arquivo, s.questoes_json, s.respostas_json, s.acertos,
                                s.total, s.criado_em, s.finalizado_em
                         FROM simulados s JOIN disciplinas d ON d.id = s.disciplina_id
                         WHERE s.usuario_id = ? ORDER BY s.criado_em""", u),
        "aulas_estudadas": ("""SELECT d.nome AS disciplina, doc.arquivo, c.criado_em FROM aulas_concluidas c
                               JOIN documentos doc ON doc.id = c.documento_id
                               JOIN disciplinas d ON d.id = doc.disciplina_id WHERE c.usuario_id = ?""", u),
        "eventos_e_lembretes": ("""SELECT d.nome AS disciplina, e.titulo, e.data, e.hora, e.descricao,
                                          e.publico, e.criado_em
                                   FROM eventos e JOIN disciplinas d ON d.id = e.disciplina_id
                                   WHERE e.usuario_id = ? ORDER BY e.data""", u),
        "entregas_de_atividades": ("""SELECT d.nome AS disciplina, a.titulo AS atividade, e.resposta, e.nota,
                                             e.comentario, e.criado_em
                                      FROM entregas e JOIN atividades a ON a.id = e.atividade_id
                                      JOIN disciplinas d ON d.id = a.disciplina_id WHERE e.aluno_id = ?""", u),
        "mensagens_no_chat_da_turma": ("""SELECT d.nome AS disciplina, m.texto, m.criado_em FROM mensagens_turma m
                                          JOIN disciplinas d ON d.id = m.disciplina_id
                                          WHERE m.usuario_id = ? ORDER BY m.criado_em""", u),
        "chamados_de_suporte": ("""SELECT categoria, assunto, mensagem, resposta, criado_em, respondido_em
                                   FROM chamados_suporte WHERE usuario_id = ? ORDER BY criado_em""", u),
        "disciplinas_criadas": ("SELECT nome, criado_em FROM disciplinas WHERE criado_por = ?", u),
        "materiais_enviados": ("""SELECT d.nome AS disciplina, doc.arquivo, doc.criado_em FROM documentos doc
                                  JOIN disciplinas d ON d.id = doc.disciplina_id WHERE doc.enviado_por = ?""", u),
        "atividades_criadas": ("SELECT titulo, descricao, prazo, criado_em FROM atividades WHERE criado_por = ?", u),
        "videos_adicionados": ("SELECT titulo, url, descricao, criado_em FROM videos WHERE adicionado_por = ?", u),
        "sessoes_ativas": ("""SELECT criado_em, expires_at FROM sessoes
                              WHERE usuario_id = ? AND expires_at > CURRENT_TIMESTAMP""", u),
    }


def exportar(usuario_id: int) -> dict:
    """Todos os dados da pessoa em formato estruturado (acesso e portabilidade, art. 18, II e V).
    Fica de fora só o que é segredo de segurança: hash da senha e tokens."""
    conta = db.consultar_um(
        """SELECT nome, email, tipo, administrador, criado_em, aceite_privacidade_versao, aceite_privacidade_em,
                  maioridade_declarada_em, email_verificado_em, ultimo_acesso
           FROM usuarios WHERE id = ?""",
        (usuario_id,),
    )
    dados = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sistema": "Assistente de Estudos",
        "conta": conta,
    }
    for nome, (sql, parametros) in _consultas_de_exportacao(usuario_id).items():
        dados[nome] = db.consultar(sql, parametros)
    logger.info("dados_exportados", extra={"usuario_id": usuario_id})
    metricas.registrar("dados_exportados")
    return dados


# ---------------------------------------------------------------- exclusão

def _conta_sistema(c: sqlite3.Connection) -> int:
    linha = c.execute("SELECT id FROM usuarios WHERE email = ?", (EMAIL_CONTA_SISTEMA,)).fetchone()
    if linha:
        return linha["id"]
    # senha_hash "!" nunca confere (conferir_senha recusa o formato) e sistema=1 bloqueia o login
    return c.execute(
        """INSERT INTO usuarios (nome, email, senha_hash, tipo, sistema) VALUES (?, ?, '!', 'professor', 1)""",
        ("Professor removido", EMAIL_CONTA_SISTEMA),
    ).lastrowid


def _excluir_dados(c: sqlite3.Connection, usuario_id: int, email: str) -> None:
    sistema = _conta_sistema(c)
    for tabela, coluna in REATRIBUIR_AO_SISTEMA:
        c.execute(f"UPDATE {tabela} SET {coluna} = ? WHERE {coluna} = ?", (sistema, usuario_id))
    c.execute("UPDATE eventos SET usuario_id = ? WHERE usuario_id = ? AND publico = 1", (sistema, usuario_id))
    c.execute("DELETE FROM eventos WHERE usuario_id = ?", (usuario_id,))
    for tabela, coluna in APAGAR:
        c.execute(f"DELETE FROM {tabela} WHERE {coluna} = ?", (usuario_id,))
    c.execute("DELETE FROM limite_uso WHERE chave = ?", (f"usuario:{usuario_id}",))
    c.execute("DELETE FROM tentativas_login WHERE chave = ?", (pseudonimo.chave("email", email),))
    # sessões, matrículas, aulas estudadas, chamados e demais tabelas novas saem em cascata
    c.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))


def _registrar_exclusao(usuario_id: int) -> None:
    registro = {"usuario_id": usuario_id, "excluido_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    caminho = config.PASTA_DADOS / "exclusoes.jsonl"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro) + "\n")


def excluir_conta(usuario: dict, senha: str, confirmacao: str) -> None:
    if confirmacao.strip().upper() != "EXCLUIR":
        raise HTTPException(400, "Para confirmar, digite EXCLUIR.")
    salvo = db.consultar_um("SELECT senha_hash, email, administrador FROM usuarios WHERE id = ?", (usuario["id"],))
    if not salvo or not conferir_senha(senha, salvo["senha_hash"]):
        raise HTTPException(400, "Senha incorreta.")
    if salvo["administrador"]:
        outros = db.consultar_um(
            "SELECT COUNT(*) AS n FROM usuarios WHERE administrador = 1 AND sistema = 0 AND id != ?",
            (usuario["id"],),
        )["n"]
        if not outros:
            raise HTTPException(409, "Você é o único administrador. Nomeie outro administrador antes de excluir a conta.")
    with db.conectar() as c:
        _excluir_dados(c, usuario["id"], salvo["email"])
    _registrar_exclusao(usuario["id"])
    logger.info("conta_excluida", extra={"usuario_id": usuario["id"]})
    metricas.registrar("conta_excluida")


def reaplicar_exclusoes(caminho: Path) -> int:
    """Depois de restaurar um backup: exclui de novo as contas que já tinham sido excluídas."""
    total, maior_id = 0, 0
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        usuario_id = json.loads(linha)["usuario_id"]
        maior_id = max(maior_id, usuario_id)
        conta = db.consultar_um("SELECT email FROM usuarios WHERE id = ? AND sistema = 0", (usuario_id,))
        if conta:
            with db.conectar() as c:
                _excluir_dados(c, usuario_id, conta["email"])
            total += 1
    # O backup é mais antigo que algumas contas: sem isto, uma conta nova poderia
    # receber o número de uma conta excluída e ser apagada na próxima restauração.
    db.executar("UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = 'usuarios'", (maior_id,))
    return total
