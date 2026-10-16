# eval/retrievers_emb.py
"""
Recuperadores hibridos (BM25 + embeddings) para el experimento. Reutilizan RecuperadorCurricular: solo cambia el
puntaje con el que se ordenan los candidatos (gancho `_puntajes`); el filtrado por area/grado/competencia es el de produccion.

Modos de puntaje (parametros FIJADOS antes de medir; ver docs/EXPERIMENTO_HIBRIDO.md):
  bm25       el actual
  denso      similitud coseno consulta-chunk
  rrf        Reciprocal Rank Fusion, k=60, rangos sobre todo el corpus (empates comparten rango)
  ponderado  0.5 * BM25/max + 0.5 * coseno normalizado min-max, normalizado sobre todo el corpus
"""
import re
from typing import List

import numpy as np

from ..core.retrieval_estructurado import BM25, RecuperadorCurricular, tokens

RRF_K = 60
ALFA = 0.5
_PREFIJO = re.compile(r"^\s*programación curricular\s+.+?\s+[1-5]\s+grado\s+secundaria\s*(.*)$", re.I | re.S)
GENERICAS = {"programacion", "curricular", "grado", "secundaria"}


def tema_de(query: str) -> str:
    """El prefijo 'programación curricular {área} {grado} grado secundaria' es de plantilla: para los vectores se usa solo el tema."""
    m = _PREFIJO.match(query)
    return (m.group(1).strip() or query) if m else query


def rangos(x: np.ndarray) -> np.ndarray:
    """Rango 1 = mejor; los empates comparten rango (los chunks con puntaje BM25 0 no se ordenan entre si)."""
    return 1 + (x[None, :] > x[:, None]).sum(axis=1)


def fusionar(modo: str, bm: np.ndarray, cos: np.ndarray, alfa: float = ALFA) -> np.ndarray:
    if modo == "bm25":
        return bm
    if modo == "denso":
        return cos
    if modo == "rrf":
        return 1.0 / (RRF_K + rangos(bm)) + 1.0 / (RRF_K + rangos(cos))
    if modo == "ponderado":
        nb = bm / bm.max() if bm.max() > 0 else bm
        rng = cos.max() - cos.min()
        nc = (cos - cos.min()) / rng if rng > 0 else cos * 0
        return alfa * nb + (1 - alfa) * nc
    raise ValueError(modo)


class RecuperadorHibrido(RecuperadorCurricular):
    def __init__(self, chunks, matriz: np.ndarray, embedder, modo: str, alfa: float = ALFA):
        super().__init__(chunks)
        self.matriz, self.emb, self.modo, self.alfa = matriz, embedder, modo, alfa

    def _puntajes(self, query: str):
        bm = np.asarray(super()._puntajes(query), dtype=float)
        if self.modo == "bm25":
            return bm
        q = self.emb.embed([tema_de(query)], "query")[0]
        return fusionar(self.modo, bm, self.matriz @ q, self.alfa)

    def sin_filtro(self, query: str, k: int = 5):
        """Control: ordena TODO el corpus por el puntaje, sin filtrar por area ni grado."""
        sc = self._puntajes(query)
        return [self.chunks[i] for i in np.argsort(-np.asarray(sc), kind="stable")[:k]]


class ComplementarioHibrido:
    """Contexto pedagogico: BM25 / vectores / fusion sobre los chunks de apoyo (sin los resumenes que el corpus reemplaza)."""

    def __init__(self, chunks: List[dict], matriz: np.ndarray, embedder, modo: str, alfa: float = ALFA):
        self.chunks, self.matriz, self.emb, self.modo, self.alfa = chunks, matriz, embedder, modo, alfa
        self.bm = BM25(chunks)

    def recuperar(self, query: str, k: int = 10) -> List[str]:
        limpia = " ".join(t for t in tokens(query) if t not in GENERICAS)
        bm = np.asarray(self.bm.scores(limpia), dtype=float)
        if self.modo == "bm25":
            sc = bm
        else:
            q = self.emb.embed([tema_de(query)], "query")[0]
            sc = fusionar(self.modo, bm, self.matriz @ q, self.alfa)
        orden = np.argsort(-sc, kind="stable")[:k]
        # como en produccion, con BM25 puro no se devuelve lo que no comparte palabras; con vectores siempre hay vecinos
        return [self.chunks[i]["doc_id"] for i in orden if (self.modo != "bm25" or sc[i] > 0)]
