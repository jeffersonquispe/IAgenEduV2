# core/retrieval_estructurado.py
"""
Recuperacion estructurada sobre el Programa Curricular de Educacion Secundaria (data/programa_curricular_secundaria_2016.json).

Cada chunk trae metadatos (tipo, area, competencia, ciclo, grado). Cuando el area y el grado se conocen, los
desempenos candidatos son pocos (uno por competencia del area), asi que se devuelven SIEMPRE, ordenados por BM25
sobre el tema, y si el docente ya eligio la competencia se recuperan por busqueda exacta. Los vecinos tipados
(capacidades de la competencia y estandar del mismo ciclo) se anexan despues en vez de competir por rango.

Motivo: sin filtrar por metadatos, ~80% de los desempenos recuperados eran de otro grado (ver docs/METRICAS_EFECTIVIDAD.md 5.D).
"""
import difflib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

CICLO_DE_GRADO = {1: "VI", 2: "VI", 3: "VII", 4: "VII", 5: "VII"}
RUTA_CORPUS = Path(__file__).resolve().parents[2] / "data" / "programa_curricular_secundaria_2016.json"

_STOPWORDS = set(
    "a al algo con como cual cuales de del el en es esta este la las lo los para por que se su sus un una uno y o u e ni "
    "sobre entre desde hasta ser son".split()
)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokens(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9ñ]+", norm(s)) if t not in _STOPWORDS and len(t) > 1]


