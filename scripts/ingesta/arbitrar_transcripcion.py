#!/usr/bin/env python3
"""
Concilia dos transcripciones independientes de cada pagina (Haiku y Sonnet) con un arbitro que mira la imagen.

Ningun modelo es completo: cada uno omite o altera algunos items. Por pagina se alinean los items de ambas
lecturas y se piden al arbitro (Claude con vision) solo las decisiones que importan:
  - conflicto:   el mismo item leido distinto -> texto correcto segun la imagen
  - solo_haiku:  item que Sonnet no trae -> ¿es una vineta propia impresa en la pagina?
  - solo_sonnet: item que Haiku no trae  -> ¿aparece impreso?
Cada cambio queda registrado en "_arbitraje" de la pagina final (antes/despues), y las respuestas del arbitro
que no coinciden con ninguna de las dos lecturas se marcan "tercera_lectura" para revision humana.

Uso:
  python scripts/ingesta/arbitrar_transcripcion.py --pdf RUTA.pdf --haiku DIR --sonnet DIR --out DIR [--pages 41,48]
"""
import argparse
import difflib
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import pypdfium2 as pdfium
from botocore.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraer_programa_curricular import _json_de, renderizar  # noqa: E402

UMBRAL_PAREJA = 0.55   # similitud minima para considerar que dos items son "el mismo" leido distinto
UMBRAL_IGUAL = 0.995   # por encima, se consideran identicos


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def es_intro(t: str) -> bool:
    """Frase introductoria de cada columna ('Cuando el estudiante ... realiza desempeños como los siguientes')."""
    low = (t or "").lower()
    return bool(re.match(r"\s*(cuando|en proceso)\b.{0,40}\bestudiante", low)) or "realiza desempeños como" in low[:400]


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio()


def alinear(a_items, b_items):
    """Empareja items de A (haiku) con B (sonnet) por mejor similitud; devuelve (parejas, solo_a, solo_b)."""
    cand = sorted(((ratio(a["texto"], b["texto"]), i, j) for i, a in enumerate(a_items) for j, b in enumerate(b_items)),
                  reverse=True)
    usado_a, usado_b, parejas = set(), set(), []
    for r, i, j in cand:
        if r < UMBRAL_PAREJA:
            break
        if i in usado_a or j in usado_b:
            continue
        usado_a.add(i)
        usado_b.add(j)
        parejas.append((i, j, r))
    return (parejas,
            [i for i in range(len(a_items)) if i not in usado_a],
            [j for j in range(len(b_items)) if j not in usado_b])


PROMPT = """Eres un verificador de transcripciones. La imagen es una pagina escaneada del "Programa Curricular de Educacion Secundaria" (Peru, MINEDU 2016).
Dos transcriptores leyeron esta pagina y discrepan en los puntos de abajo. Mira la IMAGEN y decide segun lo que esta realmente impreso.
No corrijas ortografia ni "mejores" el texto: copia lo impreso, con tildes y enes. Responde SOLO con JSON.

{bloques}

Formato de respuesta:
{{
  "conflictos": [ {{"id": <id>, "texto_correcto": <texto del item tal como esta impreso, completo>}} ],
  "existencia": [ {{"id": <id>, "veredicto": "vineta_propia" | "parte_de_otra" | "no_aparece", "texto_correcto": <texto impreso si vineta_propia, si no ''>}} ]
}}
Reglas: "vineta_propia" = aparece como una vineta/item independiente; "parte_de_otra" = el texto esta impreso pero como continuacion de otra vineta; "no_aparece" = no esta en la pagina."""


def bloque(conf, solo_h, solo_s):
    out = []
    if conf:
        out.append("CONFLICTOS (el mismo item, leido distinto; da el texto correcto):")
        for k, (cid, a, b) in enumerate(conf):
            if k % 2:  # alterna el orden para que el arbitro no prefiera sistematicamente la lectura B (la de Sonnet)
                a, b = b, a
            out.append(f"[{cid}]\n  Lectura A: {a}\n  Lectura B: {b}")
    if solo_h or solo_s:
        out.append("EXISTENCIA (un transcriptor trae este item y el otro no):")
        for cid, t in solo_h + solo_s:
            out.append(f"[{cid}] {t}")
    return "\n".join(out)


def arbitrar(client, model, jpeg, conf, solo_h, solo_s):
    ultimo = None
    for intento in range(4):
        try:
            extra = "" if intento == 0 else ('\nIMPORTANTE: tu respuesta anterior no fue JSON valido. Escapa las comillas '
                                             'dobles internas como \\" y no dejes comas finales.')
            r = client.converse(modelId=model, messages=[{"role": "user", "content": [
                {"image": {"format": "jpeg", "source": {"bytes": jpeg}}},
                {"text": PROMPT.format(bloques=bloque(conf, solo_h, solo_s)) + extra}]}],
                inferenceConfig={"maxTokens": 6000, "temperature": 0 if intento == 0 else 0.2})
            return _json_de(r["output"]["message"]["content"][0]["text"]), r.get("usage", {})
        except Exception as e:
            ultimo = e
            time.sleep(2 ** intento)
    raise RuntimeError(str(ultimo))


