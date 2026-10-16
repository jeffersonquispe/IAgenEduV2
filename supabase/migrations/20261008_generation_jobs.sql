-- HU-33: jobs de generación en segundo plano.
-- Idempotente: se puede ejecutar más de una vez.

BEGIN;

CREATE TABLE IF NOT EXISTS generation_jobs (
    id                 varchar PRIMARY KEY,
    user_id            uuid REFERENCES profiles(id),
    tipo               varchar,                       -- 'unidad' | 'sesion'
    status             varchar DEFAULT 'pending',     -- pending | running | done | failed
    params             json,
    result_document_id varchar REFERENCES documents(id),
    error              text,
    created_at         timestamp DEFAULT (now() at time zone 'utc'),
    updated_at         timestamp DEFAULT (now() at time zone 'utc')
);

CREATE INDEX IF NOT EXISTS ix_generation_jobs_user_id ON generation_jobs (user_id);
CREATE INDEX IF NOT EXISTS ix_generation_jobs_status  ON generation_jobs (status);

COMMIT;

-- Verificación:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'generation_jobs' ORDER BY ordinal_position;
