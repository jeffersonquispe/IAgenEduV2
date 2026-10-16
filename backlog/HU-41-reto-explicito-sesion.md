# HU-41: Campo "Reto" explícito en la Situación Significativa de la Sesión de Aprendizaje

**Épica:** Generación / Estructura del documento | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** que la sesión generada incluya una pregunta-reto explícita y diferenciada dentro de la situación significativa, **para** plantear el desafío de la clase con claridad a mis estudiantes, en vez de tener que extraerlo yo mismo del párrafo narrativo.

## Contexto

`Sesión de Aprendizaje ejm.docx`, Tabla 2, tiene columnas separadas **"Situación significativa | Reto | Reto sugerido"** — el reto es una pregunta explícita citada aparte (ej. *"¿Cómo podemos transformar un problema real de nuestra comunidad educativa en una solución digital concreta utilizando la lógica de programación?"*).

`src/prompts/sesion_aprendizaje.md` (línea 58) solo pide que la situación significativa *"genere una pregunta o reto implícito"* dentro del mismo párrafo — no como campo propio. Esto choca con uno de los objetivos declarados en la reunión de planificación: *"Incorporar el carisma institucional: integrar el reto de identificar problemas reales desde la lógica de programación y el carisma salesiano."* Sin un campo de Reto explícito, ese objetivo queda diluido en la narrativa.

## Criterios de aceptación

- `sesion_aprendizaje.md` agrega un campo **"RETO"** separado de "SITUACIÓN SIGNIFICATIVA", redactado como pregunta directa dirigida al estudiante.
- El campo se muestra como sección propia en `Editor.jsx` y en la exportación, no incrustado en el párrafo de situación significativa.
- `StructureValidator.SECCIONES_SESION` incorpora la verificación del nuevo campo.

**Archivos relevantes:** `src/prompts/sesion_aprendizaje.md`, `src/validators/structure_validator.py` (`SECCIONES_SESION`), `frontend/src/pages/Editor.jsx`

**Depende de / relaciona con:** HU-32 — el Reto es donde el contexto/carisma institucional se vuelve más visible en el documento.
**Fuente:** `Sesión de Aprendizaje ejm.docx` (Tabla 2, columnas "Reto"/"Reto sugerido"); objetivo de reunión "Incorporar el carisma institucional"
