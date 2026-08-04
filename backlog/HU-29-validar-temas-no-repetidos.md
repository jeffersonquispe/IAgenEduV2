# HU-29: Validar que no haya temas repetidos entre sesiones de una misma unidad

**Épica:** Calidad del contenido generado | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** que el sistema detecte si dos sesiones de la secuencia generada dentro de una Unidad cubren el mismo tema, **para** no terminar con una planificación que repite contenido en clases distintas.

## Contexto

`docs/FLUJO_APLICATIVO(2).md` §3.1 declara esta regla explícitamente para la Unidad Didáctica: *"Secuencia de Sesiones: (...) No debe haber temas repetidos en sesiones distintas."* Hoy `StructureValidator` (`src/validators/structure_validator.py`) solo valida presencia de secciones, formato de tabla y orden de columnas — **no compara los temas entre las sesiones generadas**.

## Criterios de aceptación

- Al validar una Unidad recién generada (que ya produce una secuencia de N sesiones dentro de un mismo documento), `StructureValidator.validar_unidad_didactica()` incorpora una verificación que extrae el tema/título de cada sesión de la secuencia y marca `ADVERTENCIA` si dos o más son idénticos o muy similares.
- La extracción de títulos de sesión puede apoyarse en `extraer_titulos_sesiones()` (`src/utils/table_utils.py`), que ya existe para otro propósito y hace justamente ese parseo.
- El resultado se refleja en `ValidationReport` igual que cualquier otro error (afecta `puntaje` y aparece en `pipeline_runs` vía `PipelineMetrics`).

## Notas de implementación — alcance en dos fases

- **Fase 1 (esta historia):** solo valida duplicados **dentro de la secuencia de sesiones de una misma Unidad**, ya que hoy esa secuencia completa se genera y guarda en un solo documento (`documents.type = "unidad"`).
- **Fase 2 (fuera de alcance por ahora):** extender la validación para comparar contra Sesiones ya generadas y persistidas como documentos independientes de esa misma Unidad — esto requiere que exista un vínculo explícito Sesión→Unidad, que hoy no existe (ver **HU-22**, selector de unidad padre). No implementar esta fase hasta que HU-22 esté resuelta.

**Archivos relevantes:** `src/validators/structure_validator.py`, `src/utils/table_utils.py`

**Fuente:** `docs/FLUJO_APLICATIVO(2).md` §3.1
