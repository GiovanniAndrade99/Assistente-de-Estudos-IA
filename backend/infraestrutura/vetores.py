"""Banco vetorial simples feito com NumPy.

Substitui o ChromaDB, que travava no Windows com Python 3.14 (access violation).
A busca é por similaridade de cosseno:

    similaridade(a, b) = (a · b) / (|a| * |b|)

Como os vetores são normalizados ao serem guardados (|v| = 1), basta um
produto escalar entre a pergunta e todos os trechos de uma vez.

Concorrência e falhas (a indexação roda em segundo plano enquanto o chat lê):
- vetores e trechos ficam num "retrato" imutável, trocado inteiro sob uma trava;
  quem está lendo continua com o retrato antigo, sem ver meio-termo;
- tudo vai para um arquivo só (indice.npz), gravado num temporário e trocado com
  os.replace: uma queda no meio da gravação não corrompe o índice;
- `substituir` só tira os trechos antigos de um arquivo quando os novos já estão
  prontos: reenviar um PDF não deixa a disciplina sem material no meio do caminho.
"""
import json
import os
import threading
from pathlib import Path

import numpy as np


def _normalizar(vetores) -> np.ndarray:
    novos = np.asarray(vetores, dtype=np.float32)
    if novos.size == 0:
        return np.empty((0, 0), dtype=np.float32)
    return novos / np.linalg.norm(novos, axis=1, keepdims=True)


class BancoVetorial:
    def __init__(self, pasta: Path):
        pasta.mkdir(parents=True, exist_ok=True)
        self._arquivo = pasta / "indice.npz"
        self._trava = threading.Lock()
        self._retrato = self._carregar(pasta)  # (vetores, trechos): sempre trocados juntos

    def _carregar(self, pasta: Path) -> tuple[np.ndarray, list[dict]]:
        if self._arquivo.exists():
            with np.load(self._arquivo, allow_pickle=False) as dados:
                return dados["vetores"], json.loads(dados["trechos"].tobytes().decode("utf-8"))
        # Formato antigo: dois arquivos (vetores.npy + trechos.json)
        antigo_vetores, antigo_trechos = pasta / "vetores.npy", pasta / "trechos.json"
        if antigo_vetores.exists() and antigo_trechos.exists():
            return np.load(antigo_vetores), json.loads(antigo_trechos.read_text(encoding="utf-8"))
        return np.empty((0, 0), dtype=np.float32), []

    def __len__(self) -> int:
        return len(self._retrato[1])

    def _salvar(self, vetores: np.ndarray, trechos: list[dict]) -> None:
        temporario = self._arquivo.with_name("indice.tmp")
        bytes_trechos = np.frombuffer(json.dumps(trechos, ensure_ascii=False).encode("utf-8"), dtype=np.uint8)
        with open(temporario, "wb") as arquivo:
            np.savez(arquivo, vetores=vetores, trechos=bytes_trechos)
        os.replace(temporario, self._arquivo)
        for antigo in ("vetores.npy", "trechos.json"):  # formato antigo, já migrado
            self._arquivo.with_name(antigo).unlink(missing_ok=True)

    def _trocar(self, manter, novos_vetores=None, novos_trechos=None) -> None:
        """Monta o novo retrato (trechos mantidos + novos), grava e troca. Chamar com a trava."""
        vetores_atuais, trechos_atuais = self._retrato
        vetores = vetores_atuais[manter] if manter else np.empty((0, 0), dtype=np.float32)
        trechos = [trechos_atuais[i] for i in manter]
        if novos_trechos:
            novos = _normalizar(novos_vetores)
            vetores = novos if len(trechos) == 0 else np.vstack([vetores, novos])
            trechos = trechos + list(novos_trechos)
        self._salvar(vetores, trechos)
        self._retrato = (vetores, trechos)

    def adicionar(self, vetores: list[list[float]], trechos: list[dict]) -> None:
        with self._trava:
            self._trocar(list(range(len(self))), vetores, trechos)

    def substituir(self, disciplina_id: int, arquivo: str, vetores: list[list[float]], trechos: list[dict]) -> None:
        """Troca de uma vez os trechos de um arquivo da disciplina pelos novos."""
        with self._trava:
            manter = [i for i, t in enumerate(self._retrato[1])
                      if not (t["disciplina_id"] == disciplina_id and t["arquivo"] == arquivo)]
            self._trocar(manter, vetores, trechos)

    def remover(self, disciplina_id: int, arquivo: str | None = None) -> None:
        """Remove os trechos de um arquivo da disciplina (ou da disciplina inteira)."""
        with self._trava:
            manter = [i for i, t in enumerate(self._retrato[1])
                      if not (t["disciplina_id"] == disciplina_id and arquivo in (None, t["arquivo"]))]
            if len(manter) != len(self):
                self._trocar(manter)

    def tem_trechos(self, disciplina_id: int, arquivo: str) -> bool:
        trechos = self._retrato[1]
        return any(t["disciplina_id"] == disciplina_id and t["arquivo"] == arquivo for t in trechos)

    def buscar(self, vetor: list[float], k: int, disciplina_id: int) -> list[dict]:
        """Retorna os k trechos da disciplina mais parecidos, com a similaridade de cosseno."""
        vetores, trechos = self._retrato  # retrato estável durante a busca
        indices = [i for i, t in enumerate(trechos) if t["disciplina_id"] == disciplina_id]
        if not indices:
            return []
        consulta = np.asarray(vetor, dtype=np.float32)
        consulta /= np.linalg.norm(consulta)
        similaridades = vetores[indices] @ consulta
        melhores = np.argsort(-similaridades)[:k]
        return [
            {**trechos[indices[i]], "similaridade": round(float(similaridades[i]), 3)}
            for i in melhores
        ]
