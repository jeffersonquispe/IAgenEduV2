# eval/retrievers.py
"""
Recuperadores comparables para evaluar el RAG sobre el corpus local (data/*.json).

Cada recuperador recibe (query, grado, area, k, usar_meta) y devuelve una lista ordenada de doc_id
("<fuente>:<chunk_id>"). Estrategias:
  - baseline:        la logica actual de produccion (rag_service._buscar_contexto_local)
  - bm25:            BM25 con normalizacion de acentos y stopwords
  - bm25_grafo:      bm25 + expansion por vecinos en un grafo generico de keywords compartidas
  - bm25_meta:       bm25 + filtro duro por area / grado / ciclo (metadatos del Programa Curricular)
  - bm25_meta_grafo: bm25_meta + expansion por un grafo curricular tipado (los vecinos compiten por rango)
  - servicio:        el RAGEducativoService real (recuperacion estructurada + contexto complementario)
  - servicio_con_competencia: igual, pasando la competencia elegida en el wizard (busqueda exacta)
`usar_meta=False` desactiva el filtrado cuando el area/grado no se conocen (consultas libres).
"""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from ..core import rag_service as rs
from ..core.retrieval_estructurado import BM25, CICLO_DE_GRADO, _clave, norm as _norm, pasa_filtro as _pasa_filtro

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

FUENTES = {
    "curriculo": rs._CURRICULO_JSON,
    "orientaciones": rs._ORIENTACIONES_JSON,
    "ses2": rs._SESION_EF_EPT_JSON,
    "ses3": rs._SESION_3_EVAL_JSON,
    "modulo1": rs._ENFOQUE_MODULO1_JSON,
    "metodologias": rs._METODOLOGIAS_ACTIVAS_2026_JSON,
    # Programa Curricular completo transcrito del PDF (scripts/ingesta/); aun no esta en rag_service
    "programa": "data/programa_curricular_secundaria_2016.json",
}
# top_k por fuente que usa produccion en buscar_contexto_curricular ("programa": supuesto para la evaluacion)
TOP_K_PRODUCCION = {"curriculo": 8, "orientaciones": 6, "ses2": 5, "ses3": 5, "modulo1": 5, "metodologias": 6,
                    "programa": 8}


def cargar_corpus() -> Tuple[List[dict], Dict[str, dict]]:
    """Devuelve (chunks, datos_por_fuente). Cada chunk: doc_id, fuente, section, text, keywords + metadatos."""
    chunks, data = [], {}
    for fuente, rel in FUENTES.items():
        path = DATA_DIR / Path(rel).name
        d = json.loads(path.read_text(encoding="utf-8"))
        data[fuente] = d
        for ch in d.get("chunks", []):
            chunks.append({
                "doc_id": f"{fuente}:{ch['id']}",
                "fuente": fuente,
                "section": ch.get("section", ""),
                "text": ch.get("text", ""),
                "keywords": ch.get("keywords", []),
                # metadatos estructurados (solo el corpus del Programa Curricular los trae)
                "tipo": ch.get("tipo"), "area": ch.get("area"), "competencia": ch.get("competencia"),
                "ciclo": ch.get("ciclo"), "grado": ch.get("grado"),
            })
    assert len({c["doc_id"] for c in chunks}) == len(chunks), "doc_id duplicado en el corpus"
    return chunks, data


# --------------------------------------------------------------------------- baseline
def make_baseline(chunks: List[dict], data: Dict[str, dict], programa_primero: bool = False) -> Callable:
    """Replica buscar_contexto_curricular en modo fallback local (sin Bedrock).
    programa_primero: itera el corpus nuevo antes que los demas; los puntajes se recortan a 1.0 y los empates se
    resuelven por orden de fuente, asi que el orden puede cambiar mucho el resultado."""
    orden = ["programa"] + [f for f in TOP_K_PRODUCCION if f != "programa"] if programa_primero else list(TOP_K_PRODUCCION)
    por_contenido = {f"[{c['section']}]\n{c['text']}": c["doc_id"] for c in chunks}

    def retrieve(query: str, grado: int, area: str, k: int = 10, usar_meta: bool = True) -> List[str]:
        todos = []
        for fuente in orden:
            top_k = TOP_K_PRODUCCION[fuente]
            todos.extend(rs._buscar_contexto_local(query, grado, area, data[fuente], top_k=top_k))
        todos.sort(key=lambda d: d.get("score", 0), reverse=True)
        return [por_contenido[d["contenido"]] for d in todos[:k]]

    return retrieve


# --------------------------------------------------------------------------- BM25
def make_bm25(chunks: List[dict]) -> Callable:
    bm = BM25(chunks)
    ids = [c["doc_id"] for c in chunks]

    def retrieve(query: str, grado: int, area: str, k: int = 10, usar_meta: bool = True) -> List[str]:
        sc = bm.scores(query)
        orden = sorted(range(len(sc)), key=lambda i: -sc[i])
        return [ids[i] for i in orden[:k] if sc[i] > 0]

    return retrieve


# --------------------------------------------------------------------------- grafo generico de keywords
def _construir_grafo(chunks: List[dict]) -> Dict[int, Dict[int, float]]:
    """Aristas: adyacencia dentro de la misma fuente (0.3) y Jaccard de keywords normalizadas."""
    kws = [set(_norm(k) for k in c["keywords"]) for c in chunks]
    g: Dict[int, Dict[int, float]] = defaultdict(dict)
    for i, ci in enumerate(chunks):
        for j in range(i + 1, len(chunks)):
            w = 0.0
            if ci["fuente"] == chunks[j]["fuente"] and j == i + 1:
                w = 0.3
            inter = kws[i] & kws[j]
            if inter:
                w = max(w, len(inter) / len(kws[i] | kws[j]))
            if w > 0:
                g[i][j] = g[j][i] = w
    return g


