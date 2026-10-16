# HU-47: Exportación fiel a la plantilla oficial (encabezado y control documentario)

**Épica:** Exportación | **Prioridad:** Baja | **Esfuerzo:** S

**Como** docente, **quiero** que el PDF/DOCX exportado incluya el encabezado de control documentario oficial (nombre del formato, versión, aprobado por, revisado por, fecha, número de páginas), **para** entregar un documento que mi institución reconozca como válido sin maquetarlo yo mismo.

## Contexto

**HU-23** (exportación DOCX con estilos institucionales) ya está en el backlog, pero sin una especificación concreta de qué estilo aplicar. `Unidad ejemplo.docx` y `Sesión de Aprendizaje ejm.docx` ahora dan esa especificación: ambos incluyen una tabla de encabezado con *"Documento: Formato de Unidad/Sesión Didáctica | Red [institución] | Versión: 02 | Aprobado por: [rol] | Fecha: [fecha] | Revisado por: [equipo] | Fecha: [fecha] | Páginas: N"*. Ningún generador actual (`pdf_generator.py`, `export.py`) reproduce esta tabla de control documentario.

## Criterios de aceptación

- `pdf_generator.py` (y el generador DOCX que resulte de HU-23) agregan una tabla de encabezado/pie configurable con: nombre del formato, nombre de la institución/red, número de versión, aprobado por, revisado por, fecha de revisión, número de páginas.
- Estos valores son configurables (no hardcodeados a "Red Salesiana de Escuelas RSE"), idealmente desde `InstitutionProfile` (HU-31) o una configuración de exportación aparte.
- Si no hay configuración institucional, el encabezado se omite (sin regresión respecto al comportamiento actual).

**Archivos relevantes:** `src/core/pdf_generator.py`, `src/api/routes/export.py`

**Depende de / relaciona con:** HU-23, HU-31
**Fuente:** `Unidad ejemplo.docx` y `Sesión de Aprendizaje ejm.docx` (Tabla 0, control documentario)
