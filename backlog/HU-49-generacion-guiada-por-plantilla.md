# HU-49: Generación de contenido guiada por la plantilla institucional activa

**Épica:** Generación / Plantillas institucionales | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** que la IA genere el contenido siguiendo exactamente las tablas y columnas de la plantilla que subí, **para** no recibir secciones que mi institución no usa, o que falten secciones que sí usa.

## Contexto

**Depende de HU-48** (la plantilla debe existir y estar parseada en un esquema antes de poder usarse). Hoy `PromptManager.cargar()` (`src/core/prompt_manager.py`) siempre carga el prompt estático `unidad_didactica.md`/`sesion_aprendizaje.md`, y `StructureValidator` siempre valida contra `SECCIONES_UNIDAD`/`SECCIONES_SESION` fijas. Ninguno de los dos sabe que puede existir una plantilla distinta subida por el docente.

## Criterios de aceptación

- Si el docente tiene una plantilla activa (HU-48) para el tipo de documento que está generando, `PromptManager` construye el prompt combinando: (a) las reglas pedagógicas fijas que ya existen (progresividad de rúbrica, no repetición de temas, coherencia con la metodología, etc.) y (b) la estructura de tablas/columnas del esquema de la plantilla, en vez de la estructura fija de los `.md` actuales.
- Las celdas de instrucción/placeholder detectadas en HU-48 (ej. "Hay que recordar que los criterios se desprenden de los estándares...") se usan como **instrucción para la IA**, no como contenido a repetir literalmente en el documento generado.
- Si el docente **no** tiene plantilla subida, el comportamiento es exactamente el actual (prompts `.md` fijos) — sin regresión.
- `StructureValidator` valida contra las secciones/tablas de la plantilla activa cuando existe una, en vez de las constantes hardcodeadas.
- El camino de streaming (`/generate/unidad/stream`, que construye el prompt manualmente — ver nota de arquitectura en HU-32) también respeta la plantilla activa, para no reabrir la divergencia ya conocida entre ambos caminos de generación.

## Notas de implementación

- Cuidado con el tamaño de prompt si la plantilla tiene muchas tablas/columnas — considerar un límite razonable, igual que ya advierte HU-32 para `contexto_relevante`.
- Este HU es el que hace que "cambiar de plantilla" cambie de verdad lo que la IA genera; HU-48 solo la almacena y la interpreta.

**Archivos relevantes:** `src/core/prompt_manager.py`, `src/validators/structure_validator.py`, `src/agents/generator_agent.py`, `src/api/services/generation_service.py`

**Depende de:** HU-48
**Fuente:** solicitud de funcionalidad de plantillas personalizables; `Unidad didáctica(3).docx`, `Sesión de Aprendizaje(1).docx`
