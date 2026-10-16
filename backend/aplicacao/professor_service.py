"""Regras de negócio do painel do professor.

Temas das dúvidas: as perguntas dos alunos são agrupadas aqui mesmo (TF-IDF e
similaridade de cosseno com NumPy), sem mandar nada de novo ao Gemini. Exemplos de
perguntas só aparecem em temas com perguntas de pelo menos dois alunos, e nunca com
o nome de quem perguntou.

CSV de notas: separador ";" e BOM (abre direto no Excel em português) e proteção
contra injeção de fórmula: célula que começa com = + - @ vira texto.
"""
import csv
import io
import re
import unicodedata

import numpy as np

from ..infraestrutura import db

# Palavras que não dizem o assunto da dúvida (já sem acento)
STOPWORDS = set("""
a o as os um uma uns umas de do da dos das em no na nos nas por para pra pro com sem que qual quais quando
como onde porque se e ou mas nem e sao ser foi era sera tem ter tinha ha isso isto esse essa este esta esses
essas aquele aquela ao aos me mim eu voce voces ele ela eles elas nos meu minha meus minhas seu sua seus suas
lhe lhes mais menos muito muita muitos muitas ja nao sim tambem entre sobre ate depois antes explique explica
explicar explicacao diferenca diferencas exemplo exemplos fale falar defina definicao significa significado
entender entendi pode podem poderia favor duvida professor professora aula aulas material conteudo coisa
coisas fazer faz serve servem usar usa usado funciona funcionam algum alguma alguns algumas cada outro outra
mesmo mesma tipo tipos forma formas jeito vez vezes the of and what how
""".split())


def perguntas_dos_alunos(disciplina_id: int) -> list[dict]:
    return db.consultar(
        """SELECT p.pergunta, p.resposta, p.criado_em, u.nome AS aluno
           FROM perguntas p JOIN usuarios u ON u.id = p.usuario_id
           WHERE p.disciplina_id = ? AND u.tipo = 'aluno'
           ORDER BY p.criado_em DESC LIMIT 200""",
        (disciplina_id,),
    )


def notas_dos_alunos(disciplina_id: int) -> list[dict]:
    return db.consultar(
        """SELECT u.nome AS aluno, r.arquivo, r.acertos, r.total, r.criado_em
           FROM resultados_simulado r JOIN usuarios u ON u.id = r.usuario_id
           WHERE r.disciplina_id = ? AND u.tipo = 'aluno'
           ORDER BY r.criado_em DESC LIMIT 200""",
        (disciplina_id,),
    )


# ---------------------------------------------------------------- temas das dúvidas

def _palavras(texto: str) -> list[str]:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    palavras = []
    for p in re.findall(r"[a-z0-9]+", sem_acento):
        if len(p) < 3 or p in STOPWORDS:
            continue
        if len(p) > 4 and p.endswith("s"):  # plural simples: "lacos" e "laco" contam juntos
            p = p[:-1]
        palavras.append(p)
    return palavras


def _tfidf(documentos: list[list[str]]) -> tuple[np.ndarray, list[str]]:
    vocabulario = sorted({p for d in documentos for p in d})
    indice = {p: i for i, p in enumerate(vocabulario)}
    matriz = np.zeros((len(documentos), len(vocabulario)))
    for linha, palavras in enumerate(documentos):
        for p in palavras:
            matriz[linha, indice[p]] += 1
    frequencia_doc = (matriz > 0).sum(axis=0)
    matriz *= np.log((1 + len(documentos)) / (1 + frequencia_doc)) + 1
    normas = np.linalg.norm(matriz, axis=1, keepdims=True)
    normas[normas == 0] = 1
    return matriz / normas, vocabulario


def agrupar_duvidas(perguntas: list[dict], limiar: float = 0.3, max_exemplos: int = 3) -> list[dict]:
    """Agrupa perguntas parecidas. `perguntas`: [{"pergunta", "usuario_id"}] em ordem fixa.

    Agrupamento guloso e determinístico: cada pergunta entra no tema mais parecido
    (cosseno com o centro do tema >= limiar) ou abre um tema novo.
    """
    textos = [(p, _palavras(p["pergunta"])) for p in perguntas]
    textos = [(p, palavras) for p, palavras in textos if palavras]
    if not textos:
        return []
    vetores, vocabulario = _tfidf([palavras for _, palavras in textos])
    grupos: list[dict] = []
    for (pergunta, _), vetor in zip(textos, vetores):
        melhor, similaridade = None, limiar
        for grupo in grupos:
            centro = grupo["soma"] / (np.linalg.norm(grupo["soma"]) or 1)
            valor = float(centro @ vetor)
            if valor >= similaridade:
                melhor, similaridade = grupo, valor
        if melhor is None:
            melhor = {"soma": np.zeros_like(vetor), "perguntas": []}
            grupos.append(melhor)
        melhor["soma"] += vetor
        melhor["perguntas"].append(pergunta)

    temas = []
    for grupo in grupos:
        alunos = {p["usuario_id"] for p in grupo["perguntas"]}
        principais = [vocabulario[i] for i in np.argsort(-grupo["soma"], kind="stable")[:3] if grupo["soma"][i] > 0]
        exemplos = []
        if len(alunos) >= 2:  # exemplo de pergunta só quando o tema não aponta para um aluno só
            for p in grupo["perguntas"]:
                texto = p["pergunta"].strip()
                if texto not in exemplos:
                    exemplos.append(texto[:200])
                if len(exemplos) == max_exemplos:
                    break
        temas.append({"tema": ", ".join(principais), "perguntas": len(grupo["perguntas"]), "alunos": len(alunos),
                      "exemplos": exemplos})
    temas.sort(key=lambda t: (-t["alunos"], -t["perguntas"], t["tema"]))
    return temas


