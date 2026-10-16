# HU-40: Sección "Materiales Básicos" (docente/estudiante) en la Unidad Didáctica

**Épica:** Generación / Estructura del documento | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** que la Unidad Didáctica generada incluya una sección de materiales básicos separada para el docente y para el estudiante, **para** saber de antemano qué recursos debo preparar y cuáles pedir a mis alumnos, sin redactarla yo mismo.

## Contexto

`Unidad ejemplo.docx` incluye explícitamente la sección **"MATERIALES BÁSICOS PARA UTILIZAR EN LA UNIDAD"**, con dos sub-listas diferenciadas — "PARA EL DOCENTE" (ej. computadora y proyector, guías de algoritmos, rúbricas) y "PARA EL ESTUDIANTE" (ej. cuaderno de trabajo, computadora, entorno de programación).

`src/prompts/unidad_didactica.md` no genera esta sección hoy. En contraste, la Sesión de Aprendizaje **sí** la tiene ("MATERIALES Y RECURSOS", `sesion_aprendizaje.md` línea 62). Se confirma también en el validador: `StructureValidator.SECCIONES_UNIDAD` (líneas 67-75) no incluye `"MATERIALES"`, mientras que `SECCIONES_SESION` (líneas 77-83) sí lo exige.

## Criterios de aceptación

- `unidad_didactica.md` agrega una sección "MATERIALES BÁSICOS" con dos listas diferenciadas (docente / estudiante), contextualizadas al área curricular y a los temas de la unidad.
- `StructureValidator.SECCIONES_UNIDAD` incluye `"MATERIALES"` como sección obligatoria (igual que ya ocurre para Sesión).
- El contenido aparece en la exportación PDF/DOCX de la Unidad y es editable en `Editor.jsx` como cualquier otra sección.

**Archivos relevantes:** `src/prompts/unidad_didactica.md`, `src/validators/structure_validator.py` (`SECCIONES_UNIDAD`), `src/core/pdf_generator.py`

**Fuente:** `Unidad ejemplo.docx` ("MATERIALES BÁSICOS PARA UTILIZAR EN LA UNIDAD")
