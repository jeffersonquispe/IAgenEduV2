# Tablas de la evaluación de extremo a extremo (generadas por `python -m src.eval.e2e_informe`)

Casos completos en las tres condiciones: **12**.

### Medidas automáticas contra el Programa Curricular

| Medida | sin_rag | rag_previo | rag_nuevo |
|---|---|---|---|
| solape léxico con los desempeños oficiales del grado (`solape_grado`) | 0.102 | 0.100 | 0.355 |
| margen frente a otros grados (`margen_grado`) | -0.007 | 0.001 | 0.150 |
| desempeños más cercanos al grado pedido (azar 0.20) (`grado_primero`) | 0.201 | 0.336 | 0.700 |
| cobertura de lo oficial del grado (`cobertura`) | 0.063 | 0.059 | 0.220 |
| competencias nombradas: precisión (`comp_precision`) | 1.000 | 1.000 | 1.000 |
| competencias pedidas que aparecen: recall (solo si el docente las eligió) (`comp_recall`) | 1.000 | 1.000 | 1.000 |

### Medidas automáticas: diferencia `rag_nuevo` − otra condición (media pareada, IC 95% bootstrap)

| Medida | vs | diferencia | IC 95% | casos que mejoran / empeoran |
|---|---|---|---|---|
| `solape_grado` | sin_rag | +0.253 | [+0.171, +0.357] | 12 / 0 de 12 |
| `solape_grado` | rag_previo | +0.255 | [+0.172, +0.359] | 12 / 0 de 12 |
| `margen_grado` | sin_rag | +0.157 | [+0.073, +0.266] | 12 / 0 de 12 |
| `margen_grado` | rag_previo | +0.149 | [+0.065, +0.259] | 12 / 0 de 12 |
| `grado_primero` | sin_rag | +0.499 | [+0.343, +0.646] | 11 / 0 de 12 |
| `grado_primero` | rag_previo | +0.364 | [+0.208, +0.525] | 9 / 0 de 12 |
| `cobertura` | sin_rag | +0.157 | [+0.094, +0.252] | 12 / 0 de 12 |
| `cobertura` | rag_previo | +0.161 | [+0.091, +0.259] | 12 / 0 de 12 |
| `comp_precision` | sin_rag | +0.000 | [+0.000, +0.000] | 0 / 0 de 12 |
| `comp_precision` | rag_previo | +0.000 | [+0.000, +0.000] | 0 / 0 de 12 |
| `comp_recall` | sin_rag | +0.000 | [+0.000, +0.000] | 0 / 0 de 9 |
| `comp_recall` | rag_previo | +0.000 | [+0.000, +0.000] | 0 / 0 de 9 |

### Juez (0 a 3 por criterio; total 0 a 12)

| Medida | sin_rag | rag_previo | rag_nuevo |
|---|---|---|---|
| juez: competencias (`competencias`) | 3.000 | 3.000 | 3.000 |
| juez: capacidades (`capacidades`) | 2.667 | 2.750 | 2.917 |
| juez: desempenos_grado (`desempenos_grado`) | 2.083 | 1.917 | 2.417 |
| juez: coherencia (`coherencia`) | 2.750 | 2.833 | 3.000 |
| juez: total (`total`) | 10.500 | 10.500 | 11.333 |

### Juez: diferencia `rag_nuevo` − otra condición (media pareada, IC 95% bootstrap)

| Medida | vs | diferencia | IC 95% | casos que mejoran / empeoran |
|---|---|---|---|---|
| `competencias` | sin_rag | +0.000 | [+0.000, +0.000] | 0 / 0 de 12 |
| `competencias` | rag_previo | +0.000 | [+0.000, +0.000] | 0 / 0 de 12 |
| `capacidades` | sin_rag | +0.250 | [-0.083, +0.583] | 4 / 1 de 12 |
| `capacidades` | rag_previo | +0.167 | [-0.167, +0.583] | 2 / 1 de 12 |
| `desempenos_grado` | sin_rag | +0.333 | [+0.083, +0.583] | 4 / 0 de 12 |
| `desempenos_grado` | rag_previo | +0.500 | [+0.250, +0.750] | 6 / 0 de 12 |
| `coherencia` | sin_rag | +0.250 | [+0.000, +0.500] | 3 / 0 de 12 |
| `coherencia` | rag_previo | +0.167 | [+0.000, +0.417] | 2 / 0 de 12 |
| `total` | sin_rag | +0.833 | [+0.417, +1.250] | 8 / 0 de 12 |
| `total` | rag_previo | +0.833 | [+0.250, +1.417] | 8 / 1 de 12 |

### Por escenario de uso (medidas automáticas: `solape_grado` y `grado_primero`)

| Escenario | n | sin_rag: solape / grado_primero | rag_previo: solape / grado_primero | rag_nuevo: solape / grado_primero |
|---|---|---|---|---|
| 1comp | 6 | 0.09 / 0.19 | 0.09 / 0.34 | 0.33 / 0.68 |
| 2comp | 3 | 0.14 / 0.11 | 0.11 / 0.33 | 0.38 / 0.72 |
| sin_comp | 3 | 0.08 / 0.31 | 0.10 / 0.33 | 0.38 / 0.72 |

### Costo, tamaño y tiempo de la generación

| Condición | tokens de entrada (media) | tokens de salida (media) | caracteres del prompt (media) | segundos (media) | costo medio por documento | terminó (`end_turn`) |
|---|---|---|---|---|---|---|
| sin_rag | 3042 | 6405 | 9461 | 63 | US$0.105 | 12/12 |
| rag_previo | 4042 | 6249 | 12470 | 60 | US$0.106 | 12/12 |
| rag_nuevo | 5654 | 6822 | 18624 | 66 | US$0.119 | 12/12 |

Costo total de generar todos los documentos: **US$3.96** (tarifa asumida: US$3.0/M entrada, US$15.0/M salida).
