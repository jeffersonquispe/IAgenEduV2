# HU-50: Exportar el documento rellenando directamente el archivo de plantilla subido

**Épica:** Exportación / Plantillas institucionales | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** que el PDF/DOCX final salga con el diseño exacto del archivo de plantilla que subí (tablas, encabezado de control documentario, orden de columnas), **para** entregar un documento indistinguible del formato oficial de mi institución, sin tener que darle formato a mano después.

## Contexto

**Depende de HU-48** (esquema de plantilla) y se beneficia de que exista **HU-49** (contenido ya generado respetando esa estructura). Hoy `src/core/pdf_generator.py` y el exportador DOCX (`src/api/routes/export.py`) construyen el documento de exportación **desde cero**, con su propio maquetado — no reutilizan el `.docx` original que el docente pudiera haber subido. Esto es lo que hoy deja pendiente **HU-23** (estilos institucionales) y **HU-47** (encabezado de control documentario): sin esta historia, cualquier estilo institucional hay que reconstruirlo a mano en el generador.

## Criterios de aceptación

- Cuando existe una plantilla activa (HU-48) para el tipo de documento exportado, `POST /export/docx` abre el `.docx` original subido (no uno generado desde cero) y rellena cada celda de dato — localizada por el esquema de HU-48 — con el contenido correspondiente del documento generado, dejando intactas las celdas fijas (encabezado, control documentario, texto institucional).
- El resultado conserva el diseño, tablas, fuentes y logos del archivo original tal como lo subió el docente.
- `POST /export/pdf` sigue el mismo criterio cuando es técnicamente viable (renderizar el `.docx` ya rellenado a PDF), o documenta explícitamente la limitación si no lo es en esta iteración.
- Si no existe plantilla activa, el comportamiento es el actual (generador propio) — sin regresión.
- Si el esquema de la plantilla no cubre alguna sección que el documento generado sí tiene (o viceversa), se registra una advertencia visible al docente en vez de fallar silenciosamente o perder contenido.

## Notas de implementación

- `python-docx` permite editar el texto de celdas existentes preservando el resto del documento — es el mecanismo natural para esta historia (evitar reconstruir la tabla desde cero).
- Esta historia **resuelve HU-47 automáticamente** para instituciones con plantilla subida; HU-47 sigue siendo necesaria como fallback para instituciones sin plantilla propia.

**Archivos relevantes:** `src/core/pdf_generator.py`, `src/api/routes/export.py`, nuevo módulo de relleno de plantilla (comparte base con `src/core/template_parser.py` de HU-48)

**Depende de:** HU-48 | **Relaciona con:** HU-49, HU-23, HU-47
**Fuente:** solicitud de funcionalidad de plantillas personalizables; `Unidad didáctica(3).docx`, `Sesión de Aprendizaje(1).docx`
