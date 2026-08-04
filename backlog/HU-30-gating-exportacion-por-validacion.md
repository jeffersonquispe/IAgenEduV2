# HU-30: Bloquear la exportación si el documento no pasa la validación estructural

**Épica:** Calidad / Exportación | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** que el sistema me advierta o me impida descargar un documento con errores estructurales críticos, **para** no entregar accidentalmente un archivo incompleto o mal formado a mi institución.

## Contexto

`docs/FLUJO_APLICATIVO(2).md` §6 afirma: *"Validación Final: El botón de descarga solo aparece si el 'Motor de Reglas' confirma que la tabla generada es consistente y no contiene errores de estructura."*

Hoy esto **no ocurre**: el pipeline sí calcula `ValidationReport.es_valido`/`puntaje` durante la generación (`AgentCoordinator` → `PipelineMetrics`) y lo persiste en la tabla `pipeline_runs`, pero:
- Esa información **no viaja en la respuesta JSON** de `POST /generate/unidad` / `/generate/sesion` (`src/api/routes/generation.py`) — solo se guarda en base de datos.
- `Editor.jsx` no la consulta en absoluto: los botones "Exportar DOCX"/"Exportar PDF" (`handleExport`) están siempre habilitados, sin condicionarse a ningún resultado de validación.

## Criterios de aceptación

- `POST /generate/unidad` y `POST /generate/sesion` incluyen en su respuesta el resultado de validación (`es_valido`, `puntaje_validacion`, `errores_criticos`), no solo el contenido parseado.
- `Editor.jsx` deshabilita (o exige una confirmación explícita antes de permitir) los botones de exportación cuando el documento generado tiene `errores_criticos > 0`, mostrando al docente qué sección(es) fallaron.
- Después de un refinamiento con IA (`POST /generate/refine`) que corrija el problema, el estado de validación se actualiza para reflejar el nuevo resultado.

## Notas de implementación

- Definir si la validación se re-ejecuta automáticamente tras cada edición **manual** de una sección (costoso: implica volver a correr `StructureValidator`/`ContentValidator` en cada guardado) o si solo se actualiza tras pasos que ya pasan por el pipeline de IA (generación inicial y refinamiento). Se recomienda la segunda opción para no penalizar la edición libre del docente con validaciones constantes.
- Evitar un bloqueo total sin salida: si el docente necesita exportar igual pese a advertencias (p. ej. para revisión interna), permitir "exportar de todas formas" con la advertencia visible, en vez de deshabilitar el botón sin alternativa.

**Archivos relevantes:** `src/api/routes/generation.py`, `src/agents/coordinator.py` (`PipelineMetrics`), `frontend/src/pages/Editor.jsx`

**Fuente:** `docs/FLUJO_APLICATIVO(2).md` §6
