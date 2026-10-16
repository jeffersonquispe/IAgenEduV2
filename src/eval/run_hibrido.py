# eval/run_hibrido.py
"""
Experimento hibrido: ¿mejoran los embeddings (solos o fusionados con BM25) la recuperacion actual?

Parte A (curricular, 68 consultas): ordenan los desempenos candidatos del area y grado (el filtro por metadatos se mantiene)
                                    y, como control, el corpus completo SIN filtro.
Parte B (pedagogia, 19 consultas libres): contexto complementario.

Uso (desde la raiz del repo):  python -m src.eval.run_hibrido
Cuesta centavos la primera vez (embeddings de ~800 chunks por modelo); luego usa el cache en disco.
"""
import json
import random
import statistics
from pathlib import Path

import numpy as np

from .embeddings import MODELOS, Embedder
from .metrics import evaluar
from .retrievers import cargar_corpus
from .retrievers_emb import ALFA, ComplementarioHibrido, RecuperadorHibrido, tema_de
from .run_retrieval_eval import cargar_oro, errores_graves

SALIDA = Path(__file__).parent / "resultados"
FECHA = "2026-10-15"
MODOS = ("denso", "rrf", "ponderado")
SUPERADOS = {"curriculo:ciclo_vi", "curriculo:ciclo_vii"}   # y curriculo:area_*  (los reemplaza el Programa Curricular)


def texto_chunk(c):
    return f"{c['section']}\n{c['text']}"


