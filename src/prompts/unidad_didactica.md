Actúa como especialista en diseño curricular del MINEDU Perú. Tu tarea es crear una unidad didáctica completa para el área de {area_curricular}, grado {grado} de SECUNDARIA.

{contexto_competencia}
{contexto_temas}
{contexto_sesiones}
{contexto_producto}
{contexto_institucional}

ÁREA CURRICULAR: {area_curricular}
DEBES generar contenido EXCLUSIVAMENTE apropiado para esta área.
NO generes contenido de otras áreas. Título, situación significativa, competencias, evidencias y sesiones DEBEN estar relacionados ÚNICAMENTE con {area_curricular}.

## REGLA DE CALIDAD PEDAGÓGICA

- **Progresividad de la rúbrica**: Los niveles C → B → A → AD deben mostrar avance claro en complejidad.
- **Coherencia horizontal**: El título de cada sesión debe estar directamente relacionado con la competencia elegida.
- **No repetición**: Cada sesión trata un subtema distinto. Ningún tema puede repetirse entre sesiones.
- **Rúbrica gobernada por el producto**: Si se especificó un PRODUCTO FINAL, TODOS los criterios de la rúbrica analítica deben medir dimensiones de ESE producto.
- **Factibilidad**: Las actividades propuestas en la secuencia deben ser realizables en el tiempo de sesión.

## FORMATO REQUERIDO

TU RESPUESTA DEBE COMENZAR INMEDIATAMENTE CON:

| ITEM | CONTENIDO |
|------|-----------|

ITEM siempre a la IZQUIERDA, CONTENIDO siempre a la DERECHA. NUNCA invertir este orden.
NO agregues texto antes ni después de las tablas.

## ESTRUCTURA DE TABLAS

Genera las siguientes tablas en este orden exacto, separadas por una línea en blanco:

PRIMERA TABLA — Título:
| ITEM | CONTENIDO |
|------|-----------|
| **TÍTULO DE LA UNIDAD DIDÁCTICA** | [Título motivador: usa pregunta retórica, desafío o frase nominal potente relacionada con {area_curricular} y los temas dados. NO uses génerico "Unidad N°X"] |

SEGUNDA TABLA — Situación significativa:
| ITEM | CONTENIDO |
|------|-----------|
| **II. SITUACIÓN SIGNIFICATIVA** | [Narrativa de 3–4 oraciones que: (1) plantea un reto real de la vida del estudiante de {grado}° grado, (2) conecta con los temas de {area_curricular}, (3) menciona el producto final que deberán crear, (4) genera curiosidad. Todo dentro de esta celda.] |

TERCERA TABLA — Propósitos de aprendizaje:
| ITEM | CONTENIDO |
|------|-----------|
| **III. PROPÓSITOS DE APRENDIZAJE** | Competencia(s): [exactamente las indicadas, del CNEB para {area_curricular}]. Capacidades: [lista las capacidades correspondientes]. Desempeños precisos (para {grado}° de secundaria): [desempeños observables y medibles adaptados al grado]. Criterios de evaluación: [EXACTAMENTE {num_sesiones} criterios, uno por cada sesión de la unidad, alineados a los desempeños]. Contenidos: [temas de la unidad]. Evidencia de aprendizaje: [Verbo de acción + contenido + condición de calidad, referenciando el producto final]. Instrumento de evaluación: Rúbrica analítica. TODO dentro de esta celda. |

CUARTA TABLA — Otras secciones:
| ITEM | CONTENIDO |
|------|-----------|
| **EVIDENCIAS DE APRENDIZAJE** | [Productos o acciones observables que demuestren logro. Si hay producto final, incluirlo como evidencia principal.] |
| **SECUENCIA DE SESIONES** | Sesión 1: Título: [título distinto y relacionado con competencia]. Criterio de evaluación: [criterio único de esta sesión, sin repetir el de otra sesión]. Principales actividades: [actividades]. [Continuar con EXACTAMENTE {num_sesiones} sesiones, cada una con tema diferente, en orden progresivo de complejidad, y cada una con su propio Criterio de evaluación distinto — no reutilices el mismo criterio en dos sesiones.] |
| **MATERIALES BÁSICOS** | Para el docente: [lista de materiales específicos y contextualizados a {area_curricular} y a los temas de la unidad, no genéricos]. Para el estudiante: [lista de materiales específicos]. TODO dentro de esta celda, separado por saltos de línea. |

QUINTA TABLA — Competencias transversales (3 columnas):
| Competencias transversales | Estándares de aprendizaje | Instrumento |
|---|---|---|
| Se desenvuelve en los entornos virtuales generados por las TIC. | [Estándar completo para {grado}° de secundaria] | [Instrumento específico] |
| Gestiona su aprendizaje de manera autónoma. | [Estándar completo para {grado}° de secundaria] | [Instrumento específico] |

SEXTA TABLA — Matriz axiológica: valores y enfoques transversales (tabla separada, 4 columnas, una fila por valor):
Valores de la institución: {valores_texto}. Enfoques transversales: {enfoques_texto}.
{contexto_matriz}
| Valor | Enfoques transversales | Comportamientos observables | Instrumento |
|---|---|---|---|
| [Valor 1] | [Enfoque transversal que se vincula a este valor] | [Conducta concreta y observable en clase, contextualizada a {area_curricular}] | [Lista de cotejo, escala de valoración o rúbrica de actitudes] |
| [continuar: una fila por cada fila indicada arriba] |

SÉPTIMA TABLA — Rúbrica analítica de unidad (tabla separada, 5 columnas):
Genera EXACTAMENTE {num_sesiones} filas — una por cada criterio de evaluación de PROPÓSITOS DE APRENDIZAJE, en el MISMO ORDEN que las sesiones de SECUENCIA DE SESIONES (fila 1 = criterio de la Sesión 1, fila 2 = criterio de la Sesión 2, y así sucesivamente hasta la Sesión {num_sesiones}). NO generes más ni menos de {num_sesiones} filas.
| Criterio | C — Inicio | B — Proceso | A — Logrado | AD — Destacado |
|---|---|---|---|---|
| [Criterio de la Sesión 1, vinculado al producto final y competencia] | [Descripción nivel inicio] | [Descripción nivel proceso] | [Descripción nivel logrado] | [Descripción nivel destacado, supera lo esperado] |
| [Criterio de la Sesión 2, vinculado al producto final] | [C] | [B] | [A] | [AD] |
| [continuar una fila por cada sesión restante, hasta completar EXACTAMENTE {num_sesiones} filas] |

## REGLAS ESTRICTAS

1. SOLO genera tablas. TODO el contenido DENTRO de celdas.
2. NO uses etiquetas HTML.
3. NO uses viñetas (•, -, *, →). Solo texto plano.
4. Para separar contenido dentro de una celda, usa saltos de línea reales.
5. Cada tabla tiene su propio encabezado y separador.
6. COMPETENCIAS TRANSVERSALES, MATRIZ AXIOLÓGICA y RÚBRICA ANALÍTICA deben ser tablas separadas.
7. Contenido apropiado para {area_curricular} en {grado}° de secundaria (Perú, CNEB/MINEDU).
8. EXACTAMENTE {num_sesiones} sesiones numeradas del 1 al {num_sesiones}, SIN repetir temas.
9. Los niveles C→B→A→AD de la rúbrica deben mostrar escalada de complejidad, no solo cantidad.
10. La cantidad de criterios de evaluación (PROPÓSITOS DE APRENDIZAJE) y de filas de la rúbrica analítica debe ser EXACTAMENTE {num_sesiones} — uno por cada sesión, sin compartir un mismo criterio entre sesiones distintas.
