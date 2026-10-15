# eval/e2e_puntuar.py
"""
Mide los documentos generados por e2e_generar contra el Programa Curricular (la fuente oficial).

Medidas automaticas (sin juez), sobre la celda "III. PROPOSITOS DE APRENDIZAJE". El modelo no copia los desempenos
oficiales sino que los ADAPTA al tema, asi que no hay umbral de "copia": se usa el solapamiento lexico continuo
(Jaccard de palabras de contenido) de cada desempeno generado con los oficiales de las competencias del caso:
  - solape_grado   : con los oficiales del grado pedido (mayor = mas anclado en lo oficial)
  - solape_otro    : media, sobre los otros 4 grados, del mejor solape con cada uno (cada grado por separado, para
                     que el tamano del conjunto de comparacion no sesgue)
  - margen_grado   : solape_grado - solape_otro (negativo = el texto se parece mas a otros grados)
  - grado_primero  : fraccion de desempenos cuyo mejor solape es con el grado PEDIDO frente a los otros 4 (azar: 0.20)
  - cobertura      : cuanto de lo oficial del grado queda representado en el documento (media del mejor solape)
  - competencias   : precision/recall de las competencias nombradas frente a las pedidas (o a las del area si no se pidio)

Medida con juez (opcional, cuesta): Claude califica de 0 a 3 con la referencia oficial a la vista.

Uso:  python -m src.eval.e2e_puntuar              # medidas automaticas
      python -m src.eval.e2e_puntuar --juez       # ademas llama al juez
"""
import argparse
import difflib
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

from ..core.retrieval_estructurado import RecuperadorCurricular
from .e2e_casos import CASO_POR_ID, CASOS, Caso

SALIDA = Path(__file__).parent / "resultados" / "e2e"
CONDICIONES = ("sin_rag", "rag_previo", "rag_nuevo")
MIN_PALABRAS = 6       # segmentos mas cortos no se evaluan (restos de numeracion, etc.)


def _norm(s: str) -> List[str]:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9ñ]+", s)


def _sim(a: List[str], b: List[str]) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else 0.0


_STOP = set("de la el en y a los las del con que por para su sus un una al se como o e lo es".split())


def _jaccard(a: List[str], b: List[str]) -> float:
    """Solapamiento de palabras de contenido (sin orden): robusto a que el modelo reordene o parafrasee."""
    A, B = {w for w in a if w not in _STOP}, {w for w in b if w not in _STOP}
    return len(A & B) / len(A | B) if A | B else 0.0


def _oraciones(texto: str) -> List[str]:
    texto = re.sub(r"<br\s*/?>|[••]", ". ", texto or "")
    partes = re.split(r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ¿¡0-9])", texto)
    return [p.strip(" -*;.\n") for p in partes if len(_norm(p)) >= MIN_PALABRAS]


# ------------------------------------------------------------------ extraccion desde el documento generado
def celda_propositos(doc: str) -> str:
    m = re.search(r"\|\s*\**\s*III\.\s*PROP[ÓO]SITOS DE APRENDIZAJE\s*\**\s*\|(.*?)(?:\|\s*\n|\Z)", doc, re.S | re.I)
    return m.group(1) if m else ""


def partes_de_la_celda(celda: str) -> Dict[str, str]:
    """competencias / capacidades / desempenos / criterios, segun las etiquetas que pide la plantilla."""
    pos = {}
    for clave, patron in (("competencias", r"Competencia\(?s?\)?\s*:"), ("capacidades", r"Capacidades\s*:"),
                          ("desempenos", r"Desempe[ñn]os[^:]{0,60}:"), ("criterios", r"Criterios de evaluaci[óo]n\s*:")):
        m = re.search(patron, celda, re.I)
        if m:
            pos[clave] = (m.start(), m.end())
    orden = sorted(pos.items(), key=lambda kv: kv[1][0])
    out = {}
    for i, (clave, (_, fin)) in enumerate(orden):
        out[clave] = celda[fin:(orden[i + 1][1][0] if i + 1 < len(orden) else len(celda))].strip()
    return out


