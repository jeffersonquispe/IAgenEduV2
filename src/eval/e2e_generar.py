# eval/e2e_generar.py
"""
Genera la Unidad Didactica de cada caso bajo tres condiciones y guarda texto + tokens usados.

  sin_rag    : el generador no recibe contexto recuperado (lo que escribiria el modelo "de memoria")
  rag_previo : el RAG antes de este trabajo (puntaje por palabras clave sobre los JSON de resumen)
  rag_nuevo  : recuperacion estructurada del Programa Curricular + BM25 complementario

Usa la MISMA etapa generadora que la app activa (GeneratorAgent.construir_prompt_unidad + BedrockClient.invocar_stream
con sus valores por defecto: Sonnet, max_tokens=8000, temperature=0.7, como generation_service); no corre el validador ni
el formateador, para aislar el efecto del RAG.

Uso (desde la raiz del repo):
    python -m src.eval.e2e_generar --casos c01,c02 --condiciones sin_rag,rag_previo,rag_nuevo
"""
import argparse
import io
import json
import os
import time
from pathlib import Path

from .e2e_casos import CASOS, CASO_POR_ID, competencias_para_wizard

SALIDA = Path(__file__).parent / "resultados" / "e2e"
CONDICIONES = ("sin_rag", "rag_previo", "rag_nuevo")


class _MedidorDeTokens:
    """Envuelve client.invoke_model_with_response_stream para registrar tokens y motivo de parada del stream sin alterar
    lo que recibe invocar_stream (que es lo que usa la app activa)."""

    def __init__(self, client):
        self._original = client.invoke_model_with_response_stream
        self.entrada = self.salida = self.llamadas = 0
        self.stop_reason = None
        client.invoke_model_with_response_stream = self

    def __call__(self, **kw):
        resp = self._original(**kw)
        self.llamadas += 1

        def copia():
            for evento in resp["body"]:
                chunk = evento.get("chunk")
                if chunk:
                    d = json.loads(chunk["bytes"])
                    if d.get("type") == "message_start":
                        self.entrada += d.get("message", {}).get("usage", {}).get("input_tokens", 0)
                    elif d.get("type") == "message_delta":
                        self.salida += d.get("usage", {}).get("output_tokens", 0)
                        self.stop_reason = d.get("delta", {}).get("stop_reason") or self.stop_reason
                yield evento

        return {**resp, "body": copia()}


def _servicio_rag(condicion: str):
    """RAGEducativoService configurado para la condicion (el entorno se lee al construirlo)."""
    from ..core.rag_service import RAGEducativoService
    previos = {k: os.environ.get(k) for k in ("RAG_ESTRUCTURADO", "RAG_COMPLEMENTARIO_BM25")}
    try:
        if condicion == "rag_previo":
            os.environ["RAG_ESTRUCTURADO"] = os.environ["RAG_COMPLEMENTARIO_BM25"] = "0"
        else:
            os.environ.pop("RAG_ESTRUCTURADO", None)
            os.environ.pop("RAG_COMPLEMENTARIO_BM25", None)
        return RAGEducativoService()
    finally:
        for k, v in previos.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def generar(caso_id: str, condicion: str, sobrescribir: bool = False) -> dict:
    from ..agents.generator_agent import GeneratorAgent
    caso = CASO_POR_ID[caso_id]
    SALIDA.mkdir(parents=True, exist_ok=True)
    base = SALIDA / f"{caso_id}_{condicion}"
    if base.with_suffix(".json").exists() and not sobrescribir:
        return json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))

    agente = GeneratorAgent()
    if condicion == "sin_rag":
        agente._buscar_contexto_rag = lambda *a, **k: ""
    else:
        agente.rag_service = _servicio_rag(condicion)
    medidor = _MedidorDeTokens(agente.bedrock.client)

    competencias = competencias_para_wizard(caso)
    prompt = agente.construir_prompt_unidad(area_curricular=caso.area, grado=caso.grado,
                                            competencia_referencia=competencias, temas=caso.tema, num_sesiones=6)
    t0 = time.perf_counter()
    # igual que generation_service: invocar_stream con sus valores por defecto (modelo Sonnet, 8000 tokens, temperatura 0.7)
    texto = "".join(agente.bedrock.invocar_stream(prompt))
    meta = {"caso": caso_id, "condicion": condicion, "segundos": round(time.perf_counter() - t0, 1),
            "tokens_entrada": medidor.entrada, "tokens_salida": medidor.salida, "llamadas": medidor.llamadas, "stop_reason": medidor.stop_reason,
            "chars_prompt": len(prompt), "chars_contexto_rag": prompt.split("\n\n", 1)[0].count("") if prompt.startswith("CONTEXTO OFICIAL") else 0,
            "con_contexto": prompt.startswith("CONTEXTO OFICIAL DEL MINEDU"), "modelo": agente.bedrock.CLAUDE_SONNET}
    base.with_suffix(".md").write_text(texto, encoding="utf-8")
    base.with_name(base.name + "_prompt.txt").write_text(prompt, encoding="utf-8")
    base.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", default=",".join(c.id for c in CASOS))
    ap.add_argument("--condiciones", default=",".join(CONDICIONES))
    ap.add_argument("--sobrescribir", action="store_true")
    args = ap.parse_args()
    tin = tout = 0
    for cid in args.casos.split(","):
        for cond in args.condiciones.split(","):
            m = generar(cid, cond, args.sobrescribir)
            tin += m["tokens_entrada"]; tout += m["tokens_salida"]
            print(f"{cid} {cond:<10} {m['segundos']:>5}s  in={m['tokens_entrada']:>6} out={m['tokens_salida']:>5} {m.get('stop_reason')} "
                  f"prompt={m['chars_prompt']:>6} chars  contexto={'si' if m['con_contexto'] else 'no'}", flush=True)
    print(f"TOTAL tokens in={tin} out={tout}")


if __name__ == "__main__":
    main()
