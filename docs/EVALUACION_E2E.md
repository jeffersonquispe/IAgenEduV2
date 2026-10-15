# Evaluación de extremo a extremo: ¿el RAG mejora la unidad didáctica generada?

Ejecutada el 2026-10-15 (commit base `6d414ff`, rama `version2`). Modelo generador y juez: Claude Sonnet 4.6 en Bedrock.
Código: `src/eval/e2e_*.py` · documentos generados y puntajes: `src/eval/resultados/e2e/` · tablas completas: `informe_tablas.md`.
Reproducir (cuesta ~US$4.5): `python -m src.eval.e2e_generar && python -m src.eval.e2e_juez && python -m src.eval.e2e_informe`.

## Qué se midió

12 casos que cubren 9 de las 11 áreas, los 5 grados y tres escenarios de uso: 6 con una competencia elegida, 3 con dos (el máximo de HU-45)
y 3 sin ninguna (el sistema debe seleccionarlas). Cada caso se generó **una vez** bajo tres condiciones, con la misma etapa generadora que la
app activa (`GeneratorAgent.construir_prompt_unidad` + `invocar_stream`: Sonnet, 8000 tokens, temperatura 0.7), sin validador ni formateador:

| Condición | Contexto que recibe el generador |
|---|---|
| `sin_rag` | ninguno (el modelo escribe de memoria) |
| `rag_previo` | el RAG de antes de este trabajo (puntaje por palabras clave sobre los JSON de resumen) |
| `rag_nuevo` | recuperación estructurada del Programa Curricular + BM25 complementario |

Se evaluó la celda **III. Propósitos de aprendizaje**, que es donde el RAG debería influir (competencias, capacidades y desempeños).

- **Medidas automáticas** contra el Programa Curricular. El modelo no copia los desempeños oficiales, los adapta al tema, así que no hay umbral
  de copia: se usa el solapamiento léxico continuo (Jaccard de palabras de contenido) de cada desempeño generado con los oficiales de cada grado.
  `grado_primero` es la fracción de desempeños cuyo mejor solape es con el grado **pedido** frente a los otros cuatro (azar: 0.20).
- **Juez**: Claude califica de 0 a 3 en cuatro criterios con la referencia oficial a la vista y sin saber la condición.

## Resultados (n = 12 casos; diferencia `rag_nuevo` − otra condición, IC 95% bootstrap sobre los casos)

| Medida | sin_rag | rag_previo | rag_nuevo | Δ vs sin_rag [IC] | Δ vs rag_previo [IC] | casos que mejoran / empeoran |
|---|---|---|---|---|---|---|
| solape léxico con los oficiales del grado | 0.10 | 0.10 | **0.36** | +0.25 [+0.17, +0.36] | +0.26 [+0.17, +0.36] | 12/0 en ambas |
| margen frente a otros grados | −0.01 | 0.00 | **+0.15** | +0.16 [+0.07, +0.27] | +0.15 [+0.07, +0.26] | 12/0 en ambas |
| `grado_primero` (azar 0.20) | 0.20 | 0.34 | **0.70** | +0.50 [+0.34, +0.65] | +0.36 [+0.21, +0.53] | 11/0 y 9/0 |
| cobertura de lo oficial del grado | 0.06 | 0.06 | **0.22** | +0.16 [+0.09, +0.25] | +0.16 [+0.09, +0.26] | 12/0 en ambas |
| competencias: precisión / recall | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 0 | 0 | sin diferencias |
| **juez: desempeños del grado** (0–3) | 2.08 | 1.92 | **2.42** | +0.33 [+0.08, +0.58] | +0.50 [+0.25, +0.75] | 4/0 y 6/0 |
| juez: capacidades | 2.67 | 2.75 | 2.92 | +0.25 [−0.08, +0.58] | +0.17 [−0.17, +0.58] | 4/1 y 2/1 |
| juez: coherencia | 2.75 | 2.83 | 3.00 | +0.25 [0.00, +0.50] | +0.17 [0.00, +0.42] | 3/0 y 2/0 |
| juez: competencias | 3.00 | 3.00 | 3.00 | 0 | 0 | sin diferencias |
| **juez: total** (0–12) | 10.50 | 10.50 | **11.33** | +0.83 [+0.42, +1.25] | +0.83 [+0.25, +1.42] | 8/0 y 8/1 |

Por escenario (solape / `grado_primero`): 1 competencia (n=6) 0.09/0.19 → 0.09/0.34 → **0.33/0.68**; 2 competencias (n=3) 0.14/0.11 → 0.11/0.33 → **0.38/0.72**;
sin competencia (n=3) 0.08/0.31 → 0.10/0.33 → **0.38/0.72** (orden: sin_rag → rag_previo → rag_nuevo).

