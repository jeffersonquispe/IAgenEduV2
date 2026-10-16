# HU-46: Completar los "Datos Informativos" institucionales de la Unidad (DRE/UGEL, fechas, coordinación pedagógica, secciones)

**Épica:** Generación / Personalización institucional | **Prioridad:** Baja | **Esfuerzo:** S-M

**Como** docente, **quiero** que los datos informativos de la Unidad (DRE/UGEL, fecha de inicio y término, coordinación pedagógica, secciones y docentes involucrados) se completen a partir de mi perfil institucional en vez de quedar ausentes del documento, **para** no tener que agregarlos a mano en cada exportación.

## Contexto

`Unidad ejemplo.docx`, Tabla 1 ("DATOS INFORMATIVOS"), incluye: DRE/UGEL, Institución educativa, Área curricular, Grado y secciones (ej. *"3ro A y 3ro B"*), Fecha de inicio, Fecha de término, Coordinación pedagógica y Docente(s). Varios de estos campos —DRE/UGEL, fechas de inicio/término, coordinación pedagógica, secciones/docentes múltiples— no están contemplados ni en el wizard actual ni en el perfil institucional que define **HU-31** (`nombre_institucion, nivel_modalidad, vision, mision, contexto_relevante, valores_institucionales`).

## Criterios de aceptación

- `InstitutionProfile` (HU-31) se amplía con `dre_ugel` y `coordinacion_pedagogica` (ambos opcionales).
- El wizard permite indicar, por generación, secciones (texto libre, ej. *"3ro A y 3ro B"*), fecha de inicio y fecha de término, sin bloquear el avance si se dejan vacíos.
- La sección DATOS INFORMATIVOS de la Unidad exportada (PDF/DOCX) incluye estos campos cuando están disponibles; se omiten o usan placeholder si no lo están.

## Notas de implementación

- No implementar antes que HU-31 exista — depende directamente del modelo `InstitutionProfile`.
- No duplicar con HU-28 (ya reemplazada por HU-31/HU-32); esta historia cubre campos adicionales que ni siquiera HU-28 contemplaba.

**Archivos relevantes:** `src/api/models.py` (`InstitutionProfile`), `frontend/src/components/GenerationWizard.jsx`, `src/core/pdf_generator.py`

**Depende de:** HU-31
**Fuente:** `Unidad ejemplo.docx` (Tabla 1, "DATOS INFORMATIVOS")
