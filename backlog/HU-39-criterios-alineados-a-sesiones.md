# HU-39: Alinear el número de criterios de evaluación (y filas de rúbrica) con el número de sesiones de la Unidad

**Épica:** Generación / Calidad del contenido | **Prioridad:** Alta | **Esfuerzo:** S-M

**Como** docente, **quiero** que la Unidad Didáctica genere tantos criterios de evaluación (y filas de rúbrica analítica) como sesiones solicité, con cada sesión referenciando de forma unívoca su propio criterio, **para** mantener la relación 1:1 entre evaluación y sesiones que exige la planificación institucional.

## Contexto

La reunión de planificación docente concluyó explícitamente: *"Relación Criterios-Sesiones: existe una relación directa entre los criterios de evaluación creados y el número de sesiones (por ejemplo, si hay seis criterios, se plantean aproximadamente seis sesiones)."* `Unidad ejemplo.docx` lo confirma en la práctica: Tabla 3 tiene 4 criterios de evaluación y Tabla 5 tiene exactamente 4 sesiones, cada una citando su criterio correspondiente.

Sin embargo, `src/prompts/unidad_didactica.md` pide un número **fijo** de criterios independiente de `{num_sesiones}`:
- Línea 47 (TERCERA TABLA — Propósitos): *"Criterios de evaluación: [3 criterios alineados a los desempeños]"* — hardcodeado a 3.
- Líneas 62-67 (SEXTA TABLA — Rúbrica analítica): exactamente 3 filas de criterio hardcodeadas en la plantilla del prompt.

El wizard (`GenerationWizard.jsx` línea 39) tiene **`num_sesiones: 6`** como valor por defecto — es decir, en el caso más común hoy (6 sesiones) el documento igual pide solo 3 criterios/filas de rúbrica, rompiendo la relación 1:1 que exige el lineamiento.

## Criterios de aceptación

- `unidad_didactica.md` solicita exactamente `{num_sesiones}` criterios de evaluación, no un número fijo.
- La rúbrica analítica (SEXTA TABLA) genera exactamente `{num_sesiones}` filas, una por criterio.
- Cada sesión de la SECUENCIA DE SESIONES referencia el criterio que le corresponde, sin criterios compartidos entre sesiones distintas.
- `StructureValidator` incorpora una verificación (`ADVERTENCIA`) que compara la cantidad de filas de la rúbrica/criterios contra `num_sesiones` y marca discrepancia.

## Notas de implementación

- Reutilizar `extraer_titulos_sesiones()` (`src/utils/table_utils.py`), ya usado por **HU-29** para parsear la secuencia de sesiones, como base para contar filas/criterios de forma consistente.

**Archivos relevantes:** `src/prompts/unidad_didactica.md` (líneas 44-47, 62-67), `src/validators/structure_validator.py`, `src/utils/table_utils.py`

**Depende de / relaciona con:** HU-29
**Fuente:** notas de la reunión de planificación docente — "Relación Criterios-Sesiones"; `Lineamientos.docx`; `Unidad ejemplo.docx` (Tablas 3 y 5)
