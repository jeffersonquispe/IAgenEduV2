# Experimento híbrido: BM25 + embeddings

Ejecutado el 2026-10-15. Reproducir: `python -m src.eval.run_hibrido` (cuesta centavos la primera vez; luego usa el caché de
`src/eval/resultados/cache_embeddings/`, que no se versiona). Resultados por consulta: `src/eval/resultados/hibrido_2026-10-15.json`;
tablas: `hibrido_2026-10-15.txt`. Código: `src/eval/embeddings.py`, `retrievers_emb.py`, `run_hibrido.py`.

## Pregunta

La recuperación actual no usa embeddings (BM25 más filtros por metadatos). ¿Mejora si se le suman, y dónde?

## Diseño (fijado antes de medir)

- **Modelos de Bedrock** (los tres habilitados en la cuenta), todos reportados sin elegir el mejor después:
  Titan Text Embeddings v2, Titan v1 (el que declara `scripts/aws/kb-config.json`) y Cohere Embed Multilingual v3.
  Cohere admite 2048 caracteres por texto: los chunks más largos se parten en trozos de ≤ 1800 caracteres (con su título) y se promedian.
- **Dónde actúan.** (A) Ordenan los desempeños candidatos del área y grado (el filtro por metadatos se mantiene) y (B) el contexto
  complementario de pedagogía. Se reutiliza el `RecuperadorCurricular` de producción; solo cambia el puntaje (gancho `_puntajes`).
- **Modos:** `denso` (coseno), `rrf` (Reciprocal Rank Fusion, k = 60) y `ponderado` (0.5 · BM25/máx + 0.5 · coseno normalizado min-max).
  Los vectores reciben solo el tema (sin el prefijo «programación curricular… grado secundaria»); el BM25 actual recibe la consulta completa.
- **Controles:** (1) BM25 con solo el tema, para saber si la mejora viene de quitar el prefijo y no de los vectores; (2) los mismos
  puntajes **sin** filtro de metadatos, para saber si los vectores resuelven el error de grado; (3) α = 0.25 y 0.75 como sensibilidad
  (el parámetro principal es 0.5).
- **Estadística:** 68 consultas = 34 temas × 2 variantes, que no son independientes; el intervalo de confianza (bootstrap, 10 000
  remuestreos) se calcula sobre los 34 temas. Azar de `hit_obj@1`: 0.38.

## Resultados

### A. Ordenar los desempeños candidatos (`hit_obj@1`)

| Estrategia | todas (68) | formato del pipeline | solo el tema |
|---|---|---|---|
| BM25 actual | 0.750 | 0.735 | 0.765 |
| BM25 con solo el tema (control) | 0.765 | 0.765 | 0.765 |
| Titan v2: denso / RRF / ponderado | 0.853 / **0.941** / 0.926 | 0.853 / 0.941 / 0.941 | 0.853 / 0.941 / 0.912 |
| Titan v1: denso / RRF / ponderado | 0.912 / 0.897 / 0.912 | 0.912 / 0.912 / 0.912 | 0.912 / 0.882 / 0.912 |
| Cohere: denso / RRF / ponderado | 0.882 / 0.897 / **0.941** | 0.882 / 0.912 / 0.941 | 0.882 / 0.882 / 0.941 |

Diferencia pareada frente al BM25 actual (IC 95 % sobre los 34 temas; consultas que mejoran / empeoran):

| Estrategia | Δ hit_obj@1 | IC | mejoran / empeoran |
|---|---|---|---|
| BM25 con solo el tema (control) | +0.015 | [−0.03, +0.06] | 2 / 1 |
| Titan v2 ponderado | +0.176 | [+0.07, +0.29] | 12 / 0 |
| Titan v2 RRF | +0.191 | [+0.07, +0.32] | 13 / 0 |
| Cohere ponderado | +0.191 | [+0.07, +0.32] | 13 / 0 |
| Titan v1 ponderado | +0.162 | [+0.04, +0.29] | 12 / 1 |
| Titan v2 solo vectores | +0.103 | [−0.04, +0.25] | 11 / 4 |
| Cohere solo vectores | +0.132 | [−0.01, +0.28] | 13 / 4 |

Sensibilidad a α (ponderado): con α = 0.25 los tres modelos dan 0.941; con α = 0.75 dan 0.868 (Titan v2), 0.838 (Titan v1) y 0.882 (Cohere).

### A'. Control sin filtro de metadatos: ¿los vectores evitan el desempeño de otro grado? (top-5)

| Estrategia | desempeños de otro grado |
|---|---|
| BM25 | 81 % |
| solo vectores (Titan v2 / v1 / Cohere) | 79 % / 72 % / 77 % |
| híbridos (RRF y ponderado, los tres modelos) | 76 % a 81 % |

### B. Contexto pedagógico (19 consultas libres)

| Estrategia | hit@5 | recall@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| BM25 actual | 1.00 | 0.78 | 0.95 | 0.83 |
| Titan v2 solo vectores | 1.00 | 0.88 | 1.00 | 0.93 |
| Titan v2 ponderado / RRF | 1.00 | 0.86 / 0.86 | 1.00 / 1.00 | 0.92 / 0.91 |
| Titan v1 solo vectores | 1.00 | 0.89 | 0.97 | 0.91 |
| Cohere ponderado | 1.00 | 0.83 | 0.97 | 0.87 |

