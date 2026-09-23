"""Popula o sistema com as disciplinas e aulas do curso de Ciência da Computação.

Para cada disciplina de dados_curso_cc.py:
  - cria a disciplina (dona: uma conta de professor);
  - gera um PDF por aula e indexa no RAG (chat, resumo, flashcards e simulado funcionam);
  - agenda as aulas e a prova no calendário da turma;
  - publica uma atividade com prazo.

Pode ser rodado de novo sem duplicar nada: o que já existe é pulado (útil se a
cota do Gemini acabar no meio da indexação).

IMPORTANTE: pare o servidor antes. Ele mantém o banco vetorial em memória e, ao
receber um novo upload, sobrescreveria os trechos indexados por este script.

Uso (na pasta raiz do projeto):
    python -m scripts.popular_curso
    python -m scripts.popular_curso --email eu@escola.com   # usa um professor já cadastrado
"""
import argparse
import html
import re
import socket
import sys
from datetime import date, timedelta

import pymupdf

from backend import db, rag
from backend.auth import gerar_hash

from .dados_curso_cc import DISCIPLINAS

EMAIL_PADRAO = "professor.cc@exemplo.com"
SENHA_PADRAO = "professor123"

CSS_PDF = """
* { font-family: sans-serif; }
body { font-size: 11pt; line-height: 1.45; color: #1f2330; }
.cabecalho { font-size: 9pt; color: #6b7080; }
h1 { font-size: 20pt; color: #4f46e5; margin: 4pt 0 2pt; }
h2 { font-size: 13pt; color: #1f2330; margin: 14pt 0 4pt; }
p { margin: 0 0 6pt; text-align: justify; }
li { margin-bottom: 3pt; }
"""


def servidor_rodando(porta: int = 8000) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def obter_professor(email: str, senha: str) -> int:
    usuario = db.consultar_um("SELECT id, tipo FROM usuarios WHERE email = ?", (email,))
    if usuario:
        if usuario["tipo"] != "professor":
            sys.exit(f"A conta {email} é de aluno. Informe o e-mail de um professor com --email.")
        return usuario["id"]
    print(f"Criando a conta de professor {email} (senha: {senha})")
    return db.executar(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, 'professor')",
        ("Coordenação de Ciência da Computação", email, gerar_hash(senha)),
    )


def nome_do_arquivo(numero: int, titulo: str) -> str:
    titulo = re.sub(r"[^\w\s-]", "", titulo)  # tira caracteres proibidos em nomes de arquivo
    return f"Aula {numero:02d} - {titulo}.pdf"


def gerar_pdf(caminho, disciplina: dict, numero: int, aula: dict) -> None:
    e = html.escape
    corpo = [
        f"<p class='cabecalho'>Ciência da Computação · {disciplina['semestre']}º semestre · "
        f"{e(disciplina['nome'])} · Aula {numero}</p>",
        f"<h1>{e(aula['titulo'])}</h1>",
    ]
    for subtitulo, texto in aula["secoes"]:
        corpo += [f"<h2>{e(subtitulo)}</h2>", f"<p>{e(texto)}</p>"]
    corpo.append("<h2>Pontos-chave</h2><ul>" + "".join(f"<li>{e(p)}</li>" for p in aula["pontos"]) + "</ul>")

    # Story distribui o HTML pelas páginas que forem necessárias
    story = pymupdf.Story(html="".join(corpo), user_css=CSS_PDF)
    pagina = pymupdf.paper_rect("a4")
    area = pagina + (56, 56, -56, -56)  # margens de ~2 cm
    caminho.parent.mkdir(parents=True, exist_ok=True)
    escritor = pymupdf.DocumentWriter(str(caminho))
    continua = True
    while continua:
        dispositivo = escritor.begin_page(pagina)
        continua, _ = story.place(area)
        story.draw(dispositivo)
        escritor.end_page()
    escritor.close()


def proxima_segunda() -> date:
    hoje = date.today()
    return hoje + timedelta(days=7 - hoje.weekday())


def agendar(disciplina_id: int, professor_id: int, d: dict) -> None:
    """Aulas em semanas seguidas no dia da disciplina; prazo da atividade e prova depois."""
    inicio = proxima_segunda() + timedelta(days=d["dia"])
    datas_aulas = [inicio + timedelta(weeks=i) for i in range(len(d["aulas"]))]
    eventos = [
        (f"Aula {i}: {aula['titulo']}", dia, "Material disponível no Assistente IA.")
        for i, (aula, dia) in enumerate(zip(d["aulas"], datas_aulas), start=1)
    ]
    eventos.append(("Prova 1", datas_aulas[-1] + timedelta(weeks=2), "Conteúdo: todas as aulas até aqui."))
    for titulo, dia, descricao in eventos:
        db.executar(
            """INSERT INTO eventos (disciplina_id, usuario_id, titulo, data, descricao, publico)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (disciplina_id, professor_id, titulo, dia.isoformat(), descricao),
        )
    atividade = d["atividade"]
    db.executar(
        "INSERT INTO atividades (disciplina_id, criado_por, titulo, descricao, prazo) VALUES (?, ?, ?, ?, ?)",
        (disciplina_id, professor_id, atividade["titulo"], atividade["descricao"],
         (datas_aulas[-1] + timedelta(weeks=1)).isoformat()),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", default=EMAIL_PADRAO, help="professor dono das disciplinas")
    parser.add_argument("--senha", default=SENHA_PADRAO, help="senha, caso a conta precise ser criada")
    args = parser.parse_args()
    for saida in (sys.stdout, sys.stderr):  # o console do Windows usa cp1252 por padrão
        saida.reconfigure(encoding="utf-8")

    if servidor_rodando():
        sys.exit("O servidor está rodando na porta 8000. Pare-o (Ctrl+C) e rode este script de novo.")

    db.criar_tabelas()
    professor_id = obter_professor(args.email.strip().lower(), args.senha)
    falhas = 0

    for d in DISCIPLINAS:
        existente = db.consultar_um("SELECT id FROM disciplinas WHERE nome = ?", (d["nome"],))
        if existente:
            disciplina_id = existente["id"]
            print(f"\n= {d['nome']} (já existe)")
        else:
            disciplina_id = db.executar(
                "INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", (d["nome"], professor_id))
            agendar(disciplina_id, professor_id, d)
            print(f"\n+ {d['nome']} ({d['semestre']}º semestre): calendário e atividade criados")

        for numero, aula in enumerate(d["aulas"], start=1):
            arquivo = nome_do_arquivo(numero, aula["titulo"])
            if db.consultar_um("SELECT 1 FROM documentos WHERE disciplina_id = ? AND arquivo = ?",
                               (disciplina_id, arquivo)):
                print(f"  = {arquivo} (já indexado)")
                continue
            caminho = rag.caminho_do_pdf(disciplina_id, arquivo)
            gerar_pdf(caminho, d, numero, aula)
            try:
                trechos = rag.indexar_pdf(disciplina_id, arquivo)
            except Exception as erro:  # sem chave, sem cota, sem internet...
                caminho.unlink(missing_ok=True)
                falhas += 1
                print(f"  ✖ {arquivo}: {erro}")
                continue
            db.executar(
                "INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por) VALUES (?, ?, ?, ?)",
                (disciplina_id, arquivo, trechos, professor_id),
            )
            print(f"  + {arquivo}: {trechos} trechos indexados")

    print(f"\nPronto: {len(DISCIPLINAS)} disciplinas.")
    if falhas:
        print(f"{falhas} aula(s) não foram indexadas. Rode o script de novo para tentar só essas.")


if __name__ == "__main__":
    main()
