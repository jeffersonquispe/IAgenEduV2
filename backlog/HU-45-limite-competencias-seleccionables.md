# HU-45: Límite máximo de competencias seleccionables por documento

**Épica:** Generación / Calidad del contenido | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** que el wizard me impida seleccionar más competencias de las recomendadas pedagógicamente, **para** no diluir el foco de la unidad o sesión intentando abarcar demasiadas competencias a la vez.

## Contexto

`Lineamientos.docx` especifica para la Unidad Didáctica: *"Competencia (Máximo hasta 2 competencias)."* El objetivo de la reunión de planificación lo reafirma: *"Focalizar el aprendizaje: no intentar abarcar demasiadas competencias a la vez; el objetivo es elegir una, dos o como máximo tres competencias por sesión."*

Hoy `GenerationWizard.jsx` (líneas 292-304) permite seleccionar cualquier cantidad de competencias del multi-select, sin límite superior — solo muestra un contador informativo (*"N competencia(s) seleccionada(s)"*, línea 304), sin bloquear nada.

## Criterios de aceptación

- El selector de competencias del wizard de Unidad impide marcar más de 2 opciones (deshabilita las restantes o muestra advertencia al intentar una tercera).
- El selector de competencias del wizard de Sesión impide marcar más de 3 opciones.
- El backend valida el mismo límite en `/generate/unidad` y `/generate/sesion` (no confiar solo en la validación de UI), respondiendo `422` si se excede.
- El límite y su razón pedagógica quedan visibles como texto de ayuda junto al selector, no solo como restricción silenciosa.

**Archivos relevantes:** `frontend/src/components/GenerationWizard.jsx` (líneas 285-304), `src/api/routes/generation.py`

**Fuente:** `Lineamientos.docx` (columna "Competencia (Máximo hasta 2 competencias)"); objetivo de reunión "Focalizar el aprendizaje"
