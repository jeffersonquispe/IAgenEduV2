# HU-48: Subir y parsear la plantilla institucional (Unidad/Sesión) en un esquema reutilizable

**Épica:** Generación / Plantillas institucionales | **Prioridad:** Media | **Esfuerzo:** L

**Como** docente (o coordinador), **quiero** subir el archivo .docx de la "silueta" oficial de mi institución para Unidad Didáctica y para Sesión de Aprendizaje, **para** que el sistema aprenda esa estructura exacta en vez de usar la estructura genérica fija que trae hoy.

## Contexto

Hoy la estructura de ambos documentos está **hardcodeada** en `src/prompts/unidad_didactica.md` y `sesion_aprendizaje.md` (tablas, columnas y orden fijos en Markdown) y replicada en `StructureValidator.SECCIONES_UNIDAD`/`SECCIONES_SESION`. Esa estructura coincide, por ahora, con el formato de la Red Salesiana de Escuelas (ver `Unidad ejemplo.docx`, `Sesión de Aprendizaje ejm.docx`), pero es una coincidencia de origen, no una relación explícita: si el colegio cambia su formato — o si el sistema se usa en otra institución — hoy hay que editar el código.

`Unidad didáctica(3).docx` y `Sesión de Aprendizaje(1).docx` son la versión **en blanco (silueta)** de ese mismo formato: mismas tablas y columnas que los ejemplos llenos, pero con celdas vacías y texto instructivo en algunas (ej. Tabla 3 de la Unidad: *"Hay que recordar que los criterios se desprenden de los estándares de aprendizaje."*; Tabla 4: *"Pueden incluir los valores de la matriz axiológica."*). Son exactamente el tipo de archivo que un docente subiría como plantilla.

## Criterios de aceptación

- Nuevo endpoint (ej. `POST /institucion/plantilla`) que acepta un `.docx` y un tipo de documento (`unidad` | `sesion`), protegido por `get_current_user`.
- El backend usa `python-docx` (ya es dependencia, ver `requirements.txt`) para recorrer el documento y producir un **esquema estructurado** (JSON): lista de tablas en orden, columnas de cada tabla, encabezados/párrafos fijos fuera de tabla (ej. "UNIDAD DIDÁCTICA N°", "DATOS INFORMATIVOS").
- El parser distingue, de forma heurística, celdas de **instrucción/placeholder** (texto orientador para el docente, como los ejemplos citados arriba) de celdas de **dato a completar** (vacías o con `[...]`) — y las marca en el esquema en vez de tratarlas como contenido fijo.
- El esquema y el archivo original se guardan asociados a la institución del docente (mismo alcance que `InstitutionProfile`, **HU-31**), uno por tipo de documento.
- Si el docente sube una plantilla nueva, **reemplaza** la anterior para generaciones futuras; los documentos ya generados no se alteran retroactivamente.
- Si el `.docx` no contiene ninguna tabla reconocible, el endpoint rechaza el archivo con un mensaje claro en vez de guardar un esquema vacío.

## Notas de implementación

- Esfuerzo **L**: el parseo heurístico de instrucciones vs. datos es la parte más riesgosa — conviene que el endpoint devuelva el esquema extraído para que el docente lo confirme/edite antes de activarlo (evita que un parseo incorrecto rompa la generación en silencio).
- No mezclar el esquema de plantilla con `Document.content` (que es el contenido *generado*, no la definición de estructura).

**Archivos relevantes:** nueva ruta (`src/api/routes/institution.py` o similar), `src/api/models.py` (nueva tabla `document_templates`), nuevo módulo de parseo (ej. `src/core/template_parser.py`)

**Depende de / relaciona con:** HU-31 (perfil institucional)
**Fuente:** `Unidad didáctica(3).docx`, `Sesión de Aprendizaje(1).docx` (versión en blanco de la plantilla RSE)