def make_bm25_grafo(chunks: List[dict], semillas: int = 3, alpha: float = 0.4) -> Callable:
    bm = BM25(chunks)
    ids = [c["doc_id"] for c in chunks]
    g = _construir_grafo(chunks)

    def retrieve(query: str, grado: int, area: str, k: int = 10, usar_meta: bool = True) -> List[str]:
        sc = bm.scores(query)
        mx = max(sc) or 1.0
        norm = [s / mx for s in sc]
        top = sorted(range(len(sc)), key=lambda i: -sc[i])[:semillas]
        final = list(norm)
        for s in top:
            if sc[s] <= 0:
                continue
            for v, w in g[s].items():
                final[v] += alpha * norm[s] * w
        orden = sorted(range(len(final)), key=lambda i: -final[i])
        return [ids[i] for i in orden[:k] if final[i] > 0]

    return retrieve


# --------------------------------------------------------------------------- metadatos + grafo curricular
def area_canonica(area, chunks):
    """Mapea el slug de area que recibe el RAG ('ciencia_y_tecnología') al nombre canonico del corpus."""
    nombres = {_clave(c["area"]): c["area"] for c in chunks if c.get("area")}
    return nombres.get(_clave(area)) if area else None


def _grafo_curricular(chunks):
    """Aristas tipadas 'misma competencia y ciclo': desempenos(grado) -> competencia(ciclo) / estandar(ciclo)."""
    por_comp = defaultdict(list)
    for i, c in enumerate(chunks):
        if c.get("competencia"):
            por_comp[c["competencia"]].append(i)
    g = defaultdict(set)
    for idxs in por_comp.values():
        for i in idxs:
            for j in idxs:
                if i == j:
                    continue
                ci, cj = chunks[i], chunks[j]
                ciclo_i = ci["ciclo"] or CICLO_DE_GRADO.get(ci["grado"])
                ciclo_j = cj["ciclo"] or CICLO_DE_GRADO.get(cj["grado"])
                if ci["tipo"] == "desempenos" and cj["tipo"] in ("competencia", "estandar") and ciclo_i == ciclo_j:
                    g[i].add(j)
    return g


def make_bm25_meta(chunks: List[dict], con_grafo: bool = False, semillas: int = 2, alpha: float = 0.5) -> Callable:
    bm = BM25(chunks)
    ids = [c["doc_id"] for c in chunks]
    grafo = _grafo_curricular(chunks) if con_grafo else {}

    def retrieve(query: str, grado: int, area: str, k: int = 10, usar_meta: bool = True) -> List[str]:
        sc = bm.scores(query)
        area_can = area_canonica(area, chunks) if usar_meta else None
        if usar_meta:
            sc = [s if _pasa_filtro(c, grado, area_can) else 0.0 for s, c in zip(sc, chunks)]
        mx = max(sc) or 1.0
        norm = [s / mx for s in sc]
        final = list(norm)
        if con_grafo and usar_meta:
            sem = [i for i in sorted(range(len(sc)), key=lambda i: -sc[i])[:semillas * 3]
                   if chunks[i]["tipo"] == "desempenos"][:semillas]
            for s_ in sem:
                for v in grafo.get(s_, ()):
                    if _pasa_filtro(chunks[v], grado, area_can):
                        final[v] += alpha * norm[s_]
        orden = sorted(range(len(final)), key=lambda i: -final[i])
        return [ids[i] for i in orden[:k] if final[i] > 0]

    return retrieve


def make_servicio(con_competencia: bool = False) -> Callable:
    """Evalua el RAGEducativoService REAL (Bedrock KB sin configurar => recuperacion estructurada + JSON locales).
    Con area/grado desconocidos (consultas libres de pedagogia) se mide solo el contexto complementario.
    con_competencia: ademas pasa la competencia elegida (lo que hace el wizard) -> busqueda exacta."""
    servicio = rs.RAGEducativoService()
    por_contenido = {f"[{c['section']}]\n{c['text']}": c["doc_id"] for c in cargar_corpus()[0]}

    def retrieve(query: str, grado: int, area: str, k: int = 10, usar_meta: bool = True, competencia: str = None) -> List[str]:
        if usar_meta:
            res = servicio.buscar_contexto_curricular(query, grado, area, competencia if con_competencia else None)
        else:
            res = servicio._buscar_contexto_complementario(query, grado, area)
        ids = []
        for d in res["documentos"]:
            cid = (d.get("metadata") or {}).get("chunk_id")
            ids.append(f"programa:{cid}" if (d.get("metadata") or {}).get("recuperacion") == "estructurada"
                       else por_contenido.get(d["contenido"], "?"))
        return ids[:k]

    retrieve.acepta_competencia = True
    return retrieve


def construir_recuperadores() -> Dict[str, Callable]:
    chunks, data = cargar_corpus()
    return {
        "baseline": make_baseline(chunks, data),
        "baseline_prog1o": make_baseline(chunks, data, programa_primero=True),
        "bm25": make_bm25(chunks),
        "bm25_grafo": make_bm25_grafo(chunks),
        "bm25_meta": make_bm25_meta(chunks),
        "bm25_meta_grafo": make_bm25_meta(chunks, con_grafo=True),
        "servicio": make_servicio(),
        "servicio_con_competencia": make_servicio(con_competencia=True),
    }
