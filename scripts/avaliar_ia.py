"""Avalia as respostas do chat (RAG) com o Gemini real, usando só o conteúdo demo.

Monta a disciplina "Algoritmos e Programação" do curso demo numa pasta de dados
TEMPORÁRIA (não toca em data/), indexa os PDFs, faz as perguntas de
avaliacao/conjunto_algoritmos.json e confere cada resposta (avaliacao/metricas.py).
Nenhum dado pessoal vai para o Gemini: só as aulas demo e as perguntas do conjunto.

Uso:
    python -m scripts.avaliar_ia                  # meta de acerto 0.9
    python -m scripts.avaliar_ia --meta 0.85 --intervalo 6 --saida relatorio.json

Sai com código 1 se a taxa de acerto ficar abaixo da meta. Cada caso faz uma busca
(embedding) e uma geração; --intervalo espaça as chamadas para caber na cota por
minuto do nível gratuito.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONJUNTO = RAIZ / "avaliacao" / "conjunto_algoritmos.json"


def _preparar_ambiente() -> Path:
    """Precisa rodar antes de importar o backend: a config lê PASTA_DADOS na importação."""
    pasta = Path(tempfile.mkdtemp(prefix="avaliacao-ia-"))
    os.environ["PASTA_DADOS"] = str(pasta)
    os.environ["DADOS_DEMO"] = "false"
    os.environ.setdefault("APP_ENV", "development")
    return pasta


def _montar_disciplina(conjunto: dict) -> int:
    import pymupdf

    from backend.aplicacao import indexacao_service
    from backend.core.seguranca import gerar_hash_senha, gerar_token_sessao
    from backend.infraestrutura import db, rag
    from scripts.dados_curso_cc import DISCIPLINAS
    from scripts.popular_curso import gerar_pdf, nome_do_arquivo

    db.criar_tabelas()
    professor = db.executar("INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, 'professor')",
                            ("Avaliação", "avaliacao@exemplo.invalid", gerar_hash_senha(gerar_token_sessao())))
    dados = next(d for d in DISCIPLINAS if d["nome"] == conjunto["disciplina"])
    disciplina = db.executar("INSERT INTO disciplinas (nome, criado_por) VALUES (?, ?)", (dados["nome"], professor))

    arquivos = []
    for numero, aula in enumerate(dados["aulas"], start=1):
        nome = nome_do_arquivo(numero, aula["titulo"])
        gerar_pdf(rag.caminho_do_pdf(disciplina, nome), dados, numero, aula)
        arquivos.append(nome)
    extra = conjunto["pdf_com_instrucao"]
    documento = pymupdf.open()
    documento.new_page().insert_textbox(pymupdf.Rect(56, 56, 540, 790), extra["texto"], fontsize=11)
    documento.save(rag.caminho_do_pdf(disciplina, extra["arquivo"]))
    documento.close()
    arquivos.append(extra["arquivo"])

    for nome in arquivos:
        documento_id = db.executar(
            "INSERT INTO documentos (disciplina_id, arquivo, trechos, enviado_por, status, progresso) "
            "VALUES (?, ?, 0, ?, 'processando', 0)", (disciplina, nome, professor))
        indexacao_service.indexar_documento(documento_id)
        situacao = db.consultar_um("SELECT status, erro, alerta_instrucoes FROM documentos WHERE id = ?", (documento_id,))
        print(f"  indexado: {nome} ({situacao['status']}{', alerta de instruções' if situacao['alerta_instrucoes'] else ''})")
        if situacao["status"] != "pronto":
            raise SystemExit(f"falha ao indexar {nome}: {situacao['erro']}")
    return disciplina


def _perguntar(pergunta: str, disciplina: int, tentativas: int = 4) -> dict | None:
    """Resposta do RAG, ou None se o Gemini continuar indisponível (429/5xx) depois das
    tentativas: indisponibilidade da API não conta como erro de qualidade."""
    from google.genai.errors import APIError

    from backend.infraestrutura import rag

    for tentativa in range(tentativas):
        try:
            return rag.responder(pergunta, disciplina)
        except APIError as erro:
            if erro.code != 429 and erro.code < 500:
                raise
            if tentativa < tentativas - 1:
                time.sleep(20 * (tentativa + 1))  # cota por minuto ou sobrecarga: espera e tenta de novo
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--meta", type=float, default=0.9, help="taxa mínima de acerto (padrão 0.9)")
    parser.add_argument("--intervalo", type=float, default=4.0, help="segundos entre perguntas (padrão 4)")
    parser.add_argument("--saida", type=Path, help="grava o relatório completo em JSON")
    parser.add_argument("--manter", action="store_true", help="não apaga a pasta temporária de dados")
    args = parser.parse_args()

    pasta = _preparar_ambiente()
    sys.path.insert(0, str(RAIZ))
    from avaliacao import metricas
    from backend import config, prompts

    if not config.GEMINI_API_KEY:
        print("GEMINI_API_KEY não configurada (.env ou variável de ambiente).")
        return 2
    conjunto = json.loads(CONJUNTO.read_text(encoding="utf-8"))
    try:
        print(f"Montando '{conjunto['disciplina']}' em pasta temporária…")
        disciplina = _montar_disciplina(conjunto)
        resultados, sem_resposta = [], []
        for caso in conjunto["casos"]:
            resultado = _perguntar(caso["pergunta"], disciplina)
            if resultado is None:
                sem_resposta.append(caso["id"])
                print(f"  ---  {caso['id']}: Gemini indisponível, caso fora da conta")
                continue
            avaliado = metricas.avaliar_caso(caso, resultado["resposta"], resultado["fontes"])
            avaliado.update(pergunta=caso["pergunta"], resposta=resultado["resposta"],
                            fontes=[f"{f['arquivo']} p.{f['pagina']}" for f in resultado["fontes"]],
                            modelo=resultado.get("modelo"))
            resultados.append(avaliado)
            print(f"  {'OK ' if avaliado['acertou'] else 'ERRO'} {caso['id']}: {caso['pergunta'][:70]}"
                  + (f"  -> {'; '.join(avaliado['falhas'])}" if avaliado["falhas"] else ""))
            time.sleep(args.intervalo)
    finally:
        if args.manter:
            print("dados em", pasta)
        else:
            shutil.rmtree(pasta, ignore_errors=True)

    resumo = metricas.resumir(resultados)
    resumo.update(modelo=config.GEMINI_MODEL, versao_prompts=prompts.VERSAO_PROMPTS, meta=args.meta,
                  data=time.strftime("%Y-%m-%d"), sem_resposta=sem_resposta)
    print("\nResumo:", json.dumps(resumo, ensure_ascii=False, indent=2))
    if args.saida:
        args.saida.write_text(json.dumps({"resumo": resumo, "resultados": resultados}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    return 0 if resumo["taxa"] >= args.meta else 1


if __name__ == "__main__":
    sys.exit(main())