def ic_por_tema(difs_por_id, n=10000, seed=7):
    """Bootstrap sobre los 34 TEMAS: cada tema aporta dos consultas (formato del pipeline y solo el tema) que no son independientes."""
    grupos = {}
    for i, d in difs_por_id.items():
        grupos.setdefault(i[1:], []).append(d)
    medias = [statistics.mean(v) for v in grupos.values()]
    rng = random.Random(seed)
    ms = sorted(statistics.mean(rng.choices(medias, k=len(medias))) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def auc(positivos, negativos):
    """P(un positivo puntua mas que un negativo); 0.5 = no separa."""
    return statistics.mean((1.0 if p > n else 0.5 if p == n else 0.0) for p in positivos for n in negativos)


def main():
    chunks, _ = cargar_corpus()
    meta = {c["doc_id"]: c for c in chunks}
    prog = [c for c in chunks if c["fuente"] == "programa"]
    comp = [c for c in chunks if c["fuente"] != "programa" and c["doc_id"] not in SUPERADOS and not c["doc_id"].startswith("curriculo:area_")]
    oro = cargar_oro()
    estr = [q for q in oro if q["set"] == "estructurado"]
    ped = [q for q in oro if q["set"] == "pedagogia"]
    print(f"corpus estructurado: {len(prog)} chunks | complementario: {len(comp)} chunks | consultas: {len(estr)} curriculares, {len(ped)} libres")

    filas = {}      # estrategia -> lista de dicts por consulta
    costos = {}
    separabilidad = {}

    def ev_estr(nombre, fn, con_graves=False):
        out = []
        for q in estr:
            ranked = fn(q)
            m = evaluar(ranked, q["relevantes"])
            if con_graves:
                m.update(errores_graves(ranked, meta, q))
            out.append({"id": q["id"], "tipo": q["tipo"], "ranked": ranked, **m})
        filas[nombre] = out

    def ev_ped(nombre, fn):
        filas[nombre] = [{"id": q["id"], "ranked": (r := fn(q)), **evaluar(r, q["relevantes"])} for q in ped]

    # ---- referencia: BM25 actual (no usa vectores)
    base = RecuperadorHibrido(prog, np.zeros((len(prog), 1)), None, "bm25")
    est = lambda rec: (lambda q: [c["doc_id"] for c in rec.recuperar(q["query"], q["grado"], q["area"], None, k=5, m=4, con_resto=False)])
    ev_estr("estr_bm25", est(base))
    # control: el BM25 actual con la consulta SIN el prefijo de plantilla (los vectores reciben solo el tema)
    ev_estr("estr_bm25_tema", lambda q: [c["doc_id"] for c in base.recuperar(tema_de(q["query"]), q["grado"], q["area"], None, k=5, m=4, con_resto=False)])
    ev_estr("sinfiltro_bm25", lambda q: [c["doc_id"] for c in base.sin_filtro(q["query"])], con_graves=True)
    ev_ped("ped_bm25", lambda q: ComplementarioHibrido(comp, np.zeros((len(comp), 1)), None, "bm25").recuperar(q["query"]))

    for clave in MODELOS:
        emb = Embedder(clave)
        M_prog = emb.embed_documentos([texto_chunk(c) for c in prog])
        M_comp = emb.embed_documentos([texto_chunk(c) for c in comp])
        for modo in MODOS:
            rec = RecuperadorHibrido(prog, M_prog, emb, modo)
            ev_estr(f"estr_{modo}_{clave}", est(rec))
            ev_estr(f"sinfiltro_{modo}_{clave}", lambda q, r=rec: [c["doc_id"] for c in r.sin_filtro(q["query"])], con_graves=True)
            ch = ComplementarioHibrido(comp, M_comp, emb, modo)
            ev_ped(f"ped_{modo}_{clave}", lambda q, c=ch: c.recuperar(q["query"]))
        for alfa, etq in ((0.25, "a25"), (0.75, "a75")):       # sensibilidad (secundaria): el parametro principal es 0.5
            rec = RecuperadorHibrido(prog, M_prog, emb, "ponderado", alfa)
            ev_estr(f"estr_ponderado_{etq}_{clave}", est(rec))
        # ¿se pueden separar las consultas con contenido pedagogico de las que no lo tienen? (similitud maxima con el contexto de apoyo)
        sim_top = lambda textos: [float((M_comp @ emb.embed([tema_de(t)], "query")[0]).max()) for t in textos]
        con = sim_top([q["query"] for q in ped])
        sin = sim_top([q["query"] for q in estr if q["tipo"] == "tema_solo"])
        separabilidad[clave] = {"auc": round(auc(con, sin), 3), "con_contenido_min": round(min(con), 3), "con_contenido_media": round(statistics.mean(con), 3),
                                "sin_contenido_media": round(statistics.mean(sin), 3), "sin_contenido_max": round(max(sin), 3)}
        costos[clave] = round(emb.costo_estimado(), 4)
        print(f"modelo {clave}: listo (costo de esta ejecucion ≈ US${costos[clave]})")

    # ------------------------------------------------------------------ resumen
    def media(nombre, sel, met):
        v = [f[met] for f in filas[nombre] if sel(f) and f.get(met) is not None]
        return statistics.mean(v) if v else None

    L = [f"Experimento híbrido ({FECHA}). Modelos: {', '.join(MODELOS)}. α = {ALFA}, RRF k = 60 (fijados antes de medir).\n"]
    todas = lambda f: True
    pipe = lambda f: f["tipo"] == "estructurado"
    tema = lambda f: f["tipo"] == "tema_solo"
    L.append("== A. Curricular: ordenar los desempeños candidatos (filtro por área y grado activo). hit_obj@1 / mrr_obj; n=34 + 34 ==")
    L.append(f"{'estrategia':<34}{'todas h@1':>10}{'mrr':>7}{'pipeline h@1':>14}{'solo tema h@1':>15}")
    for n in filas:
        if n.startswith("estr_"):
            L.append(f"{n:<34}{media(n, todas, 'hit_obj@1'):>10.3f}{media(n, todas, 'mrr_obj'):>7.3f}{media(n, pipe, 'hit_obj@1'):>14.3f}{media(n, tema, 'hit_obj@1'):>15.3f}")
    L.append("\n== A'. Control SIN filtro de metadatos: ¿los embeddings evitan el desempeño de otro grado? (top-5) ==")
    L.append(f"{'estrategia':<34}{'hit_obj@1':>10}{'grado equivocado':>18}{'área equivocada':>17}")
    for n in filas:
        if n.startswith("sinfiltro_"):
            L.append(f"{n:<34}{media(n, todas, 'hit_obj@1'):>10.3f}{media(n, todas, 'grado_mal@5'):>18.3f}{media(n, todas, 'area_mal@5'):>17.3f}")
    L.append("\n== B. Pedagogía (19 consultas libres) ==")
    L.append(f"{'estrategia':<34}{'hit@5':>8}{'recall@5':>10}{'mrr':>7}{'ndcg@5':>8}")
    for n in filas:
        if n.startswith("ped_"):
            L.append(f"{n:<34}{media(n, todas, 'hit@5'):>8.3f}{media(n, todas, 'recall@5'):>10.3f}{media(n, todas, 'mrr'):>7.3f}{media(n, todas, 'ndcg@5'):>8.3f}")

    L.append("\n== Diferencias pareadas frente a estr_bm25 (68 consultas; IC 95 % bootstrap sobre los 34 temas) ==")
    L.append(f"{'estrategia':<34}{'Δ hit_obj@1':>12}{'IC':>20}{'mejoran/empeoran':>18}{'Δ mrr_obj':>11}{'IC':>20}")
    ref = {f["id"]: f for f in filas["estr_bm25"]}
    for n in filas:
        if not n.startswith("estr_") or n == "estr_bm25":
            continue
        d1 = [f["hit_obj@1"] - ref[f["id"]]["hit_obj@1"] for f in filas[n]]
        d2 = [f["mrr_obj"] - ref[f["id"]]["mrr_obj"] for f in filas[n]]
        (a1, b1) = ic_por_tema({f["id"]: f["hit_obj@1"] - ref[f["id"]]["hit_obj@1"] for f in filas[n]})
        (a2, b2) = ic_por_tema({f["id"]: f["mrr_obj"] - ref[f["id"]]["mrr_obj"] for f in filas[n]})
        L.append(f"{n:<34}{statistics.mean(d1):>+12.3f}{f'[{a1:+.2f}, {b1:+.2f}]':>20}{f'{sum(x > 0 for x in d1)}/{sum(x < 0 for x in d1)}':>18}"
                 f"{statistics.mean(d2):>+11.3f}{f'[{a2:+.2f}, {b2:+.2f}]':>20}")
    L.append("\n== C. ¿Se puede descartar el contexto de apoyo cuando la consulta no tiene contenido pedagógico? (similitud máxima, AUC) ==")
    L.append("   con contenido = las 19 consultas libres; sin contenido = los 34 temas curriculares (p. ej. «ecuaciones lineales»)")
    for k, v in separabilidad.items():
        L.append(f"{k:<14} AUC={v['auc']:.3f} | con contenido: min {v['con_contenido_min']:.2f}, media {v['con_contenido_media']:.2f} | sin contenido: media {v['sin_contenido_media']:.2f}, max {v['sin_contenido_max']:.2f}")
    L.append("\n== D. Consultas donde estr_ponderado_titan_v2 NO pone primero el desempeño correcto ==")
    por_id = {q["id"]: q for q in estr}
    for f in filas["estr_ponderado_titan_v2"]:
        if f["hit_obj@1"] < 1:
            q = por_id[f["id"]]
            primero = meta.get(f["ranked"][0], {}) if f["ranked"] else {}
            L.append(f"{f['id']} {q['query'][:70]!r}: esperado «{q['competencia_objetivo'][:42]}», salió «{(primero.get('competencia') or '-')[:42]}»")
    L.append("\nCosto de los embeddings en esta ejecución (USD, estimado; 0 si todo salió del cache): " + json.dumps(costos))
    texto = "\n".join(L)
    print("\n" + texto)
    (SALIDA / f"hibrido_{FECHA}.txt").write_text(texto, encoding="utf-8")
    (SALIDA / f"hibrido_{FECHA}.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
