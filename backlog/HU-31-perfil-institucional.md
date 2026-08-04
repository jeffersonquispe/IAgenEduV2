# HU-31: Perfil institucional del docente

**Épica:** Generación / Personalización institucional | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** registrar los datos de mi institución educativa (nombre, visión, misión, contexto relevante) una sola vez, **para** no tener que repetirlos cada vez que genero un documento.

## Contexto

Esta historia **reemplaza y amplía** a **HU-28** (que solo agregaba un campo de texto libre "Institución Educativa" para el encabezado del documento exportado). Aquí se modela como un perfil persistente por docente, reutilizable en todas sus generaciones, y sienta la base de datos que **HU-32** usa para inyectar ese contexto en el pipeline de IA.

Hoy no existe ninguna noción de "institución" en el modelo de datos (`src/api/models.py`) ni en el wizard de generación — cada generación parte solo de datos curriculares (área, grado, competencias, temas).

## Criterios de aceptación

- Nueva tabla `institution_profiles`, 1:1 con `User` (mismo patrón que `UserStats`):
  `id, user_id, nombre_institucion, nivel_modalidad, vision, mision, contexto_relevante, valores_institucionales (opcional)`.
- `contexto_relevante` es texto libre (zona urbana/rural, características de los estudiantes, enfoque institucional) — no se fuerza una estructura rígida.
- Nuevos endpoints `GET /institucion` y `PUT /institucion`, protegidos por `get_current_user`, mismo patrón que `GET /auth/stats`.
- Nueva pantalla de configuración en el frontend (una vez, no repetida por generación) — pestaña o sección nueva accesible desde `Sidebar.jsx`/`Dashboard.jsx`, no dentro del `GenerationWizard`.
- El perfil es opcional: un docente sin perfil configurado puede seguir generando documentos exactamente igual que hoy.
- Migración incremental en `migrate_db.py` para crear la tabla sin romper bases de datos existentes (mismo patrón `table_exists`/`column_exists` que ya usa el archivo).

## Notas de implementación

- No mezclar esto con `UserStats` — son conceptos distintos (estadísticas de uso vs. perfil institucional), aunque compartan la relación 1:1 con `User`.
- El campo `valores_institucionales` es opcional a propósito: si se deja vacío, el generador sigue usando los 13 valores MINEDU genéricos ya hardcodeados en `generator_agent.py` (`VALORES_PERMITIDOS`).

**Archivos relevantes:** `src/api/models.py`, `src/api/schemas.py`, nueva ruta (`src/api/routes/institution.py` o similar), `migrate_db.py`, `frontend/src/components/Sidebar.jsx`, nueva página/componente de configuración

**Depende de / relaciona con:** reemplaza **HU-28**; prerrequisito de **HU-32**
