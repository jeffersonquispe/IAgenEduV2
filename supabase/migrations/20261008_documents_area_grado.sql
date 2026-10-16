-- HU-24 (fase 2): guardar área y grado en el propio documento para que el
-- filtro del Dashboard alcance también a los generados en modo "solo_generador"
-- (hoy esos datos solo existen en pipeline_runs).
-- Idempotente: se puede ejecutar más de una vez.

BEGIN;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS area_curricular varchar;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS grado varchar;

-- Relleno de los documentos existentes desde su pipeline_run (1:1).
UPDATE documents d
SET area_curricular = p.area_curricular,
    grado           = p.grado
FROM pipeline_runs p
WHERE p.document_id = d.id
  AND d.area_curricular IS NULL
  AND d.grado IS NULL;

COMMIT;

-- Verificación:
-- SELECT title, type, area_curricular, grado FROM documents ORDER BY created_at;