### C. Con vectores siempre hay vecinos: ¿se puede descartar el contexto sin contenido pedagógico?

Similitud máxima con el contexto de apoyo, para las 19 consultas pedagógicas frente a los 34 temas curriculares (p. ej. «ecuaciones lineales»):

| Modelo | AUC | con contenido (mín.) | sin contenido (máx.) |
|---|---|---|---|
| Titan v2 | 1.000 | 0.49 | 0.43 |
| Titan v1 | 0.992 | 0.57 | 0.65 |
| Cohere | 0.995 | 0.59 | 0.61 |

Con Titan v2 hay una separación limpia en esta muestra; con los otros dos los rangos se solapan un poco.

### D. Dónde falla el mejor híbrido (Titan v2 ponderado): 5 de 68 consultas, 3 temas

- «textos argumentativos»: sale *Lee diversos tipos de textos* en lugar de *Escribe*. El tema admite ambas lecturas; la etiqueta es criterio del autor.
- «la independencia del Perú»: sale *Gestiona responsablemente el espacio y el ambiente* en lugar de *Construye interpretaciones históricas*. Error real.
- «capacidades físicas y condición física»: sale *Interactúa… sociomotrices* en lugar de *Asume una vida saludable*. Competencias cercanas.

### Costo y operación

- Embeddings del corpus: ≈ US$0.004 con Titan v2, ≈ US$0.02 con Titan v1 o Cohere (una vez). Todo el experimento costó menos de US$0.05.
- Latencia de embeber una consulta: Titan v2 mediana 340 ms (máximo 1.1 s); Cohere mediana 970 ms. Frente a ~60 s por generación, es despreciable.
- Vectores del corpus: 625 × 1024 × 4 bytes ≈ 2.5 MB con Titan v2.

## Errores propios corregidos durante el experimento

1. La primera versión de RRF invertía el rango (daba el peor resultado como mejor): `hit_obj@1 = 0.03`, muy por debajo del azar. Se detectó por
   ser absurdo y se corrigió antes de interpretar.
2. El BM25 recibía el prefijo de plantilla y los vectores no, lo que podía inflar la mejora. Se agregó el control (BM25 con solo el tema): +0.015.
3. El intervalo se calculaba sobre 68 consultas como si fueran independientes; se rehízo sobre los 34 temas.

## Conclusiones

1. **Los embeddings sí mejoran el orden de los desempeños candidatos**: de 0.75 a 0.91–0.94 en `hit_obj@1`, con los tres modelos y con
   RRF y ponderado, y sin causa atribuible al prefijo. Los híbridos arreglan entre 10 y 13 consultas y rompen 0 o 1; los vectores solos arreglan
   11 a 15 y rompen 4, y su intervalo incluye el cero. **La fusión rinde más que cualquiera de las dos señales por separado.**
2. **No reemplazan al filtro por metadatos.** Sin filtro, 72 a 81 % de los desempeños son de otro grado, con vectores o sin ellos. Dos desempeños
   de grados distintos son casi iguales en significado.
3. **En el flujo actual el efecto sobre el documento generado probablemente es pequeño**, y no se midió. Con `m = 4` los 4 desempeños candidatos
   (el máximo por área y grado) ya entran todos al prompt, así que ordenarlos mejor solo cambia su posición y cuál competencia aporta sus
   capacidades y su estándar en el quinto puesto. Dónde sí podrían aportar: **sugerir competencias a partir del tema** (acierto en primer puesto de
   0.75 a ≈ 0.93) y **el contexto pedagógico** (recall@5 de 0.78 a 0.83–0.89), este último con un umbral de similitud.
4. **Los modelos no se distinguen entre sí con esta muestra.** Titan v2, Titan v1 y Cohere quedan en 0.91–0.94; Titan v2 es el más barato y rápido, y
   el único con una separación limpia en C.

## Límites

- El oro lo armó el autor: la competencia objetivo de cada tema (y 2 de las 3 fallas de D se deben a ambigüedad de esa etiqueta) y la relevancia
  de pedagogía, sin validación de un docente. 34 temas y 19 consultas libres; en B no hay intervalos.
- La sensibilidad a α muestra que más peso a los vectores rinde algo más, pero eso se vio después de medir: no se adopta α = 0.25 sin validarlo aparte.
- El umbral de similitud (C) se observó en la misma muestra; habría que fijarlo con consultas nuevas.
- Cohere vio los chunks largos partidos y promediados; Titan los vio completos.
- No se midió la generación de extremo a extremo con estos recuperadores ni la Knowledge Base de Bedrock.

## Si se integra

Lo mínimo sería: vectores precalculados del corpus (2.5 MB), una llamada a Bedrock por generación (~340 ms) con **respaldo automático a BM25 si falla**,
fusión ponderada o RRF solo para ordenar dentro del filtro por metadatos, y un umbral de similitud para el contexto complementario. El filtro
por área, grado y competencia se queda como está.
