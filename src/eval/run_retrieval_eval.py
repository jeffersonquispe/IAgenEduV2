# eval/run_retrieval_eval.py
"""
Evalua recuperadores contra los sets de oro.

  gold_retrieval.json        pedagogia / metodologia (relevancia etiquetada a mano, 25 consultas)
  gold_estructurado.json     programacion curricular (relevancia derivada de metadatos, 68 consultas)

Uso (desde la raiz del repo):
    python -m src.eval.run_retrieval_eval                    # tablas resumen
    python -m src.eval.run_retrieval_eval --verbose          # + fallas por consulta
    python -m src.eval.run_retrieval_eval --json out.json
"""
import argparse
import json
import re
import statistics
import time
from pathlib import Path

from .metrics import evaluar
from .retrievers import cargar_corpus, construir_recuperadores

AQUI = Path(__file__).parent
COLS = ["hit@5", "recall@5", "precision@5", "mrr", "ndcg@5", "recall@10", "ndcg@10"]
COLS_OBJ = ["hit_obj@1", "hit_obj@3", "hit_obj@5", "mrr_obj"]
COLS_ERR = ["grado_mal@5", "area_mal@5"]


def _parse_pipeline(query: str):
    """Consultas libres de gold_retrieval.json: se asume el default que usa el RAG cuando no hay datos."""
    m = re.search(r"programación curricular (.+?) (\d) grado", query)
    if m:
        return int(m.group(2)), m.group(1).replace(" ", "_").lower()
    return 3, "ciencia_tecnologia"


def cargar_oro():
    """Devuelve lista de dicts con: id, tipo, set, query, grado, area, usar_meta, relevantes, y meta esperada."""
    out = []
    for q in json.loads((AQUI / "gold_retrieval.json").read_text(encoding="utf-8"))["queries"]:
        grado, area = _parse_pipeline(q["query"])
        # tipo 'pipeline' = area y grado conocidos; 'natural' = consulta libre (sin filtrar por metadatos)
        out.append({**q, "set": "pedagogia", "grado": grado, "area": area, "usar_meta": q["tipo"] == "pipeline",
                    "grado_esperado": None, "area_esperada": None})
    p = AQUI / "gold_estructurado.json"
    if p.exists():
        for q in json.loads(p.read_text(encoding="utf-8"))["queries"]:
            out.append({**q, "set": "estructurado", "area": q["area_slug"], "usar_meta": True,
                        "grado_esperado": q["grado"], "area_esperada": q["area"]})
    return out


def errores_graves(ranked, meta, q, k=5):
    """Entre los k primeros: fraccion de desempenos de OTRO grado y de chunks con area distinta a la pedida."""
    top = [meta[d] for d in ranked[:k]]
    des = [c for c in top if c.get("tipo") == "desempenos"]
    con_area = [c for c in top if c.get("area")]
    return {
        "grado_mal@5": (sum(c["grado"] != q["grado_esperado"] for c in des) / len(des)) if des and q["grado_esperado"] else None,
        "area_mal@5": (sum(c["area"] != q["area_esperada"] for c in con_area) / len(con_area)) if con_area and q["area_esperada"] else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", help="guardar resultados detallados en este archivo")
    args = ap.parse_args()

    oro = cargar_oro()
    chunks, _ = cargar_corpus()
    meta = {c["doc_id"]: c for c in chunks}
    recuperadores = construir_recuperadores()
    detalle = {}

    for nombre, retrieve in recuperadores.items():
        filas, lat = [], []
        for q in oro:
            t0 = time.perf_counter()
            extra = {"competencia": q.get("competencia_objetivo")} if getattr(retrieve, "acepta_competencia", False) else {}
            ranked = retrieve(q["query"], q["grado"], q["area"], k=10, usar_meta=q["usar_meta"], **extra)
            lat.append((time.perf_counter() - t0) * 1000)
            filas.append({"id": q["id"], "set": q["set"], "tipo": q["tipo"], "ranked": ranked,
                          **evaluar(ranked, q["relevantes"]), **errores_graves(ranked, meta, q)})
        detalle[nombre] = {"filas": filas, "latencia_ms": statistics.mean(lat)}

    def media(filas, col, sel):
        v = [f[col] for f in filas if sel(f) and f.get(col) is not None]
        return statistics.mean(v) if v else float("nan")

    grupos = [("PEDAGOGÍA (todas)", lambda f: f["set"] == "pedagogia"),
              ("PEDAGOGÍA · pipeline (área y grado conocidos)", lambda f: f["set"] == "pedagogia" and f["tipo"] == "pipeline"),
              ("PEDAGOGÍA · natural (consulta libre)", lambda f: f["set"] == "pedagogia" and f["tipo"] == "natural"),
              ("ESTRUCTURADO (todas)", lambda f: f["set"] == "estructurado"),
              ("ESTRUCTURADO · formato del pipeline", lambda f: f["tipo"] == "estructurado"),
              ("ESTRUCTURADO · solo el tema", lambda f: f["tipo"] == "tema_solo")]
    for titulo, sel in grupos:
        n = sum(1 for f in next(iter(detalle.values()))["filas"] if sel(f))
        if not n:
            continue
        con_err = "ESTRUCTURADO" in titulo
        cols = (COLS_OBJ + COLS + COLS_ERR) if con_err else COLS
        print(f"\n== {titulo}  (n={n}) ==")
        print(f"{'estrategia':<17}" + "".join(f"{c[:12]:>13}" for c in cols))
        for nombre, d in detalle.items():
            print(f"{nombre:<17}" + "".join(f"{media(d['filas'], c, sel):>13.3f}" for c in cols))
    print("\nlatencia media (ms/consulta): " + ", ".join(f"{n}={d['latencia_ms']:.1f}" for n, d in detalle.items()))

    if args.verbose:
        por_id = {q["id"]: q for q in oro}
        for nombre, d in detalle.items():
            print(f"\n--- fallas {nombre} (recall@5 < 1) ---")
            for f in d["filas"]:
                if f["recall@5"] < 1:
                    q = por_id[f["id"]]
                    faltan = [x.split(":", 1)[1][:48] for x in q["relevantes"] if x not in f["ranked"][:5]]
                    print(f"{f['id']} r@5={f['recall@5']:.2f} faltan={faltan}")

    if args.json:
        Path(args.json).write_text(json.dumps(detalle, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Guardado: {args.json}")


if __name__ == "__main__":
    main()
