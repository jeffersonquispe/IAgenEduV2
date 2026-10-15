# eval/e2e_informe.py
"""
Agrega los resultados de la evaluacion de extremo a extremo y escribe las tablas en
src/eval/resultados/e2e/informe_tablas.md (+ resumen.json).

Comparaciones PAREADAS por caso (los tres documentos de un caso comparten area, grado, tema y competencias). Intervalo de
confianza del 95% por bootstrap sobre los casos (n pequeno: tomar los intervalos como orientativos, no como prueba).

Uso:  python -m src.eval.e2e_informe
"""
import json
import random
import statistics
from pathlib import Path

from .e2e_casos import CASO_POR_ID, CASOS
from .e2e_puntuar import CONDICIONES, SALIDA, Referencia, puntuar_documento

# USD por millon de tokens (Claude Sonnet en Bedrock; verificar contra la tarifa vigente de la cuenta)
PRECIO_ENTRADA, PRECIO_SALIDA = 3.0, 15.0
AUTO = [("solape_grado", "solape léxico con los desempeños oficiales del grado"), ("margen_grado", "margen frente a otros grados"),
        ("grado_primero", "desempeños más cercanos al grado pedido (azar 0.20)"), ("cobertura", "cobertura de lo oficial del grado"),
        ("comp_precision", "competencias nombradas: precisión"), ("comp_recall", "competencias pedidas que aparecen: recall (solo si el docente las eligió)")]
JUEZ = ["competencias", "capacidades", "desempenos_grado", "coherencia", "total"]


def _bootstrap_ic(difs, n=10000, seed=7):
    rng = random.Random(seed)
    medias = sorted(statistics.mean(rng.choices(difs, k=len(difs))) for _ in range(n))
    return medias[int(0.025 * n)], medias[int(0.975 * n)]


def _tabla_pareada(valores, metrica):
    """valores[cond][caso] -> filas de comparacion nuevo vs cada otra condicion."""
    filas = []
    for otra in ("sin_rag", "rag_previo"):
        casos = [c for c in valores["rag_nuevo"] if c in valores[otra]]
        difs = [valores["rag_nuevo"][c] - valores[otra][c] for c in casos]
        lo, hi = _bootstrap_ic(difs)
        mejora = sum(d > 1e-9 for d in difs)
        peor = sum(d < -1e-9 for d in difs)
        filas.append((otra, statistics.mean(difs), lo, hi, mejora, peor, len(casos)))
    return filas


