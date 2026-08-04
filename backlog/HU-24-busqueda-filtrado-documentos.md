# HU-24: Búsqueda y filtrado de documentos

**Épica:** Historial | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** buscar y filtrar mis documentos generados por tipo, área curricular, grado o texto del título, **para** encontrar rápidamente uno específico cuando ya tengo muchos generados.

## Contexto

`GET /data/documents` (`src/api/routes/data.py`) devuelve siempre los últimos 10 documentos del usuario, sin parámetros de búsqueda ni paginación. A medida que un docente acumula documentos a lo largo de un año escolar, esa lista fija de 10 deja de ser suficiente.

## Criterios de aceptación

- `GET /data/documents` acepta parámetros opcionales de filtro: `type` (`unidad`/`sesion`), `area_curricular`, `grado`, y búsqueda de texto libre sobre `title`.
- Se agrega paginación (`limit`/`offset` o cursor) en vez del límite fijo de 10.
- El Dashboard (`Dashboard.jsx`) incorpora los controles de filtro/búsqueda correspondientes.

**Archivos relevantes:** `src/api/routes/data.py`, `frontend/src/pages/Dashboard.jsx`
