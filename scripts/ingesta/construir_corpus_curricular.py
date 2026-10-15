#!/usr/bin/env python3
"""
Consolida las paginas extraidas (data/raw/programa_curricular/p*.json) en un corpus RAG con metadatos:
data/programa_curricular_secundaria_2016.json  (mismo esquema {metadata, keywords, chunks} que los demas
JSON de data/, mas campos estructurados por chunk: area, competencia, ciclo, grado, tipo, paginas).

Uso (desde la raiz del repo):  python scripts/ingesta/construir_corpus_curricular.py
"""
import difflib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw" / "programa_curricular"
SALIDA = RAIZ / "data" / "programa_curricular_secundaria_2016.json"

# 31 competencias oficiales del CNEB (29 de area + 2 transversales) y su area curricular
CANON = [
    ("Desarrollo Personal, Ciudadanía y Cívica", "Construye su identidad"),
    ("Desarrollo Personal, Ciudadanía y Cívica", "Convive y participa democráticamente en la búsqueda del bien común"),
    ("Ciencias Sociales", "Construye interpretaciones históricas"),
    ("Ciencias Sociales", "Gestiona responsablemente el espacio y el ambiente"),
    ("Ciencias Sociales", "Gestiona responsablemente los recursos económicos"),
    ("Educación Física", "Se desenvuelve de manera autónoma a través de su motricidad"),
    ("Educación Física", "Asume una vida saludable"),
    ("Educación Física", "Interactúa a través de sus habilidades sociomotrices"),
    ("Arte y Cultura", "Aprecia de manera crítica manifestaciones artístico-culturales"),
    ("Arte y Cultura", "Crea proyectos desde los lenguajes artísticos"),
    ("Comunicación", "Se comunica oralmente en su lengua materna"),
    ("Comunicación", "Lee diversos tipos de textos escritos en lengua materna"),
    ("Comunicación", "Escribe diversos tipos de textos en lengua materna"),
    ("Castellano como Segunda Lengua", "Se comunica oralmente en castellano como segunda lengua"),
    ("Castellano como Segunda Lengua", "Lee diversos tipos de textos escritos en castellano como segunda lengua"),
    ("Castellano como Segunda Lengua", "Escribe diversos tipos de textos en castellano como segunda lengua"),
    ("Inglés como Lengua Extranjera", "Se comunica oralmente en inglés como lengua extranjera"),
    ("Inglés como Lengua Extranjera", "Lee diversos tipos de textos en inglés como lengua extranjera"),
    ("Inglés como Lengua Extranjera", "Escribe diversos tipos de textos en inglés como lengua extranjera"),
    ("Matemática", "Resuelve problemas de cantidad"),
    ("Matemática", "Resuelve problemas de regularidad, equivalencia y cambio"),
    ("Matemática", "Resuelve problemas de forma, movimiento y localización"),
    ("Matemática", "Resuelve problemas de gestión de datos e incertidumbre"),
    ("Ciencia y Tecnología", "Indaga mediante métodos científicos para construir conocimientos"),
    ("Ciencia y Tecnología", "Explica el mundo físico basándose en conocimientos sobre los seres vivos, materia y energía, biodiversidad, Tierra y universo"),
    ("Ciencia y Tecnología", "Diseña y construye soluciones tecnológicas para resolver problemas de su entorno"),
    ("Educación para el Trabajo", "Gestiona proyectos de emprendimiento económico o social"),
    ("Educación Religiosa", "Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente, comprendiendo la doctrina de su propia religión, abierto al diálogo con las que le son cercanas"),
    ("Educación Religiosa", "Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida en coherencia con su creencia religiosa"),
    ("Competencias transversales", "Se desenvuelve en entornos virtuales generados por las TIC"),
    ("Competencias transversales", "Gestiona su aprendizaje de manera autónoma"),
]

CICLO_DE_GRADO = {1: "VI", 2: "VI", 3: "VII", 4: "VII", 5: "VII"}
NIVELES_UTILES = ("destacado", "ciclo vi", "ciclo vii")  # secundaria atiende VI y VII


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"^competencia\s+", "", s.strip())
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def canonizar(nombre: str):
    """Devuelve (area, nombre_canonico) o (None, nombre) si no hay coincidencia confiable."""
    n = norm(nombre)
    mejor = max(CANON, key=lambda c: difflib.SequenceMatcher(None, n, norm(c[1])).ratio())
    r = difflib.SequenceMatcher(None, n, norm(mejor[1])).ratio()
    return (mejor if r >= 0.85 else (None, nombre.strip()))


