-- HU-47: datos del encabezado de control documentario del perfil institucional
-- (red, version, aprobado_por, fecha_aprobacion, revisado_por, fecha_revision).
-- Idempotente: se puede ejecutar más de una vez.

BEGIN;

ALTER TABLE institution_profiles ADD COLUMN IF NOT EXISTS control_documentario json;

COMMIT;

-- Verificación:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'institution_profiles' AND column_name = 'control_documentario';
