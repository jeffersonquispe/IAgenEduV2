## Métricas para evaluar la efectividad del proyecto

Este documento propone métricas (cuantitativas y cualitativas) para evaluar la efectividad del **Generador Educativo AI** a nivel pedagógico, de uso, de calidad de IA y de operación técnica.

---


## 2. Calidad pedagógica de las unidades y sesiones

- **2.1. Alineamiento con el Currículo Nacional (CNEB)**
  - **Definición**: Porcentaje de documentos generados que cumplen criterios de alineamiento (competencias, capacidades, desempeños, enfoques transversales).
  - **Medición**:
    - Rúbrica de revisión experta (0–3 o 0–4) en criterios como:
      - Correspondencia con competencia oficial
      - Coherencia competencia–capacidades–desempeños
      - Inclusión de enfoques transversales pertinentes
    - \( \text{Índice de alineamiento} = \frac{\sum \text{puntuaciones rúbrica}}{\text{puntuación máxima posible}} \)

- **2.2. Claridad y precisión de desempeños**
  - **Definición**: Medida de cuán observables, medibles y pertinentes son los desempeños generados.
  - **Medición**:
    - Revisión experta con rúbrica (claridad, observabilidad, nivel de reto).
    - Encuesta a docentes (Likert 1–5) sobre:
      - “Los desempeños son claros y observables en el aula”.

- **2.3. Coherencia de la secuencia didáctica**
  - **Definición**: Grado en que Inicio–Desarrollo–Cierre están conectados con la situación significativa y la competencia.
  - **Medición**:
    - Rúbrica con criterios:
      - Inicio vincula saberes previos y contexto
      - Desarrollo moviliza la competencia
      - Cierre incluye reflexión y transferencia

