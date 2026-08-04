# HU-32: Inyectar el contexto institucional en el pipeline de generación

**Épica:** Generación / Calidad del contenido | **Prioridad:** Media | **Esfuerzo:** S-M

**Como** docente, **quiero** que la Situación Significativa y los ejemplos del documento generado reflejen la realidad de mi institución (visión, contexto de mis estudiantes), **para** recibir un documento más pertinente que uno genérico.

## Contexto

**Depende de HU-31** (el perfil institucional debe existir antes de poder usarse). Hoy el prompt de generación (`src/prompts/unidad_didactica.md`, `sesion_aprendizaje.md`) recibe únicamente variables curriculares — no hay forma de que el modelo sepa si el colegio es rural o urbano, cuál es su visión, o qué caracteriza a sus estudiantes. Eso hace que la "Situación Significativa" generada sea genérica en vez de contextualizada.

## Criterios de aceptación

- `GenerationService.crear_unidad()`/`crear_sesion()` obtienen el `InstitutionProfile` del usuario actual (si existe) y arman un bloque `contexto_institucional`.
- `PromptManager.cargar()` recibe esa variable nueva; `unidad_didactica.md` y `sesion_aprendizaje.md` la usan con una instrucción explícita (p. ej. "considera el siguiente contexto institucional al redactar la situación significativa: {contexto_institucional}").
- Si el docente no tiene perfil institucional configurado, el bloque queda vacío — **mismo comportamiento actual, sin regresión** (igual patrón que ya usa `contexto_producto` cuando `producto_final` no se especifica).
- El camino de streaming (`/generate/unidad/stream`, que construye el prompt manualmente en `GenerationService.generar_unidad_stream_events`) también incorpora la variable, para no reabrir la divergencia ya documentada entre ambos caminos (ver hoja A-2 del diagrama de arquitectura).

## Notas de implementación

- No implementar esta historia antes que HU-31 — no hay de dónde leer el contexto institucional sin el modelo de datos.
- Cuidado con el tamaño del prompt: si `contexto_relevante` es muy largo, considerar un límite razonable de caracteres para no inflar el costo/latencia de cada llamada a Bedrock.

**Archivos relevantes:** `src/api/services/generation_service.py`, `src/core/prompt_manager.py`, `src/prompts/unidad_didactica.md`, `src/prompts/sesion_aprendizaje.md`, `src/agents/generator_agent.py`

**Depende de:** **HU-31**
