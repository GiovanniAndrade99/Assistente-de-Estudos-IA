"""Banco vetorial simples feito com NumPy.

Substitui o ChromaDB, que travava no Windows com Python 3.14 (access violation).
Guarda os vetores em data/indice/vetores.npy e os textos/metadados em
data/indice/trechos.json. A busca é por similaridade de cosseno:

    similaridade(a, b) = (a · b) / (|a| * |b|)

Como os vetores são normalizados ao serem guardados (|v| = 1), basta um
produto escalar entre a pergunta e todos os trechos de uma vez.
"""
import json
from pathlib import Path

import numpy as np


class BancoVetorial:
    def __init__(self, pasta: Path):
        pasta.mkdir(parents=True, exist_ok=True)
        self._arq_vetores = pasta / "vetores.npy"
        self._arq_trechos = pasta / "trechos.json"
        if self._arq_vetores.exists() and self._arq_trechos.exists():
            self._vetores = np.load(self._arq_vetores)
            self._trechos = json.loads(self._arq_trechos.read_text(encoding="utf-8"))
        else:
            self._vetores = np.empty((0, 0), dtype=np.float32)
            self._trechos = []  # [{"texto": ..., "arquivo": ..., "pagina": ...}, ...]

    def __len__(self) -> int:
        return len(self._trechos)

    def _salvar(self) -> None:
        np.save(self._arq_vetores, self._vetores)
        self._arq_trechos.write_text(json.dumps(self._trechos, ensure_ascii=False), encoding="utf-8")

    def adicionar(self, vetores: list[list[float]], trechos: list[dict]) -> None:
        novos = np.asarray(vetores, dtype=np.float32)
        novos /= np.linalg.norm(novos, axis=1, keepdims=True)  # normaliza
        self._vetores = novos if len(self) == 0 else np.vstack([self._vetores, novos])
        self._trechos.extend(trechos)
        self._salvar()

    def remover(self, disciplina_id: int, arquivo: str | None = None) -> None:
        """Remove os trechos de um arquivo da disciplina (ou da disciplina inteira)."""
        def apagar(t: dict) -> bool:
            return t["disciplina_id"] == disciplina_id and arquivo in (None, t["arquivo"])

        manter = [i for i, t in enumerate(self._trechos) if not apagar(t)]
        if len(manter) == len(self._trechos):
            return
        self._trechos = [self._trechos[i] for i in manter]
        self._vetores = self._vetores[manter] if manter else np.empty((0, 0), dtype=np.float32)
        self._salvar()

    def buscar(self, vetor: list[float], k: int, disciplina_id: int) -> list[dict]:
        """Retorna os k trechos da disciplina mais parecidos, com a similaridade de cosseno."""
        indices = [i for i, t in enumerate(self._trechos) if t["disciplina_id"] == disciplina_id]
        if not indices:
            return []
        consulta = np.asarray(vetor, dtype=np.float32)
        consulta /= np.linalg.norm(consulta)
        similaridades = self._vetores[indices] @ consulta
        melhores = np.argsort(-similaridades)[:k]
        return [
            {**self._trechos[indices[i]], "similaridade": round(float(similaridades[i]), 3)}
            for i in melhores
        ]