- **2.4. Uso real en aula**
  - **Definición**: Porcentaje de unidades/sesiones generadas que se implementan efectivamente en clase.
  - **Fuente**: Encuestas/reportes de docentes.
  - **Fórmula**:  
    - \( \text{\% de documentos implementados} = \frac{\# \text{documentos usados en aula}}{\# \text{documentos generados}} \times 100 \)

---

## 3. Calidad del contenido generado por IA

- **3.1. Satisfacción general del docente**
  - **Definición**: Evaluación subjetiva de la utilidad del contenido generado.
  - **Medición**:
    - Encuesta Likert 1–5 después de generar o mejorar un documento:
      - “El documento generado es útil para mi planificación”.
      - “El tiempo que me ahorra compensa el tiempo de revisión”.

- **3.2. Necesidad de edición posterior**
  - **Definición**: Cuánto tiene que corregir/modificar el docente.
  - **Métricas posibles**:
    - % de secciones aceptadas sin cambios mayores.
    - Tiempo promedio de edición por documento (autorreporte o telemetría básica).

- **3.3. Consistencia terminológica y de formato**
  - **Definición**: Cumplimiento de estructuras esperadas (tablas, formato ITEM–CONTENIDO, campos obligatorios).
  - **Medición**:
    - Validadores automáticos (scripts) que:
      - Revisan si la tabla principal tiene todas las columnas.
      - Comprueban que las tablas auxiliares respetan `| ITEM | CONTENIDO |`.
    - KPIs:
      - % de documentos que pasan validación automática sin correcciones.

- **3.4. Uso efectivo del RAG**
  - **Definición**: Medida de cuánto contenido generado hace referencia correcta a normas/competencias oficiales.
  - **Medición**:
    - Muestreo de documentos generados con RAG.
    - Revisión experta para verificar:
      - Citas coherentes a currículo, orientaciones y sesiones de capacitación.
      - Ausencia de contradicciones con el CNEB.

---

## 5. Métricas de RAG y cobertura de conocimiento

- **5.1. Cobertura de fuentes relevantes**
  - **Definición**: Porcentaje de consultas cuyo contexto RAG incluye al menos un fragmento de:
    - Currículo oficial
    - Orientaciones CNEB
    - Sesiones EF/EPT
    - Módulo de enfoque por competencias
  - **Medición**:
    - Logging de `documentos` devueltos por `RAGEducativoService.buscar_contexto_curricular`.
    - Cálculo de distribución de fuentes por consulta.

- **5.2. Profundidad del contexto**
  - **Definición**: Número medio de documentos/chunks usados para construir el contexto.
  - **Fórmula**:  
    - \( \text{profundidad media} = \frac{\sum \text{\# documentos en contexto}}{\# \text{consultas RAG}} \)

- **5.3. Relevancia percibida del contexto**
  - **Definición**: Qué tan útiles consideran los docentes las referencias a fuentes oficiales.
  - **Medición**:
    - Encuesta breve en generación RAG:
      - “El contenido estaba bien respaldado en normativa oficial” (1–5).

### 5.A Métricas de recuperación (offline, con set de oro)

Miden el retriever aislado del LLM. Implementadas en `src/eval/metrics.py`; se ejecutan con
`python -m src.eval.run_retrieval_eval` sobre `src/eval/gold_retrieval.json`.

**Set de oro**: consultas con los chunks relevantes etiquetados (relevancia 2 = responde directo, 1 = apoyo).
Dos tipos: `pipeline` (consultas con el formato real que arma `GeneratorAgent._buscar_contexto_rag`) y
`natural` (preguntas libres sobre pedagogía/metodologías). Cada consulta se etiqueta por duplicado
(dos revisores) y se reporta el acuerdo (kappa de Cohen) antes de usar el set.

| Métrica | Pregunta que responde | Fórmula |
|---|---|---|
| **Hit@k** | ¿Apareció al menos un chunk relevante en el top-k? | 1 si \|top-k ∩ rel\| ≥ 1 |
| **Recall@k** | ¿Qué fracción de lo relevante se recuperó? | \|top-k ∩ rel\| / \|rel\| |
| **Precision@k** | ¿Cuánto del contexto es útil (inverso del ruido)? | \|top-k ∩ rel\| / k |
| **MRR** | ¿Qué tan arriba está el primer relevante? | 1 / rango del primero |
| **nDCG@k** | ¿Están bien ordenados, premiando los de relevancia 2? | DCG@k / IDCG@k, ganancia 2^rel − 1 |
| **Fuentes@5** | ¿El contexto es diverso o se concentra en un documento? | n.º de fuentes distintas en top-5 |
| **Latencia** | Costo del retriever | ms por consulta |

**k de referencia: 5**, porque `GeneratorAgent` y `RAGEducativoService` solo pasan `docs[:5]` al prompt.
Recall@10 y nDCG@10 se reportan como techo (lo que el retriever *podría* entregar con otro corte).
Un `Recall@10` alto con `Recall@5` bajo indica un problema de ordenamiento, no de cobertura.

### 5.B Métricas de grounding (end-to-end, requieren LLM)

Miden si el contexto recuperado se usa bien. Son manuales o con LLM-as-judge, sobre una muestra de documentos generados.

| Métrica | Definición |
|---|---|
| **Context precision (juez)** | % de los 5 chunks inyectados que el juez considera pertinentes a la consulta. |
| **Faithfulness** | % de afirmaciones normativas del documento (competencia, enfoque, estándar) que están respaldadas por algún chunk inyectado. |
| **Tasa de alucinación curricular** | % de competencias/capacidades/desempeños citados que no existen en el CNEB (verificable contra `competencias_curriculares.py`). |
| **Utilización de contexto** | % de chunks inyectados cuyo contenido se refleja en el documento. |
| **Ablación RAG** | Diferencia en rúbrica de alineamiento (2.1) y en tasa de alucinación entre generar con RAG, sin RAG y con contexto aleatorio. |

### 5.C Protocolo de comparación

1. Mismo set de oro y mismo `k` para todas las estrategias (baseline léxico actual, BM25, Bedrock KB híbrido, variantes con filtros/grafo).
2. Reportar media por tipo de consulta (`pipeline` vs `natural`), no solo global.
3. Con 25 consultas las diferencias pequeñas no son concluyentes: reportar intervalo de confianza (bootstrap sobre consultas) o prueba de Wilcoxon pareada, y ampliar el set a ≥ 50–100 consultas antes de afirmar mejoras.
4. Sin Bedrock KB configurada no se puede medir esa estrategia: añadirla a `retrievers.py` cuando exista `BEDROCK_KB_CURRICULO_ID`.

### 5.D Métricas para consultas curriculares estructuradas

Set `gold_estructurado.json` (68 consultas = 34 temas × 2 variantes: formato real del pipeline y solo el tema).
La relevancia sale de metadatos del corpus (área, grado, ciclo, competencia), no de lectura subjetiva; lo único
manual es qué competencia corresponde a cada tema, y debe validarlo un docente.

| Métrica | Definición |
|---|---|
| **hit_obj@k / mrr_obj** | ¿Apareció el chunk de desempeños de la competencia objetivo **en el grado correcto** (relevancia 2)? Aísla lo esencial sin contar competencia/estándar (relevancia 1). |
| **grado_mal@5** | Fracción de desempeños en el top-5 que son de otro grado. Mide el error pedagógicamente más grave. |
| **area_mal@5** | Fracción de chunks con área distinta a la pedida. |

**Nivel del azar (obligatorio al citar resultados).** Con área y grado conocidos hay solo 1–4 desempeños candidatos
(media 2.85). Un orden aleatorio da hit_obj@1 = 0.38, @2 = 0.73, @3 = 0.96, @5 = 1.00. Por eso **hit_obj@3 y @5 no
discriminan**: solo hit_obj@1 y mrr_obj miden si el ordenamiento aporta algo sobre el azar.

**Limitaciones conocidas de esta evaluación:**
- El set es favorable a estrategias que usan metadatos: en producción el asistente ya conoce área, grado y, en el
  caso del wizard, la competencia elegida; con la competencia conocida la recuperación de desempeños es un lookup exacto.
- Recall@k y ndcg incluyen competencia y estándar como relevantes, que es justo lo que agrega el grafo curricular
  (circularidad). Para juzgar el grafo usar hit_obj y la calidad del documento generado, no recall.
- No se midió Bedrock KB ni recuperación por embeddings, y no hay evaluación end-to-end (¿mejora el documento?).

---