ORDINALES = {"primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3, "cuarto": 4, "quinto": 5}
GRADOS_DE_CICLO = {"VI": {1, 2}, "VII": {3, 4, 5}}


def grado_de_encabezado(enc):
    """El grado se deriva del encabezado literal de la columna (no del numero que dio el modelo)."""
    palabras = norm(enc or "").split()
    for palabra, g in ORDINALES.items():
        if palabra in palabras:
            return g
    return None


def slug(*partes) -> str:
    """ID estable: se recorta solo el primer componente (nombre largo) para no perder el sufijo de grado/ciclo."""
    limpias = [re.sub(r"[^a-z0-9]+", "_", norm(str(p))).strip("_") for p in partes]
    limpias[0] = limpias[0][:70]
    return "_".join(x for x in limpias if x)


def main():
    paginas = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(RAW.glob("p*.json"))]
    paginas.sort(key=lambda p: p["_pdf_pagina"])

    comp_actual = None  # (area, nombre) vigente: se arrastra a paginas de continuacion sin cabecera
    desemp = defaultdict(list)    # (area, comp, grado) -> [(texto, pagina)]
    compinfo = {}                 # (area, comp, ciclo) -> {capacidades, descripcion, paginas}
    estand = {}                   # (area, comp, nivel) -> (texto, pagina)
    narrativa = []                # (pagina, texto)
    sin_mapear = set()
    anomalias = []                # desempeños cuyo grado no se pudo derivar del encabezado (se descartan)
    conflictos = set()            # (pagina, ciclo leido, grado del encabezado): encabezado y ciclo discrepan
    cols_grados, comp_cols = {}, None  # columna -> grado de la ultima pagina con encabezado (misma competencia)
    heredados = 0                 # desempeños de paginas de continuacion cuyo grado se heredo por columna

    for p in paginas:
        n = p["_pdf_pagina"]
        if p.get("competencia"):
            comp_actual = canonizar(p["competencia"])
            if comp_actual[0] is None:
                sin_mapear.add(p["competencia"])
        area, comp = comp_actual if comp_actual else (None, None)

        if p["tipo"] in ("narrativa", "otro") and p.get("texto"):
            narrativa.append((n, p["texto"].strip()))
        if not comp:
            continue
        if p.get("capacidades") or p.get("descripcion_nivel"):
            ciclo = (p.get("ciclo") or "").upper() or None
            info = compinfo.setdefault((area, comp, ciclo), {"capacidades": [], "descripcion": None, "paginas": []})
            for c in p.get("capacidades") or []:
                if c not in info["capacidades"]:
                    info["capacidades"].append(c)
            info["descripcion"] = info["descripcion"] or p.get("descripcion_nivel")
            info["paginas"].append(n)
        ciclo_pag = (p.get("ciclo") or "").upper()
        if comp != comp_cols:  # otra competencia: los grados por columna ya no aplican
            cols_grados, comp_cols = {}, comp
        items = p.get("desempenos") or []
        # 1) grados leidos del encabezado impreso -> mapa columna->grado de esta pagina
        # Los encabezados solo son confiables en paginas que imprimen el recuadro de la competencia;
        # en paginas de continuacion el modelo llego a inventarlos (p. 135), asi que se ignoran.
        es_box = bool(p.get("competencia")) and bool(p.get("capacidades") or p.get("descripcion_nivel"))
        if es_box and items:
            cols_grados = {}  # una pagina con recuadro redefine las columnas (p. ej. 3°/4° -> 5°)
        orden = []  # grados en orden de aparicion (el modelo emite columna izquierda primero)
        for d in items:
            g = grado_de_encabezado(d.get("encabezado_columna")) if es_box else None
            if g is not None:
                if g not in orden:
                    orden.append(g)
                cols_grados[d["columna"] if d.get("columna") is not None else orden.index(g) + 1] = g
        # 2) asignar grado: encabezado propio, o heredado por posicion de columna (pagina de continuacion)
        for d in items:
            g = grado_de_encabezado(d.get("encabezado_columna")) if es_box else None
            if g is None:
                g = cols_grados.get(d.get("columna"))
                if g is not None:
                    heredados += 1
            if g is None or not d.get("texto"):
                anomalias.append((n, "sin grado derivable", d.get("encabezado_columna")))
                continue
            if ciclo_pag in GRADOS_DE_CICLO and g not in GRADOS_DE_CICLO[ciclo_pag]:
                # el encabezado impreso manda sobre el ciclo que leyo el modelo; se deja constancia
                conflictos.add((n, ciclo_pag, g))
            desemp[(area, comp, g)].append((d["texto"].strip(), n))
        for e in p.get("estandares") or []:
            nivel = e.get("nivel") or ""
            if any(k in nivel.lower() for k in NIVELES_UTILES) and e.get("texto"):
                estand[(area, comp, nivel.strip())] = (e["texto"].strip(), n)

    chunks = []
    for (area, comp, ciclo), info in compinfo.items():
        partes = [f"Competencia \"{comp}\"" + (f" — Ciclo {ciclo}" if ciclo else "") + (f" ({area})" if area else "")]
        if info["capacidades"]:
            partes.append("Capacidades:\n" + "\n".join(f"- {c}" for c in info["capacidades"]))
        if info["descripcion"]:
            partes.append("Nivel esperado al final del ciclo:\n" + info["descripcion"])
        chunks.append({
            "id": "comp_" + slug(comp, ciclo or ""), "section": f"{comp} — Competencia y capacidades" + (f" (ciclo {ciclo})" if ciclo else ""),
            "text": "\n\n".join(partes), "keywords": [k for k in (area, comp, "capacidades", f"ciclo {ciclo}" if ciclo else None) if k],
            "tipo": "competencia", "area": area, "competencia": comp, "ciclo": ciclo, "grado": None,
            "paginas": sorted(set(info["paginas"])),
        })
    for (area, comp, g), items in sorted(desemp.items(), key=lambda kv: (str(kv[0][0]), kv[0][1], kv[0][2])):
        vistos, textos = set(), []
        for t, _ in items:
            if t not in vistos:
                vistos.add(t)
                textos.append(t)
        ciclo = CICLO_DE_GRADO[g]
        chunks.append({
            "id": "desemp_" + slug(comp, g), "section": f"{comp} — Desempeños {g}° grado de secundaria",
            "text": f"Desempeños de {g}° grado de secundaria (ciclo {ciclo}) — Competencia \"{comp}\"" + (f" ({area})" if area else "")
                    + ":\n" + "\n".join(f"- {t}" for t in textos),
            "keywords": [k for k in (area, comp, "desempeños", f"{g}° grado", f"ciclo {ciclo}") if k],
            "tipo": "desempenos", "area": area, "competencia": comp, "ciclo": ciclo, "grado": g,
            "paginas": sorted({pg for _, pg in items}),
        })
    for (area, comp, nivel), (texto, pg) in estand.items():
        m = re.search(r"ciclo\s+(vii|vi)\b", nivel.lower())
        ciclo = m.group(1).upper() if m else None
        chunks.append({
            "id": "estandar_" + slug(comp, nivel), "section": f"{comp} — Estándar: {nivel}",
            "text": f"Estándar de aprendizaje — {nivel} — Competencia \"{comp}\"" + (f" ({area})" if area else "") + f":\n{texto}",
            "keywords": [k for k in (area, comp, "estándar de aprendizaje", nivel) if k],
            "tipo": "estandar", "area": area, "competencia": comp, "ciclo": ciclo, "grado": None, "paginas": [pg],
        })
    for pg, texto in narrativa:
        bloques, actual = [], ""
        for b in (x.strip() for x in re.split(r"\n\s*\n", texto)):
            if len(actual) + len(b) > 1000 and actual:
                bloques.append(actual)
                actual = ""
            actual = (actual + "\n\n" + b).strip()
        if len(actual) > 80:
            bloques.append(actual)
        for i, par in enumerate(bloques):
            chunks.append({
                "id": f"narr_p{pg:03d}_{i}", "section": f"Programa Curricular — texto, p. {pg}", "text": par,
                "keywords": ["programa curricular", "educación secundaria"], "tipo": "narrativa",
                "area": None, "competencia": None, "ciclo": None, "grado": None, "paginas": [pg],
            })

    salida = {
        "metadata": {
            "documento": "Programa Curricular de Educación Secundaria (MINEDU, RM 649-2016-MINEDU)",
            "origen": "PDF escaneado, 259 páginas, transcrito con Claude visión (Bedrock) — ver scripts/ingesta/",
            "n_chunks": len(chunks),
        },
        "keywords": ["CNEB", "desempeños", "estándares de aprendizaje", "competencias", "capacidades", "secundaria"],
        "chunks": chunks,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    por_tipo = defaultdict(int)
    for c in chunks:
        por_tipo[c["tipo"]] += 1
    print(f"{len(chunks)} chunks -> {SALIDA}")
    print(dict(por_tipo))
    print(f"desempeños con grado heredado por columna (páginas de continuación): {heredados}")
    print(f"conflictos encabezado/ciclo (se usa el encabezado): {sorted(conflictos)}")
    print(f"desempeños descartados por encabezado ilegible: {len(anomalias)} en páginas {sorted({a[0] for a in anomalias})}")
    print("competencias sin mapear:", sorted(sin_mapear) or "ninguna")
    comps = {c for _, c in CANON}
    con_desemp = {c for (_, c, _) in desemp}
    print("competencias canonicas sin desempeños:", sorted(comps - con_desemp) or "ninguna")
    faltan = [(c, g) for (a, c) in CANON for g in range(1, 6) if a != "Competencias transversales" and (a, c, g) not in desemp]
    print(f"combinaciones competencia×grado sin desempeños: {len(faltan)}")
    for c, g in faltan[:40]:
        print(f"   {g}° {c}")


if __name__ == "__main__":
    main()