def _clave(s: str) -> str:
    """Normalizacion para comparar nombres de area/competencia (sin tildes, puntuacion ni '_')."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", norm(s).replace("_", " "))).strip()


def grado_a_int(grado) -> Optional[int]:
    """Acepta 3, '3', '3°', '3° de secundaria'. None si no es un grado 1-5."""
    m = re.search(r"[1-5]", str(grado or ""))
    return int(m.group()) if m else None


class BM25:
    def __init__(self, chunks: List[dict], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        # titulo y keywords pesan doble: se repiten en el texto indexado
        docs = [tokens(f"{c.get('section', '')} {c.get('section', '')} {' '.join(c.get('keywords', []))} "
                       f"{' '.join(c.get('keywords', []))} {c.get('text', '')}") for c in chunks]
        self.tf = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = (sum(self.len) / len(self.len)) if docs else 0.0
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> List[float]:
        q = tokens(query)
        out = []
        for tf, ln in zip(self.tf, self.len):
            s = 0.0
            for t in q:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / self.avg))
            out.append(s)
        return out


def pasa_filtro(c: dict, grado: Optional[int], area_can: Optional[str]) -> bool:
    """Un chunk estructurado solo es candidato si coincide con area, grado y ciclo pedidos.
    Los chunks sin metadatos (narrativa) siempre pasan."""
    if c.get("area") and area_can and c["area"] != area_can:
        return False
    if c.get("tipo") == "desempenos" and grado and c.get("grado") != grado:
        return False
    if c.get("tipo") in ("competencia", "estandar") and grado and c.get("ciclo") not in (None, CICLO_DE_GRADO.get(grado)):
        return False
    return True


class RecuperadorCurricular:
    def __init__(self, chunks: List[dict]):
        self.chunks = chunks
        self._bm = BM25(chunks)
        self._areas = {_clave(c["area"]): c["area"] for c in chunks if c.get("area")}
        self._competencias = {}  # nombre canonico -> area
        for c in chunks:
            if c.get("competencia"):
                self._competencias[c["competencia"]] = c.get("area")
        # vecinos tipados: desempenos(grado) -> capacidades de la competencia y estandar del mismo ciclo
        por_comp = defaultdict(list)
        for i, c in enumerate(chunks):
            if c.get("competencia"):
                por_comp[c["competencia"]].append(i)
        self._vecinos: Dict[int, List[int]] = defaultdict(list)
        for idxs in por_comp.values():
            for i in idxs:
                ci = chunks[i]
                if ci.get("tipo") != "desempenos":
                    continue
                ciclo = CICLO_DE_GRADO.get(ci["grado"])
                vec = [j for j in idxs if chunks[j].get("tipo") in ("competencia", "estandar")
                       and chunks[j].get("ciclo") in (None, ciclo)]
                # prioridad si hay que recortar: capacidades del ciclo, estandar del ciclo, estandar destacado, resto
                def prioridad(j, ciclo=ciclo):
                    t, cl = chunks[j]["tipo"], chunks[j].get("ciclo")
                    return (0 if t == "competencia" and cl == ciclo else 1 if t == "estandar" and cl == ciclo
                            else 2 if t == "estandar" else 3, j)
                self._vecinos[i] = sorted(vec, key=prioridad)

    @classmethod
    def desde_json(cls, ruta: Path = RUTA_CORPUS) -> "RecuperadorCurricular":
        return cls(json.loads(Path(ruta).read_text(encoding="utf-8"))["chunks"])

    # ---------------------------------------------------------------- resolucion de nombres
    def area_canonica(self, area: Optional[str]) -> Optional[str]:
        return self._areas.get(_clave(area)) if area else None

    def competencias_canonicas(self, textos: Iterable[str], area_can: Optional[str] = None) -> List[str]:
        """Resuelve los nombres que llegan del wizard (pueden tener otra redaccion) a competencias del corpus.
        Orden de preferencia: igualdad, contencion (la mas parecida), parecido >= 0.85. Con area conocida se
        busca primero dentro del area, lo que desambigua 'Construye su identidad' (DPCC) de la version religiosa."""
        pool_area = [c for c, a in self._competencias.items() if not area_can or a == area_can]
        out = []
        for t in textos:
            t = re.sub(r"^[\s\-\*•\d\.\)]+", "", t or "").strip()
            if len(t) < 8:
                continue
            nt = _clave(t)
            hallada = None
            for pool in (pool_area, list(self._competencias)):
                igual = [c for c in pool if _clave(c) == nt]
                if igual:
                    hallada = igual[0]
                elif len(nt) >= 15:
                    cont = [c for c in pool if nt in _clave(c) or _clave(c) in nt]
                    if cont:
                        hallada = max(cont, key=lambda c: difflib.SequenceMatcher(None, nt, _clave(c)).ratio())
                if not hallada:
                    mejor = max(pool, key=lambda c: difflib.SequenceMatcher(None, nt, _clave(c)).ratio(), default=None)
                    if mejor and difflib.SequenceMatcher(None, nt, _clave(mejor)).ratio() >= 0.85:
                        hallada = mejor
                if hallada:
                    break
            if hallada and hallada not in out:
                out.append(hallada)
        return out

    # ---------------------------------------------------------------- recuperacion
    def recuperar(self, query: str, grado, area: Optional[str] = None, competencias: Optional[Iterable[str]] = None,
                  k: int = 10, m: int = 2, con_vecinos: bool = True, con_resto: bool = True) -> List[dict]:
        """Devuelve chunks (dicts del corpus) en este orden:
        1) desempenos del grado: de las competencias pedidas si se resuelven, si no los m mejores del area por BM25;
        2) sus vecinos tipados (capacidades de la competencia y estandar del ciclo);
        3) (con_resto) el resto por BM25 filtrado por area/grado."""
        g = grado_a_int(grado)
        if g is None:       # sin grado valido no hay forma de filtrar: mezclaria desempenos de distintos grados
            return []
        area_can = self.area_canonica(area)
        sc = self._bm.scores(query)
        comps = self.competencias_canonicas(competencias or [], area_can)

        if comps:
            cand = [next((i for i, c in enumerate(self.chunks)
                          if c.get("tipo") == "desempenos" and c["competencia"] == comp and c["grado"] == g), None)
                    for comp in comps]
            primarios = [i for i in cand if i is not None]
        elif area_can:
            cand = [i for i, c in enumerate(self.chunks) if c.get("tipo") == "desempenos" and pasa_filtro(c, g, area_can)]
            cand.sort(key=lambda i: -sc[i])     # estable: los empates (sin palabras en comun) conservan el orden del corpus
            primarios = cand[:m]
        else:               # area no reconocida y sin competencia: no se inventan desempenos de areas ajenas
            primarios = []

        orden = list(primarios)
        if con_vecinos:
            # con competencias elegidas el area no filtra a los vecinos: una transversal (TIC) elegida dentro de
            # Matematica tiene sus capacidades y estandar en el area "Competencias transversales"
            area_vecinos = None if comps else area_can
            for s in primarios:
                for v in self._vecinos.get(s, ()):
                    if v not in orden and pasa_filtro(self.chunks[v], g, area_vecinos):
                        orden.append(v)
        if con_resto:
            # sin area reconocida solo se admiten chunks sin area (narrativa), nunca los de un area cualquiera
            resto = sorted((i for i in range(len(self.chunks))
                            if sc[i] > 0 and pasa_filtro(self.chunks[i], g, area_can)
                            and (area_can or not self.chunks[i].get("area"))),
                           key=lambda i: -sc[i])
            orden += [i for i in resto if i not in orden]
        return [self.chunks[i] for i in orden[:k]]