def temas_das_duvidas(disciplina_id: int) -> dict:
    perguntas = db.consultar(
        """SELECT p.pergunta, p.usuario_id FROM perguntas p JOIN usuarios u ON u.id = p.usuario_id
           WHERE p.disciplina_id = ? AND u.tipo = 'aluno' ORDER BY p.criado_em DESC, p.id DESC LIMIT 500""",
        (disciplina_id,),
    )
    return {"total_perguntas": len(perguntas), "temas": agrupar_duvidas(perguntas)[:20]}


# ---------------------------------------------------------------- o que reforçar

def o_que_reforcar(disciplina_id: int) -> list[dict]:
    """Aulas em ordem de prioridade: erro médio nos simulados (60%) e volume de dúvidas
    que usaram a aula como fonte (40%). Aula sem simulado conta erro médio de 50%."""
    aulas = db.consultar(
        """SELECT doc.arquivo,
                  (SELECT COUNT(*) FROM resultados_simulado r JOIN usuarios u ON u.id = r.usuario_id
                    WHERE r.disciplina_id = doc.disciplina_id AND r.arquivo = doc.arquivo AND u.tipo = 'aluno')
                    AS simulados,
                  (SELECT SUM(r.acertos) * 1.0 / NULLIF(SUM(r.total), 0) FROM resultados_simulado r
                    JOIN usuarios u ON u.id = r.usuario_id
                    WHERE r.disciplina_id = doc.disciplina_id AND r.arquivo = doc.arquivo AND u.tipo = 'aluno')
                    AS acerto,
                  (SELECT COUNT(*) FROM perguntas p JOIN usuarios u ON u.id = p.usuario_id
                    WHERE p.disciplina_id = doc.disciplina_id AND u.tipo = 'aluno'
                      AND EXISTS (SELECT 1 FROM json_each(p.fontes_arquivos) WHERE value = doc.arquivo))
                    AS duvidas,
                  (SELECT COUNT(*) FROM aulas_concluidas c WHERE c.documento_id = doc.id) AS estudaram
           FROM documentos doc WHERE doc.disciplina_id = ? AND doc.status = 'pronto'""",
        (disciplina_id,),
    )
    mais_duvidas = max((a["duvidas"] for a in aulas), default=0) or 1
    ranking = []
    for a in aulas:
        erro = 1 - a["acerto"] if a["acerto"] is not None else 0.5
        motivos = []
        if a["acerto"] is not None:
            motivos.append(f"acerto médio de {round(100 * a['acerto'])}% em {a['simulados']} simulado(s)")
        else:
            motivos.append("nenhum simulado feito")
        motivos.append(f"{a['duvidas']} dúvida(s) no assistente")
        ranking.append({
            "arquivo": a["arquivo"], "simulados": a["simulados"],
            "acerto": round(100 * a["acerto"]) if a["acerto"] is not None else None,
            "duvidas": a["duvidas"], "estudaram": a["estudaram"],
            "prioridade": round(0.6 * erro + 0.4 * a["duvidas"] / mais_duvidas, 3),
            "motivo": "; ".join(motivos),
        })
    ranking.sort(key=lambda r: (-r["prioridade"], r["arquivo"]))
    return ranking


# ---------------------------------------------------------------- CSV de notas

def _celula(valor) -> str:
    texto = "" if valor is None else str(valor)
    # Planilhas executam células que começam com estes caracteres como fórmula
    if texto[:1] in ("=", "+", "-", "@", "\t", "\r"):
        texto = "'" + texto
    return texto


def notas_csv(disciplina_id: int) -> str:
    linhas = db.consultar(
        """SELECT u.nome AS aluno, r.arquivo, r.acertos, r.total, r.criado_em
           FROM resultados_simulado r JOIN usuarios u ON u.id = r.usuario_id
           WHERE r.disciplina_id = ? AND u.tipo = 'aluno' ORDER BY u.nome, r.criado_em""",
        (disciplina_id,),
    )
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(["Aluno", "Material", "Acertos", "Total", "Percentual", "Data (UTC)"])
    for l in linhas:
        percentual = f"{100 * l['acertos'] / l['total']:.0f}%" if l["total"] else ""
        escritor.writerow([_celula(l["aluno"]), _celula(l["arquivo"]), l["acertos"], l["total"], percentual,
                           l["criado_em"]])
    return "﻿" + saida.getvalue()
