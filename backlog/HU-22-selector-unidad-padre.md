# HU-22: Selector de unidad padre al crear una Sesión

**Épica:** Generación | **Prioridad:** Alta | **Esfuerzo:** S

**Como** docente, **quiero** elegir la unidad didáctica ya generada a la que pertenece una nueva Sesión de Aprendizaje desde una lista, **para** no tener que copiar el título manualmente ni arriesgarme a errores de tipeo que rompan la vinculación entre ambos documentos.

## Contexto

Limitación ya documentada en `docs/DETALLES_TECNICOS.md` §15. Hoy, en el paso 2 del wizard para Sesión, el docente escribe a mano el "Título de Unidad" (`titulo_unidad`) que se envía a `POST /generate/sesion`. Si no coincide exactamente con una unidad ya generada, se pierde la vinculación real entre ambos documentos.

## Criterios de aceptación

- El paso 2 del wizard de Sesión (`GenerationWizard.jsx`) muestra un selector con las unidades didácticas (`type = "unidad"`) ya generadas por el usuario, en vez de un campo de texto libre.
- Al elegir una unidad, se reutilizan sus competencias (`competencias_unidad`) automáticamente en vez de tener que reintroducirlas.
- Se guarda una relación explícita entre la Sesión creada y el `Document.id` de la unidad elegida (hoy `Document` no tiene ese vínculo — evaluar agregar `parent_document_id` o similar).
- Sigue siendo posible crear una Sesión sin unidad asociada (caso de uso válido si el docente aún no generó la unidad en el sistema).

**Archivos relevantes:** `frontend/src/components/GenerationWizard.jsx`, `src/api/routes/data.py` (para exponer las unidades del usuario), `src/api/models.py`
