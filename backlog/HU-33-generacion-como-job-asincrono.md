# HU-33: Generación de documentos como job asíncrono

**Épica:** Infraestructura / Escalabilidad | **Prioridad:** Media | **Esfuerzo:** L

**Como** docente, **quiero** que generar un documento no dependa de mantener la pestaña del navegador abierta durante 2+ minutos, **para** no perder el trabajo si se corta la conexión o cierro el navegador por error.

**Como** administrador del sistema, **quiero** que las generaciones no bloqueen un hilo del servidor durante minutos, **para** que la plataforma soporte varios docentes generando a la vez sin que unos hagan cola detrás de otros.

## Contexto

Verificado en vivo: una generación real de Unidad Didáctica (`POST /generate/unidad`) tardó **149 segundos** con la conexión HTTP abierta todo ese tiempo, usando `asyncio.to_thread` (`src/api/routes/generation.py`). El threadpool de FastAPI/Starlette tiene un número limitado de hilos; con varios docentes generando simultáneamente, las requests empiezan a hacer cola o a hacer timeout. Además, si el docente cierra la pestaña o pierde la conexión a mitad de la generación, el trabajo se pierde por completo — no hay forma de recuperarlo.

## Criterios de aceptación

- Nueva tabla `generation_jobs`: `id, user_id, tipo (unidad|sesion), status (pending|running|done|failed), params (json), result_document_id (nullable), error (nullable), created_at, updated_at`.
- `POST /generate/unidad` y `POST /generate/sesion` crean el job en estado `pending` y devuelven `202 Accepted` con `{job_id}` inmediatamente, en vez de bloquear la conexión hasta terminar.
- El trabajo real (llamar a `GenerationService`) se ejecuta en segundo plano (para el alcance de esta historia, `BackgroundTasks` de FastAPI es suficiente — no se exige introducir Celery/RQ/Redis salvo que el volumen real lo justifique más adelante).
- Nuevo endpoint `GET /generate/jobs/{id}` para consultar el estado y, cuando `status=done`, el documento resultante.
- El frontend (`GenerationWizard.jsx`) hace polling a `GET /generate/jobs/{id}` (o reutiliza el patrón SSE ya existente en el endpoint de streaming) en vez de esperar la respuesta de un único POST.
- Si el docente cierra la pestaña y vuelve más tarde, puede consultar el estado del job desde el Dashboard (lista de jobs recientes, no solo de documentos ya terminados).

## Notas de implementación — alcance en dos fases

- **Fase 1 (esta historia):** `BackgroundTasks` de FastAPI alcanza para el volumen de uso actual (proyecto de tesis, pocos usuarios concurrentes) y no agrega infraestructura nueva (sin Redis/broker).
- **Fase 2 (fuera de alcance, solo si el uso real lo justifica):** migrar a una cola real (Celery/RQ + Redis) si se necesita reintentos robustos, prioridad de jobs, o escalar el trabajo en background a múltiples procesos/máquinas independientes del proceso web.
- Esta historia **no requiere** HU-27 (PostgreSQL) para funcionar con un solo proceso `uvicorn`, pero si se agregan más workers para escalar horizontalmente, sí hace falta — SQLite no soporta bien escrituras concurrentes entre procesos.

**Archivos relevantes:** `src/api/routes/generation.py`, `src/api/services/generation_service.py`, `src/api/models.py`, `migrate_db.py`, `frontend/src/components/GenerationWizard.jsx`, `frontend/src/pages/Dashboard.jsx`

**Relaciona con:** **HU-27** (necesaria para escalar a múltiples workers), **HU-34**
