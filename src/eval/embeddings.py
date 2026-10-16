# eval/embeddings.py
"""
Embeddings de Amazon Bedrock para el experimento hibrido (BM25 + vectores), con cache en disco.

El cache (src/eval/resultados/cache_embeddings/, ignorado por git) hace que repetir el experimento no vuelva a llamar a
Bedrock. Costo orientativo: ~0.3 M tokens por modelo para los ~800 chunks, es decir centavos.

Modelos (todos habilitados en la cuenta del proyecto):
  titan_v2     amazon.titan-embed-text-v2:0      1024 dim, multilingue
  titan_v1     amazon.titan-embed-text-v1        1536 dim; es el que declara scripts/aws/kb-config.json
  cohere_multi cohere.embed-multilingual-v3      1024 dim, multilingue, distingue documento y consulta
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import boto3
import numpy as np
from botocore.config import Config

CACHE = Path(__file__).parent / "resultados" / "cache_embeddings"
MODELOS = {"titan_v2": "amazon.titan-embed-text-v2:0", "titan_v1": "amazon.titan-embed-text-v1",
           "cohere_multi": "cohere.embed-multilingual-v3"}
PRECIO_POR_MILLON = {"titan_v2": 0.02, "titan_v1": 0.10, "cohere_multi": 0.10}   # USD; verificar contra la tarifa vigente
MAX_CHARS = 8000
SALTO = chr(10)


class Embedder:
    def __init__(self, clave: str, region: str = "us-east-1"):
        self.clave, self.modelo = clave, MODELOS[clave]
        self.client = boto3.client("bedrock-runtime", region_name=region,
                                   config=Config(read_timeout=60, retries={"max_attempts": 5, "mode": "adaptive"}))
        self.archivo = CACHE / f"{clave}.npz"
        self._cache = {}
        self.chars_nuevos = 0          # caracteres enviados a Bedrock en esta ejecucion (para estimar costo)
        if self.archivo.exists():
            d = np.load(self.archivo, allow_pickle=False)
            self._cache = dict(zip(d["k"].tolist(), d["v"]))

    # ------------------------------------------------------------------ cache
    @staticmethod
    def _k(texto: str, tipo: str) -> str:
        return hashlib.sha1(f"{tipo}|{texto}".encode("utf-8")).hexdigest()

    def guardar(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        if self._cache:
            np.savez_compressed(self.archivo, k=np.array(list(self._cache)), v=np.stack(list(self._cache.values())).astype(np.float32))

    # ------------------------------------------------------------------ llamadas
    def _titan(self, texto: str) -> np.ndarray:
        cuerpo = {"inputText": texto}
        if self.clave == "titan_v2":
            cuerpo.update({"dimensions": 1024, "normalize": True})
        r = self.client.invoke_model(modelId=self.modelo, body=json.dumps(cuerpo), accept="application/json", contentType="application/json")
        return np.array(json.loads(r["body"].read())["embedding"], dtype=np.float32)

    def _cohere(self, textos: List[str], tipo: str) -> List[np.ndarray]:
        entrada = "search_query" if tipo == "query" else "search_document"
        r = self.client.invoke_model(modelId=self.modelo, accept="application/json", contentType="application/json",
                                     body=json.dumps({"texts": textos, "input_type": entrada, "truncate": "END"}))
        return [np.array(v, dtype=np.float32) for v in json.loads(r["body"].read())["embeddings"]]

    def embed(self, textos: List[str], tipo: str = "document") -> np.ndarray:
        """Vectores unitarios (n, d), en el orden de `textos`. tipo: 'document' | 'query'."""
        textos = [t[:MAX_CHARS] for t in textos]
        faltan = [t for t in dict.fromkeys(textos) if self._k(t, tipo) not in self._cache]
        if faltan:
            self.chars_nuevos += sum(len(t) for t in faltan)
            if self.clave.startswith("cohere"):
                for i in range(0, len(faltan), 96):
                    lote = faltan[i:i + 96]
                    for t, v in zip(lote, self._cohere(lote, tipo)):
                        self._cache[self._k(t, tipo)] = v
            else:
                with ThreadPoolExecutor(max_workers=8) as ex:
                    for t, v in zip(faltan, ex.map(self._titan, faltan)):
                        self._cache[self._k(t, tipo)] = v
            self.guardar()
        m = np.stack([self._cache[self._k(t, tipo)] for t in textos]).astype(np.float64)
        return m / np.linalg.norm(m, axis=1, keepdims=True)

    def embed_documentos(self, textos: List[str]) -> np.ndarray:
        """Vectores de chunks. Cohere acepta como maximo 2048 caracteres por texto: los chunks mas largos se parten en
        trozos de <= 1800 caracteres (con su titulo) y se promedian; los modelos Titan reciben el chunk completo."""
        if not self.clave.startswith("cohere"):
            return self.embed(textos, "document")
        trozos, dueno = [], []
        for i, t in enumerate(textos):
            titulo, _, resto = t.partition(SALTO)
            actual = titulo
            partes = []
            for linea in (resto.split(SALTO) if resto else [""]):
                while len(linea) > 1500:
                    linea, cola = linea[:1500], linea[1500:]
                    if len(actual) + len(linea) + 1 > 1800:
                        partes.append(actual)
                        actual = titulo
                    actual += SALTO + linea
                    linea = cola
                if len(actual) + len(linea) + 1 > 1800:
                    partes.append(actual)
                    actual = titulo
                actual += SALTO + linea
            partes.append(actual)
            trozos += partes
            dueno += [i] * len(partes)
        E = self.embed(trozos, "document")
        out = np.zeros((len(textos), E.shape[1]))
        for v, i in zip(E, dueno):
            out[i] += v
        return out / np.linalg.norm(out, axis=1, keepdims=True)

    def costo_estimado(self) -> float:
        return self.chars_nuevos / 3.5 / 1e6 * PRECIO_POR_MILLON[self.clave]
