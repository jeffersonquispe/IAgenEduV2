# Resultados de la evaluación de recuperación (RAG)

Ejecutada el 2026-10-15 sobre el commit `6d414ff` (rama `version2`).
Reproducir: `python -m src.eval.run_retrieval_eval` · Datos crudos por consulta: `src/eval/resultados/recuperacion_2026-10-15.json`
(salida de texto: `recuperacion_2026-10-15.txt`). Métricas definidas en `docs/METRICAS_EFECTIVIDAD.md` §5.A–5.E.

## Qué se comparó

| Estrategia | Qué es |
|---|---|
| `baseline` | el recuperador que había antes: puntaje por palabras clave sobre los JSON de resumen (con el corpus nuevo añadido al final) |
| `baseline_prog1o` | igual, pero con el corpus nuevo en primer lugar (descarta un artefacto de orden de fuentes) |
| `bm25` | BM25 sin tildes ni stopwords |
| `bm25_grafo` | BM25 + expansión por un grafo genérico de keywords compartidas |
| `bm25_meta` | BM25 + filtro duro por área, grado y ciclo |
| `bm25_meta_grafo` | lo anterior + grafo curricular tipado (los vecinos compiten por rango) |
| **`servicio`** | **el `RAGEducativoService` real**: desempeños del grado + capacidades + estándar del ciclo, y después contexto complementario con BM25 |
| `servicio_con_competencia` | igual, pasando la competencia elegida en el wizard (búsqueda exacta) |

## A. Programación curricular — 34 temas en el formato real del pipeline

Oro derivado de metadatos (`gold_estructurado.json`). **Azar: hit_obj@1 = 0.38** (hay 1 a 4 desempeños candidatos por área y grado).
`hit_obj@1`: el desempeño del grado correcto sale primero. `grado equivocado`: fracción de desempeños del top-5 que son de otro grado.

| Estrategia | hit_obj@1 | mrr_obj | recall@5 | grado equivocado |
|---|---|---|---|---|
| baseline | 0.00 | 0.00 | 0.00 | — |
| baseline_prog1o | 0.15 | 0.36 | 0.23 | 81% |
| bm25 | 0.12 | 0.28 | 0.31 | 82% |
| bm25_grafo | 0.15 | 0.31 | 0.25 | 80% |
| bm25_meta | 0.35 | 0.54 | 0.58 | 0% |
| bm25_meta_grafo | 0.09 | 0.28 | 0.76 | 0% |
| **servicio** | **0.74** | **0.85** | 0.77 | **0%** |
| servicio_con_competencia | 1.00 | 1.00 | 1.00 | 0% |

Con solo el tema como consulta (otros 34 casos): `servicio` hit_obj@1 = 0.76; `baseline_prog1o` 0.65 pero con 19% de desempeños de otro grado;
`bm25` 0.06 con 79% de otro grado.

## B. Pedagogía y metodologías — 19 consultas libres

| Estrategia | hit@5 | recall@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| baseline | 0.47 | 0.35 | 0.46 | 0.36 |
| bm25 | 1.00 | 0.77 | 0.91 | 0.78 |
| bm25_grafo | 0.79 | 0.60 | 0.71 | 0.57 |
| **servicio** | **1.00** | **0.78** | **0.95** | **0.83** |

Latencia por consulta: baseline ≈ 21 ms, BM25 ≈ 1 ms, servicio ≈ 1 ms.

## Cómo leerlo

- Sin filtrar por metadatos, ~80% de los desempeños recuperados son de otro grado; el filtro lo elimina.
- El grafo no mejora lo esencial (hit_obj@1 baja de 0.35 a 0.09): sube `recall@5` solo porque el oro cuenta como relevantes la
  competencia y el estándar, que son justo lo que el grafo agrega (circular).
- Con 1 a 4 candidatos, un orden aleatorio ya da hit@3 = 0.96 y hit@5 = 1.00: esas métricas no distinguen; solo lo hace el primer puesto.
- `servicio_con_competencia` es una búsqueda exacta por construcción, no un hallazgo.

## Límites

- Los sets los armó el autor (la competencia objetivo de cada tema y la relevancia en pedagogía), sin validación de un docente.
- 34 temas × 2 variantes y 19 consultas libres: las diferencias pequeñas no son concluyentes.
- No se midieron embeddings ni Bedrock KB. El baseline varía ±0.03 entre corridas por un defecto de determinismo de ese código (suma puntajes en orden de `set`): estas cifras son las del JSON guardado, y una corrida anterior dio 0.12 en lugar de 0.15 para `baseline_prog1o`.
- Esta evaluación mide solo la recuperación; la evaluación de extremo a extremo (documento generado) está en `docs/EVALUACION_E2E.md`.
