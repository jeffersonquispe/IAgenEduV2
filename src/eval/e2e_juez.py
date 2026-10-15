# eval/e2e_juez.py
"""
Juez de la evaluacion de extremo a extremo: Claude califica cada documento de 0 a 3 en cuatro criterios, con la referencia
oficial (competencias, capacidades y desempenos del grado) a la vista. NO sabe con que condicion se genero el documento.

Solo se le entregan las secciones que el RAG puede influir (situacion significativa y propositos de aprendizaje), para
acotar costo y que el juicio no se diluya en el resto de la unidad.

Limitaciones que el informe debe repetir: el juez es el mismo modelo que genera (puede preferir su propio estilo) y
una sola calificacion por documento a temperatura 0, sin validacion humana.

Uso:  python -m src.eval.e2e_juez
"""
import json
import re
from pathlib import Path

from ..core.bedrock_client import BedrockClient
from .e2e_casos import CASO_POR_ID, CASOS
from .e2e_puntuar import CONDICIONES, SALIDA, Referencia, celda_propositos

CRITERIOS = {
    "competencias": "Las competencias nombradas son competencias oficiales del CNEB del área y coinciden con las pedidas "
                    "(si el docente no pidió ninguna: son pertinentes al área y al tema).",
    "capacidades": "Las capacidades listadas son las oficiales de esas competencias (no inventadas ni de otra competencia).",
    "desempenos_grado": "Los desempeños corresponden al grado indicado: guardan relación con los desempeños oficiales de ESE "
                        "grado de la referencia, no son de otro grado ni son inventados sin base oficial.",
    "coherencia": "Hay coherencia entre competencia, capacidades, desempeños, criterios de evaluación y el tema de la unidad.",
}

PROMPT = """Eres un evaluador experto del Currículo Nacional de la Educación Básica (CNEB) de Perú, nivel secundaria.
Califica el DOCUMENTO frente a la REFERENCIA OFICIAL. No sabes cómo se generó; juzga solo el texto.

DATOS DEL PEDIDO
- Área: {area} | Grado: {grado}° de secundaria | Tema: {tema}
- Competencias pedidas por el docente: {pedidas}

REFERENCIA OFICIAL (Programa Curricular de Educación Secundaria, MINEDU 2016)
{referencia}

DOCUMENTO A EVALUAR (extracto: situación significativa y propósitos de aprendizaje)
{documento}

Califica de 0 a 3 cada criterio (0 = no cumple, 1 = cumple poco, 2 = cumple en general con fallas, 3 = cumple plenamente):
{criterios}

Responde SOLO con JSON, sin texto adicional:
{{"competencias": {{"puntaje": <0-3>, "motivo": "<una frase>"}}, "capacidades": {{...}}, "desempenos_grado": {{...}}, "coherencia": {{...}}}}"""


def _referencia_texto(ref: Referencia, caso) -> str:
    comps = ref.competencias_esperadas(caso)
    ciclo = "VI" if caso.grado <= 2 else "VII"
    bloques = []
    for c in comps:
        caps = next((ch["text"] for ch in ref.rec.chunks if ch.get("tipo") == "competencia" and ch["competencia"] == c
                     and ch.get("ciclo") in (ciclo, None) and "Capacidades:" in ch["text"]), "")
        caps = caps.split("Capacidades:", 1)[-1].split("Nivel esperado", 1)[0].strip() if caps else "(no disponible)"
        des = "\n".join(f"  - {d}" for d in ref._desemp.get((c, caso.grado), []))
        bloques.append(f"Competencia: {c}\nCapacidades oficiales:\n{caps}\nDesempeños oficiales de {caso.grado}°:\n{des}")
    return "\n\n".join(bloques)


def _extracto(doc: str) -> str:
    m = re.search(r"\|\s*\**\s*II\.\s*SITUACI[ÓO]N SIGNIFICATIVA.*?(?=\|\s*\**\s*IV\.|\Z)", doc, re.S | re.I)
    texto = m.group(0) if m else celda_propositos(doc)
    return texto[:7000]


def _json(texto: str) -> dict:
    return json.loads(texto[texto.find("{"): texto.rfind("}") + 1])


def juzgar(ref: Referencia, cliente: BedrockClient, caso_id: str, condicion: str) -> dict:
    destino = SALIDA / f"{caso_id}_{condicion}_juez.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    caso = CASO_POR_ID[caso_id]
    doc = (SALIDA / f"{caso_id}_{condicion}.md").read_text(encoding="utf-8")
    prompt = PROMPT.format(
        area=caso.area, grado=caso.grado, tema=caso.tema,
        pedidas="; ".join(caso.competencias) if caso.competencias else "ninguna (el sistema debía seleccionarlas del área)",
        referencia=_referencia_texto(ref, caso), documento=_extracto(doc),
        criterios="\n".join(f"- {k}: {v}" for k, v in CRITERIOS.items()))
    ultimo = None
    for _ in range(3):
        try:
            r = _json(cliente.invocar(prompt=prompt, max_tokens=900, temperature=0.0))
            puntajes = {k: int(r[k]["puntaje"]) for k in CRITERIOS}
            assert all(0 <= v <= 3 for v in puntajes.values())
            salida = {"caso": caso_id, "condicion": condicion, "puntajes": puntajes,
                      "total": sum(puntajes.values()), "motivos": {k: r[k].get("motivo", "") for k in CRITERIOS}}
            destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
            return salida
        except Exception as e:  # JSON mal formado o puntaje fuera de rango: reintentar
            ultimo = e
    raise RuntimeError(f"{caso_id}/{condicion}: {ultimo}")


def main():
    ref = Referencia()
    cliente = BedrockClient()
    for c in CASOS:
        for cond in CONDICIONES:
            if not (SALIDA / f"{c.id}_{cond}.md").exists():
                continue
            r = juzgar(ref, cliente, c.id, cond)
            print(f"{c.id} {cond:<10} {r['puntajes']}  total={r['total']}", flush=True)


if __name__ == "__main__":
    main()