def main():
    ref = Referencia()
    auto, juez, meta = {}, {}, {}
    for c in CASOS:
        for cond in CONDICIONES:
            md = SALIDA / f"{c.id}_{cond}.md"
            if not md.exists():
                continue
            r = puntuar_documento(ref, c, md.read_text(encoding="utf-8"))
            if c.escenario == "sin_comp":      # sin competencias pedidas, elegir un subconjunto del area no es un error
                r.pop("comp_recall")
            auto.setdefault(cond, {})[c.id] = r
            meta.setdefault(cond, {})[c.id] = json.loads((SALIDA / f"{c.id}_{cond}.json").read_text(encoding="utf-8"))
            jf = SALIDA / f"{c.id}_{cond}_juez.json"
            if jf.exists():
                j = json.loads(jf.read_text(encoding="utf-8"))
                juez.setdefault(cond, {})[c.id] = {**j["puntajes"], "total": j["total"]}

    L = ["# Tablas de la evaluación de extremo a extremo (generadas por `python -m src.eval.e2e_informe`)\n"]
    n_casos = len(set(auto.get("rag_nuevo", {})) & set(auto.get("sin_rag", {})) & set(auto.get("rag_previo", {})))
    L.append(f"Casos completos en las tres condiciones: **{n_casos}**.\n")

    def media_por_condicion(titulo, datos, claves):
        L.append(f"### {titulo}\n")
        L.append("| Medida | " + " | ".join(CONDICIONES) + " |")
        L.append("|---|" + "---|" * len(CONDICIONES))
        for clave, desc in claves:
            fila = [f"{statistics.mean(v[clave] for v in datos[c].values() if clave in v):.3f}" if c in datos else "—" for c in CONDICIONES]
            L.append(f"| {desc} (`{clave}`) | " + " | ".join(fila) + " |")
        L.append("")

    def pareadas(titulo, datos, claves):
        L.append(f"### {titulo}: diferencia `rag_nuevo` − otra condición (media pareada, IC 95% bootstrap)\n")
        L.append("| Medida | vs | diferencia | IC 95% | casos que mejoran / empeoran |")
        L.append("|---|---|---|---|---|")
        for clave, _ in claves:
            vals = {c: {k: v[clave] for k, v in datos[c].items() if clave in v} for c in datos}
            for otra, d, lo, hi, mejora, peor, n in _tabla_pareada(vals, clave):
                L.append(f"| `{clave}` | {otra} | {d:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {mejora} / {peor} de {n} |")
        L.append("")

    media_por_condicion("Medidas automáticas contra el Programa Curricular", auto, AUTO)
    pareadas("Medidas automáticas", auto, AUTO)
    if juez:
        jc = [(k, f"juez: {k}") for k in JUEZ]
        media_por_condicion("Juez (0 a 3 por criterio; total 0 a 12)", juez, jc)
        pareadas("Juez", juez, jc)

    L.append("### Por escenario de uso (medidas automáticas: `solape_grado` y `grado_primero`)\n")
    L.append("| Escenario | n | " + " | ".join(f"{c}: solape / grado_primero" for c in CONDICIONES) + " |")
    L.append("|---|---|" + "---|" * len(CONDICIONES))
    for esc in ("1comp", "2comp", "sin_comp"):
        ids = [c.id for c in CASOS if c.escenario == esc and all(c.id in auto.get(k, {}) for k in CONDICIONES)]
        if not ids:
            continue
        cel = [f"{statistics.mean(auto[k][i]['solape_grado'] for i in ids):.2f} / {statistics.mean(auto[k][i]['grado_primero'] for i in ids):.2f}"
               for k in CONDICIONES]
        L.append(f"| {esc} | {len(ids)} | " + " | ".join(cel) + " |")
    L.append("")

    L.append("### Costo, tamaño y tiempo de la generación\n")
    L.append("| Condición | tokens de entrada (media) | tokens de salida (media) | caracteres del prompt (media) | segundos (media) | costo medio por documento | terminó (`end_turn`) |")
    L.append("|---|---|---|---|---|---|---|")
    total = 0.0
    for cond in CONDICIONES:
        ms = list(meta.get(cond, {}).values())
        if not ms:
            continue
        costo = [m["tokens_entrada"] * PRECIO_ENTRADA / 1e6 + m["tokens_salida"] * PRECIO_SALIDA / 1e6 for m in ms]
        total += sum(costo)
        fin = sum(m.get("stop_reason") == "end_turn" for m in ms)
        L.append(f"| {cond} | {statistics.mean(m['tokens_entrada'] for m in ms):.0f} | {statistics.mean(m['tokens_salida'] for m in ms):.0f} | "
                 f"{statistics.mean(m['chars_prompt'] for m in ms):.0f} | {statistics.mean(m['segundos'] for m in ms):.0f} | "
                 f"US${statistics.mean(costo):.3f} | {fin}/{len(ms)} |")
    L.append(f"\nCosto total de generar todos los documentos: **US${total:.2f}** (tarifa asumida: US${PRECIO_ENTRADA}/M entrada, US${PRECIO_SALIDA}/M salida).\n")

    (SALIDA / "informe_tablas.md").write_text("\n".join(L), encoding="utf-8")
    (SALIDA / "resumen.json").write_text(json.dumps({"automaticas": auto, "juez": juez, "meta": meta}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
