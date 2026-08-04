# HU-28: Campo "Institución Educativa" en la generación de documentos

> **Reemplazada por HU-31 + HU-32.** Aquella pareja de historias cubre esto mismo (nombre de la institución) y además lo amplía a un perfil reutilizable (visión, contexto) que se inyecta en el contenido generado, no solo en el encabezado del archivo exportado. Se deja este archivo como referencia histórica del hallazgo original en `FLUJO_APLICATIVO(2).md`.

**Épica:** Generación / Personalización institucional | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** indicar el nombre de mi institución educativa al generar un documento, **para** que aparezca en el encabezado oficial del archivo exportado sin tener que editarlo después a mano.

## Contexto

`docs/FLUJO_APLICATIVO(2).md` §2.1 describe este campo como parte de la "Sección de Configuración Base" ("Nombre del centro para el encabezado oficial"). **No existe hoy**: no está en `GenerationWizard.jsx`, ni en `schemas.py`, ni en `models.py`/`Document.content`.

## Criterios de aceptación

- El wizard (paso 1, junto a Área Curricular y Grado) incluye un campo de texto libre "Institución Educativa" — opcional, no bloquea el avance del wizard si se deja vacío.
- El valor se envía al backend junto con el resto de `params` y se guarda en `Document.content` (o un campo dedicado en `models.Document`) para poder reutilizarse en exportaciones futuras del mismo documento.
- `POST /export/pdf` y `POST /export/docx` incluyen el nombre de la institución en el encabezado si fue provisto; si no, se omite o se usa un placeholder genérico.

## Notas de implementación

- Es explícitamente texto libre en el documento funcional ("se recomienda usar el nombre legal", no se exige) — no agregar validación estricta de formato.
- Bajo esfuerzo: es un campo más en el formulario + un valor que viaja hasta el generador de PDF/DOCX, sin lógica de negocio adicional.

**Archivos relevantes:** `frontend/src/components/GenerationWizard.jsx`, `src/api/schemas.py`, `src/api/models.py`, `src/core/pdf_generator.py`, `src/api/routes/export.py`

**Fuente:** `docs/FLUJO_APLICATIVO(2).md` §2.1
