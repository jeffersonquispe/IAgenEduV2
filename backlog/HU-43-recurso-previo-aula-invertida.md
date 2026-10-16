# HU-43: Adjuntar recurso previo (enlace) para sesiones con metodología Aula Invertida

**Épica:** Generación / Metodología | **Prioridad:** Baja | **Esfuerzo:** S

**Como** docente, **quiero** poder pegar el enlace del video o lectura que mis estudiantes revisarán antes de clase al elegir la metodología Aula Invertida, **para** que la sesión generada lo incluya como recurso real en vez de una referencia genérica.

## Contexto

`Sesión de Aprendizaje ejm.docx`, Tabla 4 (Inicio), incluye un enlace real como parte del material previo de Aula Invertida: *"Fase de Aula Invertida. En casa: Los estudiantes revisan en casa los fundamentos conceptuales – Observan un video corto... https://www.youtube.com/watch?v=Tu9OQSff-gw&t=11s"*.

El wizard actual (`GenerationWizard.jsx`, líneas 374-376) solo ofrece el selector "Metodología Activa" (ERCA/ABP/Aula Invertida) sin ningún campo para adjuntar el recurso previo. El prompt (`sesion_aprendizaje.md`, líneas 24-26) por eso solo puede describir genéricamente *"lectura/vídeo previo asignado"* — no recibe ningún dato real que citar.

## Criterios de aceptación

- Cuando se elige "Aula Invertida" en el wizard, aparece un campo opcional "Recurso previo (enlace)".
- Si se provee, el valor viaja como variable nueva al prompt (ej. `{recurso_previo}`) y `sesion_aprendizaje.md` lo cita textualmente en el INICIO en vez de generar una referencia genérica.
- Si se deja vacío, el comportamiento es el actual (sin regresión): el modelo redacta una referencia genérica al material previo.

**Archivos relevantes:** `frontend/src/components/GenerationWizard.jsx`, `src/prompts/sesion_aprendizaje.md`, `src/agents/generator_agent.py` (`_construir_contexto_metodologia()`)

**Fuente:** `Sesión de Aprendizaje ejm.docx` (Tabla 4, Inicio)
