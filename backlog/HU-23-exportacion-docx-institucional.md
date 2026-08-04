# HU-23: Exportación DOCX con estilos institucionales

**Épica:** Exportación | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** que el DOCX exportado tenga el formato institucional del MINEDU (tablas, encabezados, tipografía), **para** poder entregarlo directamente sin tener que darle formato manualmente en Word.

## Contexto

Limitación ya documentada en `docs/DETALLES_TECNICOS.md` §15: `POST /export/docx` (`src/api/routes/export.py`) genera un DOCX simplificado sin estilos institucionales. Sin embargo, **la lógica que sí produce ese formato ya existe** en el proyecto: `src/app/docx_generator.py`, usada por la app Streamlit legacy.

## Criterios de aceptación

- `POST /export/docx` produce un documento con el mismo nivel de formato (tablas con estilo, encabezados, numeración) que ya genera `docx_generator.py` para Streamlit.
- El resultado distingue Unidad vs. Sesión igual que ya hace `POST /export/pdf` (por las claves presentes en `Document.content`).
- No se regresa a duplicar la lógica: portar/reutilizar `docx_generator.py` en vez de reescribirla desde cero en `export.py`.

## Notas de implementación

- `src/app/docx_generator.py` hoy solo tiene `crear_documento_unidad_didactica()` (Unidad Didáctica) — **no existe** una función equivalente para Sesión, habría que construirla desde cero siguiendo el mismo patrón de estilos.
- `crear_documento_unidad_didactica()` recibe varios parámetros ya parseados (`sesiones_data`, `competencias_trans_data`, `propositos_data`, etc.), no el `content` JSON tal como lo guarda `Document`. Se necesita una capa de adaptación entre `Document.content` (JSON con texto Markdown por sección) y esos parámetros estructurados antes de poder reutilizar la función.
- Evaluar si conviene refactorizar `docx_generator.py` para aceptar el `content` JSON directamente, ya que sería el punto de entrada común tanto para el export de la app FastAPI como para la app Streamlit legacy.

**Archivos relevantes:** `src/api/routes/export.py`, `src/app/docx_generator.py`
