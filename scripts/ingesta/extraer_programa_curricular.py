#!/usr/bin/env python3
"""
Extrae el Programa Curricular de Educacion Secundaria (PDF escaneado, sin capa de texto)
a JSON por pagina usando Claude con vision en Amazon Bedrock (API Converse).

Cada pagina se guarda en <out>/p0001.json (reanudable: omite las ya extraidas).
Registra tokens de entrada/salida para estimar costo.

Requisitos (fuera del venv del proyecto):  pip install pypdfium2 boto3 pillow
Uso:
  python scripts/ingesta/extraer_programa_curricular.py --pdf RUTA.pdf --out data/raw/programa_curricular \
      --pages 6,71,131 --model us.anthropic.claude-haiku-4-5-20251001-v1:0
  python scripts/ingesta/extraer_programa_curricular.py --pdf RUTA.pdf --out data/raw/programa_curricular   # todas
"""
import argparse
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import pypdfium2 as pdfium
from botocore.config import Config

PROMPT = """Esta imagen es una pagina del "Programa Curricular de Educacion Secundaria" (Peru, MINEDU 2016), escaneada.
Transcribe su contenido a JSON, con tildes y enes correctas, SIN inventar ni resumir nada. Responde SOLO con el JSON.

Esquema:
{
  "numero_pagina_impreso": <numero impreso al pie, o null>,
  "tipo": "desempenos" | "estandares" | "competencia_capacidades" | "narrativa" | "otro",
  "area": <nombre del area curricular si aparece, o null>,
  "competencia": <nombre exacto de la competencia, o null>,
  "ciclo": <"VI" o "VII" si aparece en la cabecera, o null>,
  "capacidades": [<texto de cada capacidad, si la pagina las lista>],
  "descripcion_nivel": <descripcion del nivel esperado al final del ciclo, o null>,
  "desempenos": [ {"columna": <posicion de la columna de izquierda a derecha: 1 = la mas a la izquierda, 2 = la siguiente...>, "encabezado_columna": <encabezado EXACTO, copiado literal, de la columna donde esta, ej. "DESEMPEÑOS PRIMER GRADO DE SECUNDARIA"; cadena vacia "" si esta pagina NO imprime encabezado (la tabla continua de la pagina anterior)>, "texto": <un desempeno, completo>} ],
  "estandares": [ {"nivel": <ej. "Nivel esperado al final del ciclo VI">, "texto": <descripcion>} ],
  "texto": <para tipo narrativa/otro: transcripcion fiel en parrafos; si no, null>,
  "continua_de_pagina_anterior": <true si el contenido empieza a mitad de una seccion sin cabecera>
}
Reglas:
- Cada vineta de una columna "DESEMPEÑOS <GRADO> GRADO DE SECUNDARIA" es UN elemento de "desempenos". Copia el encabezado de su columna LITERALMENTE; no lo conviertas a numero ni lo deduzcas.
- Si hay varias columnas (p. ej. tercer y cuarto grado), no mezcles columnas.
- Las notas al pie no van en los textos.
- Ignora el sello, la marca "649-2016-MINEDU" y el numero de pagina.
- Si un dato no esta visible en esta pagina, usa null o lista vacia; no lo deduzcas de otras paginas."""


def _json_de(texto: str) -> dict:
    i, j = texto.find("{"), texto.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("sin JSON en la respuesta")
    return json.loads(texto[i:j + 1])


def renderizar(pdf, num: int, scale: float, quality: int) -> bytes:
    """pdfium no es thread-safe: renderizar siempre desde el hilo principal."""
    img = pdf[num - 1].render(scale=scale).to_pil().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def extraer_pagina(client, jpeg: bytes, num: int, model: str) -> dict:
    ultimo = None
    for intento in range(4):
        try:
            # tras un JSON invalido (comillas internas sin escapar) el reintento lo pide explicitamente
            # y sube un poco la temperatura: con 0 repetiria exactamente el mismo error
            extra = "" if intento == 0 else (
                "\nIMPORTANTE: tu respuesta anterior no fue JSON valido. Dentro de los textos escapa cada comilla "
                'doble como \\" (o usa comillas angulares «»), y no dejes comas finales.')
            r = client.converse(
                modelId=model,
                messages=[{"role": "user", "content": [
                    {"image": {"format": "jpeg", "source": {"bytes": jpeg}}},
                    {"text": PROMPT + extra},
                ]}],
                inferenceConfig={"maxTokens": 6000, "temperature": 0 if intento == 0 else 0.2},
            )
            texto = r["output"]["message"]["content"][0]["text"]
            datos = _json_de(texto)
            datos["_pdf_pagina"] = num
            datos["_uso"] = r.get("usage", {})
            datos["_modelo"] = model
            return datos
        except Exception as e:  # throttling o JSON mal formado: reintentar con espera
            ultimo = e
            time.sleep(2 ** intento)
    raise RuntimeError(f"pagina {num}: {ultimo}")


def parse_pages(spec: str, total: int):
    if not spec:
        return list(range(1, total + 1))
    out = []
    for parte in spec.split(","):
        if "-" in parte:
            a, b = parte.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(parte))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default="", help="ej. 6,71,100-110 (1-indexado); vacio = todas")
    ap.add_argument("--model", default="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--scale", type=float, default=1.6)
    ap.add_argument("--quality", type=int, default=80)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(args.pdf)
    paginas = [p for p in parse_pages(args.pages, len(pdf)) if not (out / f"p{p:04d}.json").exists()]
    print(f"{len(paginas)} paginas por extraer con {args.model}", flush=True)

    client = boto3.client("bedrock-runtime", region_name=args.region,
                          config=Config(read_timeout=120, retries={"max_attempts": 3, "mode": "adaptive"}))
    tin = tout = fallos = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        for p in paginas:  # render en serie (rapido); solo la llamada a Bedrock va en paralelo
            futs[ex.submit(extraer_pagina, client, renderizar(pdf, p, args.scale, args.quality), p, args.model)] = p
        for n, f in enumerate(as_completed(futs), 1):
            p = futs[f]
            try:
                d = f.result()
                (out / f"p{p:04d}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
                u = d.get("_uso", {})
                tin += u.get("inputTokens", 0)
                tout += u.get("outputTokens", 0)
                print(f"[{n}/{len(paginas)}] p{p} tipo={d.get('tipo')} desemp={len(d.get('desempenos') or [])} "
                      f"est={len(d.get('estandares') or [])} in={u.get('inputTokens')} out={u.get('outputTokens')}", flush=True)
            except Exception as e:
                fallos += 1
                print(f"[{n}/{len(paginas)}] p{p} FALLO: {e}", file=sys.stderr, flush=True)
    print(f"TOTAL tokens in={tin} out={tout} fallos={fallos}")


if __name__ == "__main__":
    main()