def preparar(h, s):
    """Alinea los desempenos de una pagina y arma las preguntas para el arbitro."""
    A = [d for d in h.get("desempenos") or [] if not es_intro(d.get("texto", ""))]
    B = [d for d in s.get("desempenos") or [] if not es_intro(d.get("texto", ""))]
    parejas, sa, sb = alinear(A, B)
    conf = [(f"c{k}", A[i]["texto"], B[j]["texto"]) for k, (i, j, r) in enumerate(parejas) if r < UMBRAL_IGUAL]
    ids_conf = {f"c{k}": (i, j) for k, (i, j, r) in enumerate(parejas) if r < UMBRAL_IGUAL}
    solo_h = [(f"h{k}", A[i]["texto"]) for k, i in enumerate(sa)]
    solo_s = [(f"s{k}", B[j]["texto"]) for k, j in enumerate(sb)]
    return A, B, parejas, sa, sb, conf, ids_conf, solo_h, solo_s


def clave_nivel(nivel):
    """'Nivel destacado' -> 'destacado'; 'Nivel esperado al final del ciclo VII' -> 'vii' (clave exacta)."""
    n = norm(nivel)
    if "destacado" in n:
        return "destacado"
    m = re.findall(r"\b(vii|vi|iv|v|iii|ii|i)\b", n)
    return m[-1] if m else n


def preparar_extras(h, s):
    """Conflictos en estandares (solo niveles utiles), descripcion del nivel y capacidades.
    Devuelve [(id, campo, indice_en_sonnet, texto_haiku, texto_sonnet)]."""
    out = []
    for k, e in enumerate(s.get("estandares") or []):
        if not any(x in (e.get("nivel") or "").lower() for x in ("destacado", "ciclo vi", "ciclo vii")):
            continue
        # la pareja en Haiku es el estandar del MISMO nivel, por clave exacta: por similitud de texto "ciclo VI" y
        # "ciclo VII" se confunden y se compararian niveles distintos
        ph = next((x for x in h.get("estandares") or [] if clave_nivel(x.get("nivel")) == clave_nivel(e.get("nivel"))), None)
        if ph and ratio(ph["texto"], e["texto"]) < UMBRAL_IGUAL:
            out.append((f"e{k}", "estandares", k, ph["texto"], e["texto"]))
    if h.get("descripcion_nivel") and s.get("descripcion_nivel") and ratio(h["descripcion_nivel"], s["descripcion_nivel"]) < UMBRAL_IGUAL:
        out.append(("d0", "descripcion_nivel", 0, h["descripcion_nivel"], s["descripcion_nivel"]))
    ca = [{"texto": t} for t in h.get("capacidades") or []]
    cb = [{"texto": t} for t in s.get("capacidades") or []]
    for k, (i, j, r) in enumerate(alinear(ca, cb)[0]):
        if r < UMBRAL_IGUAL:
            out.append((f"k{k}", "capacidades", j, ca[i]["texto"], cb[j]["texto"]))
    return out


