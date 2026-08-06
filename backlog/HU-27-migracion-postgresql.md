# HU-27: Migración de SQLite a PostgreSQL

> ✅ **Implementado** — como parte de una migración más amplia a Supabase (base de datos + autenticación) motivada originalmente por HU-19 (que el email de reseteo llegara de verdad). `database.py` ahora lee `DATABASE_URL` de entorno (connection string del "Session pooler" de Supabase, driver `psycopg[binary]` v3), sin fallback a SQLite. `migrate_db.py` fue eliminado — el esquema se aplica directamente contra Postgres (`Base.metadata.create_all()` para tablas nuevas, SQL manual vía `supabase db query` para cambios de columna existentes). Alembic quedó identificado como mejora futura si el esquema empieza a cambiar seguido, pero no se configuró en este alcance. Ver también HU-19 y HU-21 (superadas por la misma migración).

**Épica:** Infraestructura | **Prioridad:** Baja | **Esfuerzo:** L

**Como** administrador del sistema, **quiero** que la base de datos soporte múltiples usuarios concurrentes de forma confiable, **para** poder desplegar la plataforma más allá de un entorno de tesis/demo de un solo usuario a la vez.

## Contexto

Limitación ya documentada en `docs/DETALLES_TECNICOS.md` §15. `src/api/database.py` usa SQLite (`sqlite:///./edu_gen.db`) con `check_same_thread=False`, lo cual permite que la app corra pero no da garantías reales de concurrencia con múltiples usuarios escribiendo a la vez (generación, refinamiento, exportación son todas escrituras).

## Criterios de aceptación

- `SQLALCHEMY_DATABASE_URL` se vuelve configurable por variable de entorno (`DATABASE_URL`, ya mencionada en `README.md` §Instalación pero no implementada en `database.py`) en vez de estar hardcodeada.
- Existe un camino de migración de esquema (Alembic, o extender `migrate_db.py`) que funcione tanto para SQLite como PostgreSQL.
- Los tipos específicos de SQLite si los hubiera (ninguno crítico detectado hoy — `JSON`, `String`, `DateTime` son portables en SQLAlchemy) se revisan para compatibilidad con PostgreSQL.
- Documentar en `CLAUDE.md`/`README.md` cómo apuntar el proyecto a una instancia PostgreSQL local o gestionada.

## Notas de implementación

- Es la historia de mayor esfuerzo y menor urgencia de esta lista: solo se vuelve necesaria si el proyecto pasa de ser una demo/tesis de un solo usuario a un despliegue con varios docentes concurrentes. No priorizar sobre las demás salvo que ese escenario ya esté planeado.

**Archivos relevantes:** `src/api/database.py`, `migrate_db.py`
