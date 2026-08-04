# HU-25: Suite de tests automatizados

**Épica:** Calidad técnica | **Prioridad:** Alta | **Esfuerzo:** L

**Como** desarrollador del proyecto, **quiero** contar con una suite de tests automatizados, **para** detectar regresiones al modificar el pipeline de agentes o las rutas de la API sin depender solo de pruebas manuales.

## Contexto

Hoy no existe ningún framework de testing configurado. `src/test_docx.py` es un script manual (`python src/test_docx.py`), no una suite `pytest`. Cambios en `structure_validator.py`, en los prompts, o en las rutas de `auth`/`generation` no tienen ninguna red de seguridad automatizada.

## Criterios de aceptación

- Se agrega `pytest` (+ `httpx`/`TestClient` de FastAPI) a las dependencias de desarrollo.
- Cobertura mínima inicial, por orden de retorno/esfuerzo:
  1. `structure_validator.py` — es lógica pura (regex/heurísticas), sin dependencias externas, y valida algo crítico (qué secciones se consideran obligatorias).
  2. Rutas de `auth.py` (`/register`, `/login`, `/me`) usando una base de datos SQLite en memoria o de prueba, no `edu_gen.db`.
  3. `gamification_logic.py` (cálculo de nivel, racha, badges) — también lógica pura, fácil de testear con datos sintéticos.
- Los tests que dependen de Bedrock (generación real vía LLM) se mockean — no se llama a AWS en la suite de CI/local.
- Comando único documentado para correr la suite (p. ej. `pytest` desde la raíz) y agregado a `CLAUDE.md`.

## Notas de implementación

- Empezar por `structure_validator.py` y `gamification_logic.py` da cobertura útil sin necesidad de mockear AWS ni configurar una base de datos de prueba — es el punto de partida de menor fricción.

**Archivos relevantes:** `src/validators/structure_validator.py`, `src/api/gamification_logic.py`, `src/api/routes/auth.py`, `src/test_docx.py` (reemplazar o integrar)