### Un ejemplo (caso c05: Comunicación 4°, «textos argumentativos», competencia «Escribe diversos tipos de textos»)

- Oficial: «…Ordena las ideas en torno a un tema, las jerarquiza en subtemas e ideas principales, y las desarrolla para contraargumentar o precisar la
  información **sin digresiones o vacíos**…»
- `sin_rag`: «Escribe ensayos argumentativos con una tesis claramente formulada, argumentos desarrollados con evidencias pertinentes y una conclusión coherente…»
  (razonable, pero genérico y no tomado del programa)
- `rag_nuevo`: «Ordena y jerarquiza las ideas en torno a una tesis, desarrollando argumentos y **contraargumentos sin digresiones ni vacíos** de información.»

### Costo, tamaño y tiempo (por documento)

| | tokens de entrada | tokens de salida | prompt (caracteres) | segundos | costo |
|---|---|---|---|---|---|
| sin_rag | 3 042 | 6 405 | 9 461 | 63 | US$0.105 |
| rag_previo | 4 042 | 6 249 | 12 470 | 60 | US$0.106 |
| rag_nuevo | 5 654 | 6 822 | 18 624 | 66 | **US$0.119** |

El RAG nuevo duplica el prompt frente a no usar RAG (+97% de caracteres), pero cuesta **+13%** por documento (la salida domina el costo) y +3 a 6 s.
Los 36 documentos terminaron (`end_turn`). Costo total de la evaluación: ~US$4.7 (generación US$3.96 + piloto descartado US$0.22 + juez ~US$0.5, estimado).

## Cómo leerlo

1. **El RAG nuevo ancla los desempeños en el Programa Curricular y en el grado correcto.** Sin RAG, el grado correcto no sale primero más que por azar
   (0.20); con el RAG previo 0.34; con el RAG nuevo 0.70. Mejora en los 12 casos en las medidas de solapamiento, y el juez, que ve la referencia pero
   no la condición, lo confirma en desempeños del grado (+0.33 a +0.50 sobre 3) y en el total (+0.83 sobre 12).
2. **El RAG previo no mejoró casi nada** frente a no usar RAG: mismo solapamiento y misma nota del juez. Su único efecto medible es un `grado_primero` algo mayor.
3. **El efecto aparece igual en los tres escenarios**, incluido cuando el docente no elige competencia.
4. **Las competencias ya salían bien sin RAG**: ninguna condición nombra competencias fuera de las pedidas (precisión 1.00 en 36 documentos). El modelo conoce
   los nombres del CNEB; lo que no conoce de memoria son los **desempeños por grado**, y ahí está toda la ganancia.

## Límites (importantes)

- **Es una medida de fidelidad al estándar oficial, no de calidad pedagógica global.** Las medidas automáticas y el juez usan la misma referencia que alimenta
  al RAG; que `rag_nuevo` se parezca más al Programa Curricular es lo que se esperaba, y no prueba por sí solo que el documento sea mejor para un docente.
  No se midió utilidad, creatividad ni satisfacción de docentes.
- **n = 12 casos, una generación por caso y temperatura 0.7**: hay ruido de muestreo que no se promedió. Los intervalos bootstrap son orientativos.
- **Efecto techo del juez**: competencias 3.00 en todo, capacidades y coherencia cerca de 3. La nota del juez discrimina poco; la diferencia sale de
  «desempeños del grado». El juez es el mismo modelo que genera (puede preferir su propio estilo) y da una sola nota 0–3 por criterio, sin validación humana.
- **Solo se evaluó la unidad** (sección III); no las sesiones, la rúbrica ni el documento completo, y sin pasar por el validador y el formateador del pipeline.
- **Los casos los eligió el autor** y cubren 9 de las 11 áreas: faltan Castellano como Segunda Lengua y Educación Religiosa.
- Los umbrales y métricas se fijaron tras ver el primer caso (c01) y antes de generar los otros 11. Un detector de nombres de competencia tenía un defecto
  (daba falsos negativos para las tres condiciones por igual); se corrigió y se recalculó antes de interpretar.

## Hallazgo lateral (a verificar)

En el piloto, con `GeneratorAgent.generar_unidad_didactica` (no `invocar_stream`), que pasa `max_tokens=4000`, **las tres unidades se cortaron a mitad de la última
tabla**. La app activa usa `invocar_stream` con 8000 y no se ve afectada, pero ese método de 4000 tokens sigue en `coordinator.generar_unidad_didactica` y
`bedrock_services`. No se investigó si algún flujo actual lo usa; conviene revisarlo.