def procesar_pagina(client, model, pdf_jpeg, n, h, s):
    A, B, parejas, sa, sb, conf, ids_conf, solo_h, solo_s = preparar(h, s)
    extras = preparar_extras(h, s)
    final = json.loads(json.dumps(s))                       # base: Sonnet
    final["desempenos"] = [dict(d) for d in B]              # sin frases introductorias
    final["_arbitraje"] = {"cambios": [], "tercera_lectura": [],
                           "preguntas": len(conf) + len(extras) + len(solo_h) + len(solo_s)}
    if not (conf or extras or solo_h or solo_s):
        return final, {}
    resp, uso = arbitrar(client, model, pdf_jpeg, conf + [(i, a, b) for i, _, _, a, b in extras], solo_h, solo_s)
    cambios, tercera = final["_arbitraje"]["cambios"], final["_arbitraje"]["tercera_lectura"]

    # conflictos en estandares / descripcion / capacidades: el texto del arbitro reemplaza al de Sonnet
    por_id = {i: (campo, idx, a, b) for i, campo, idx, a, b in extras}
    for c in resp.get("conflictos") or []:
        if c.get("id") not in por_id:
            continue
        campo, idx, antes_h, antes_s = por_id[c["id"]]
        nuevo = (c.get("texto_correcto") or "").strip()
        if not nuevo:
            continue
        if norm(nuevo) != norm(antes_s):
            if campo == "descripcion_nivel":
                final[campo] = nuevo
            elif campo == "capacidades":
                final[campo][idx] = nuevo
            else:
                final[campo][idx]["texto"] = nuevo
            cambios.append({"tipo": f"conflicto_{campo}", "antes_sonnet": antes_s, "haiku": antes_h, "despues": nuevo})
        if max(ratio(nuevo, antes_h), ratio(nuevo, antes_s)) < 0.97:
            tercera.append({"campo": campo, "haiku": antes_h, "sonnet": antes_s, "arbitro": nuevo})

    # conflictos de desempenos: texto del arbitro reemplaza al de Sonnet
    for c in resp.get("conflictos") or []:
        par = ids_conf.get(c.get("id"))
        nuevo = (c.get("texto_correcto") or "").strip()
        if not par or not nuevo:
            continue
        i, j = par
        antes_h, antes_s = A[i]["texto"], B[j]["texto"]
        if norm(nuevo) != norm(antes_s):
            idx = final["desempenos"].index(next(d for d in final["desempenos"] if d["texto"] == antes_s))
            final["desempenos"][idx]["texto"] = nuevo
            cambios.append({"tipo": "conflicto", "antes_sonnet": antes_s, "haiku": antes_h, "despues": nuevo})
        if max(ratio(nuevo, antes_h), ratio(nuevo, antes_s)) < 0.97:
            tercera.append({"haiku": antes_h, "sonnet": antes_s, "arbitro": nuevo})

    # existencia
    for e in resp.get("existencia") or []:
        cid, ver = e.get("id", ""), e.get("veredicto")
        if cid.startswith("h") and ver == "vineta_propia" and (e.get("texto_correcto") or "").strip():
            k = int(cid[1:])
            vecino = A[sa[k] - 1] if sa[k] > 0 else A[sa[k] + 1] if sa[k] + 1 < len(A) else None
            # hereda la columna del item vecino en el orden de Haiku (si ese vecino esta en Sonnet)
            col = None
            if vecino is not None:
                par = next((jj for ii, jj, _ in parejas if A[ii] is vecino), None)
                col = B[par].get("columna") if par is not None else vecino.get("columna")
            nuevo = {"columna": col, "encabezado_columna": "", "texto": e["texto_correcto"].strip(), "_origen": "haiku_verificado"}
            pos = (next((n_ for n_, d in enumerate(final["desempenos"]) if par is not None and d["texto"] == B[par]["texto"]), -1) + 1
                   if vecino is not None and par is not None else len(final["desempenos"]))
            final["desempenos"].insert(pos, nuevo)
            cambios.append({"tipo": "agregado_de_haiku", "despues": nuevo["texto"], "columna": col})
        elif cid.startswith("s") and ver == "no_aparece":
            k = int(cid[1:])
            texto = B[sb[k]]["texto"]
            final["desempenos"] = [d for d in final["desempenos"] if d["texto"] != texto]
            cambios.append({"tipo": "eliminado_de_sonnet", "antes_sonnet": texto})
    return final, uso


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--haiku", required=True)
    ap.add_argument("--sonnet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default="")
    ap.add_argument("--model", default="us.anthropic.claude-sonnet-4-6")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(args.pdf)
    client = boto3.client("bedrock-runtime", region_name=args.region,
                          config=Config(read_timeout=120, retries={"max_attempts": 3, "mode": "adaptive"}))
    solo = {int(x) for x in args.pages.split(",") if x} if args.pages else None
    paginas = []
    for f in sorted(Path(args.sonnet).glob("p*.json")):
        n = int(f.stem[1:])
        if (solo is None or n in solo) and not (out / f.name).exists():
            paginas.append((n, json.loads((Path(args.haiku) / f.name).read_text(encoding="utf-8")),
                            json.loads(f.read_text(encoding="utf-8"))))
    print(f"{len(paginas)} paginas por arbitrar", flush=True)

    tin = tout = fallos = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        for n, h, s in paginas:
            *_, conf, _, solo_h, solo_s = preparar(h, s)
            jpeg = renderizar(pdf, n, 1.6, 80) if (conf or solo_h or solo_s or preparar_extras(h, s)) else b""
            futs[ex.submit(procesar_pagina, client, args.model, jpeg, n, h, s)] = n
        for k, f in enumerate(as_completed(futs), 1):
            n = futs[f]
            try:
                final, uso = f.result()
                (out / f"p{n:04d}.json").write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")
                tin += uso.get("inputTokens", 0) if uso else 0
                tout += uso.get("outputTokens", 0) if uso else 0
                a = final["_arbitraje"]
                print(f"[{k}/{len(paginas)}] p{n} preguntas={a['preguntas']} cambios={len(a['cambios'])} "
                      f"tercera_lectura={len(a['tercera_lectura'])}", flush=True)
            except Exception as e:
                fallos += 1
                print(f"[{k}/{len(paginas)}] p{n} FALLO: {e}", file=sys.stderr, flush=True)
    print(f"TOTAL tokens in={tin} out={tout} fallos={fallos}")


if __name__ == "__main__":
    main()