# ------------------------------------------------------------------ referencia oficial
class Referencia:
    def __init__(self):
        self.rec = RecuperadorCurricular.desde_json()
        self._desemp: Dict[tuple, List[str]] = {}
        for c in self.rec.chunks:
            if c.get("tipo") == "desempenos":
                items = [l[2:].strip() for l in c["text"].splitlines() if l.startswith("- ")]
                self._desemp[(c["competencia"], c["grado"])] = items

    def competencias_esperadas(self, caso: Caso) -> List[str]:
        if caso.competencias:
            return self.rec.competencias_canonicas(caso.competencias, self.rec.area_canonica(caso.area))
        area = self.rec.area_canonica(caso.area)
        return [c for c, a in self.rec._competencias.items() if a == area]

    def por_grado(self, comps: List[str]) -> Dict[int, List[List[str]]]:
        """grado -> oraciones oficiales (normalizadas) de esas competencias."""
        out: Dict[int, List[List[str]]] = {g: [] for g in range(1, 6)}
        for (c, g), items in self._desemp.items():
            if c in comps:
                out[g] += [_norm(s) for item in items for s in (_oraciones(item) or [item])]
        return out

    def oficiales(self, comps: List[str], grado: int, mismo_grado: bool) -> List[str]:
        out = []
        for (c, g), items in self._desemp.items():
            if c in comps and ((g == grado) == mismo_grado):
                out += items
        return out


def competencias_nombradas(ref: Referencia, texto: str) -> List[str]:
    """Competencias del CNEB cuyo nombre aparece (casi literal) en `texto`."""
    palabras = _norm(texto)
    halladas = []
    for nombre in ref.rec._competencias:
        n = _norm(nombre)
        k = len(n)
        # ventanas de longitud k-1..k+1: una ventana con palabras de mas (p. ej. el prefijo "competencia 15") baja la similitud
        mejor = max((_sim(n, palabras[i:i + L]) for L in (k - 1, k, k + 1) if L > 0 for i in range(0, max(1, len(palabras) - L + 1))),
                    default=0.0)
        if mejor >= 0.88:
            halladas.append(nombre)
    return halladas


# ------------------------------------------------------------------ puntaje de un documento
def puntuar_documento(ref: Referencia, caso: Caso, doc: str) -> dict:
    celda = celda_propositos(doc)
    partes = partes_de_la_celda(celda)
    esperadas = ref.competencias_esperadas(caso)
    gen = _oraciones(partes.get("desempenos", ""))

    n = len(gen)
    por_grado = ref.por_grado(esperadas)
    sg_l, so_l, primero = [], [], []
    for g in gen:
        ng = _norm(g)
        mejor = {gr: max((_jaccard(ng, o) for o in oraciones), default=0.0) for gr, oraciones in por_grado.items()}
        sg = mejor[caso.grado]
        otros = [v for gr, v in mejor.items() if gr != caso.grado]
        sg_l.append(sg)
        so_l.append(sum(otros) / len(otros))
        primero.append(1.0 if sg > 0 and sg >= max(otros) else 0.0)
    media = lambda xs: sum(xs) / len(xs) if xs else 0.0

    # cobertura: cuanto de lo oficial del grado queda representado (para cada oficial, su mejor solape con el documento)
    gen_norm = [_norm(g) for g in gen]
    cobertura = media([max((_jaccard(o, g) for g in gen_norm), default=0.0) for o in por_grado[caso.grado]])
    nombradas = competencias_nombradas(ref, partes.get("competencias", ""))
    aciertos = len(set(nombradas) & set(esperadas))
    return {
        "n_desempenos": n,
        "solape_grado": media(sg_l), "solape_otro": media(so_l),
        "margen_grado": media([x - y for x, y in zip(sg_l, so_l)]),
        "grado_primero": media(primero),
        "cobertura": cobertura,
        "competencias_nombradas": nombradas, "competencias_esperadas": esperadas,
        "comp_precision": aciertos / len(nombradas) if nombradas else 0.0,
        "comp_recall": aciertos / len(esperadas) if esperadas else 0.0,
        "celda_encontrada": bool(celda), "desempenos_encontrados": bool(partes.get("desempenos")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", default=",".join(c.id for c in CASOS))
    args = ap.parse_args()
    ref = Referencia()
    filas = []
    for cid in args.casos.split(","):
        for cond in CONDICIONES:
            f = SALIDA / f"{cid}_{cond}.md"
            if not f.exists():
                continue
            r = puntuar_documento(ref, CASO_POR_ID[cid], f.read_text(encoding="utf-8"))
            filas.append({"caso": cid, "condicion": cond, **r})
            print(f"{cid} {cond:<10} desemp={r['n_desempenos']:>2}  solape_grado={r['solape_grado']:.2f} otro={r['solape_otro']:.2f} "
                  f"margen={r['margen_grado']:+.2f} grado_primero={r['grado_primero']:.2f} cobertura={r['cobertura']:.2f}  "
                  f"comp P={r['comp_precision']:.2f} R={r['comp_recall']:.2f}")
    (SALIDA / "puntajes_automaticos.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
