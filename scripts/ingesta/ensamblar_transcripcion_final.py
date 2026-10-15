#!/usr/bin/env python3
"""
Ensambla las paginas finales a partir del resultado del arbitraje.

Regla: la lectura base es la de Sonnet. Del arbitraje solo se aceptan cambios PEQUENOS (similitud >= UMBRAL con
la lectura de Sonnet): corrigen palabras sueltas. Los cambios grandes (eliminar o reescribir tramos largos) o las
"terceras lecturas" no se aceptan: se conserva Sonnet y se deja constancia en el informe para revision humana.

Uso:  python scripts/ingesta/ensamblar_transcripcion_final.py
Lee:  data/raw/programa_curricular_arbitrado/   Escribe: data/raw/programa_curricular/ (paginas utiles)
      docs/TRANSCRIPCION_REVISION_PENDIENTE.md
"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ARB = RAIZ / "data" / "raw" / "programa_curricular_arbitrado"
FINAL = RAIZ / "data" / "raw" / "programa_curricular"
INFORME = RAIZ / "docs" / "TRANSCRIPCION_REVISION_PENDIENTE.md"
UMBRAL = 0.90


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn"))).strip()


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio()


def revertir(pag, despues, antes):
    """Devuelve el texto 'despues' a la lectura de Sonnet donde aparezca en la pagina."""
    for d in pag.get("desempenos") or []:
        if d.get("texto") == despues:
            d["texto"] = antes
            return True
    for e in pag.get("estandares") or []:
        if e.get("texto") == despues:
            e["texto"] = antes
            return True
    if pag.get("descripcion_nivel") == despues:
        pag["descripcion_nivel"] = antes
        return True
    caps = pag.get("capacidades") or []
    if despues in caps:
        caps[caps.index(despues)] = antes
        return True
    return False


def main():
    aceptados = rechazados = 0
    pendientes = []
    for f in sorted(ARB.glob("p*.json")):
        pag = json.loads(f.read_text(encoding="utf-8"))
        arb = pag.get("_arbitraje", {})
        for c in arb.get("cambios", []):
            if c["tipo"].startswith("agregado") or c["tipo"].startswith("eliminado"):
                continue
            if sim(c["despues"], c["antes_sonnet"]) >= UMBRAL:
                aceptados += 1
            else:
                if revertir(pag, c["despues"], c["antes_sonnet"]):
                    rechazados += 1
                    pendientes.append((pag["_pdf_pagina"], c["tipo"], "cambio grande del arbitro (rechazado)", c))
        for t in arb.get("tercera_lectura", []):
            pendientes.append((pag["_pdf_pagina"], t.get("campo", "desempeno"), "tercera lectura", t))
        pag["_ensamblado"] = {"umbral_aceptacion": UMBRAL}
        (FINAL / f.name).write_text(json.dumps(pag, ensure_ascii=False, indent=1), encoding="utf-8")

    lineas = ["# Transcripción: puntos pendientes de revisión humana\n",
              f"Generado por `scripts/ingesta/ensamblar_transcripcion_final.py`. Base: lectura de Sonnet; el árbitro solo "
              f"cambia palabras sueltas (similitud ≥ {UMBRAL}). Aceptados: {aceptados}. Cambios grandes rechazados: {rechazados}.\n",
              "Cada punto debe cotejarse con la página indicada del PDF (numeración del archivo PDF, no la impresa).\n"]
    for n, tipo, motivo, c in sorted(pendientes, key=lambda x: x[0]):
        lineas.append(f"## Página {n} — {tipo} — {motivo}")
        for k, etiqueta in (("haiku", "Haiku"), ("sonnet", "Sonnet"), ("antes_sonnet", "Sonnet"), ("arbitro", "Árbitro"), ("despues", "Árbitro")):
            if c.get(k):
                lineas.append(f"- **{etiqueta}:** {c[k][:700]}")
        lineas.append("")
    INFORME.write_text("\n".join(lineas), encoding="utf-8")
    print(f"cambios del árbitro aceptados: {aceptados} | rechazados por grandes: {rechazados} | puntos pendientes: {len(pendientes)}")
    print(f"informe: {INFORME}")


if __name__ == "__main__":
    main()
