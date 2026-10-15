# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

IA-GEN-EDU generates curriculum planning documents (**Unidad Didáctica** and **Sesión de Aprendizaje**) for Peruvian secondary-school teachers, aligned to the CNEB/MINEDU national curriculum, using Amazon Bedrock (Claude). This is a thesis project (`docs/RESUMEN_PROYECTO.md`, `docs/DETALLES_TECNICOS.md` document it in depth in Spanish).

Repo layout: root has the app entry points (`run.py`, `frontend/`, `src/`) plus project-management docs (`README.md`, `CLAUDE.md`, `USER_STORIES.md`, `backlog/`). Reference documentation lives in `docs/`, one-off AWS/Bedrock Knowledge Base setup scripts in `scripts/aws/`, and the exploratory baseline notebook in `notebooks/`.

**There are two separate applications in this repo — know which one you're working on:**

1. **Active app (v2.0): FastAPI + React**, in `src/api/` and `frontend/`. This is where new work happens: Supabase Auth, a multi-agent generation pipeline, per-section editing/refinement, document history, gamification.
2. **Legacy app (v1.0): Streamlit**, in `src/app/app.py`. Single-file UI with tabs for Unidad/Sesión and a chat-style refinement box. Has no database/auth of its own — unaffected by the Supabase migration.

`requirements.txt` covers both apps' direct dependencies (Streamlit legacy + FastAPI/React active stack).

Both apps ultimately call into the same `src/core/` and `src/agents/` generation logic, but through different entry points (`bedrock_services.py` for the API, direct calls for Streamlit's `legacy_generator.py` path).

## Commands

### Active app (FastAPI backend + React frontend)

```bash
# Backend — from repo root, venv already has the needed packages
python run.py                    # Uvicorn on :5000, reload=True, docs at /docs

# Frontend — separate terminal
cd frontend
npm install
npm run dev                      # Vite on :5001, proxies /api/* -> http://localhost:5000
```

`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` are required env vars (see `.env.example`) — `database.py` and `routes/auth.py` raise `RuntimeError` at import time if any is unset, rather than falling back to a default (same fail-fast pattern HU-21 established for the now-removed `SECRET_KEY`). `DATABASE_URL` must be the Supabase project's **Session pooler** connection string (not Direct, not Transaction pooler — this backend is a persistent process with its own SQLAlchemy connection pool), prefixed `postgresql+psycopg://`.

There is no `migrate_db.py` anymore — schema changes are applied directly against the Supabase Postgres project (e.g. via `Base.metadata.create_all(bind=engine)` for new tables, or a one-off `supabase db query` / `ALTER TABLE` for column changes on existing ones). Consider adopting Alembic if the schema starts changing frequently; not set up yet.

### Legacy Streamlit app

```bash
streamlit run src/app/app.py     # or ./run_streamlit.sh — :8501
```

### Docker

`docker-compose up --build` only builds and runs the **legacy Streamlit app** (port 8501, from `Dockerfile`/`docker-compose.yml`). There is no containerization for the FastAPI/React stack.

### Tests

`pytest src/tests -v` runs the automated suite (`src/tests/`) — unit tests for the streaming generation service against mocked SSE events, plus integration tests that hit a running server on `:5000` when available (skipped otherwise). `src/test_docx.py` is a separate standalone manual script (`python src/test_docx.py`), not part of the pytest suite.

### Windows-specific gotcha

`src/api/main.py` sets `platform._wmi = None` before any other import. On machines where the WMI service is broken/hanging, `sqlalchemy`'s import-time call to `platform.win32_ver()` blocks forever waiting on a WMI query; this line forces the (already-present) fallback to `sys.getwindowsversion()`. Don't remove it without confirming WMI works on the target machine — without it, `python run.py` can hang indefinitely with no error output before Uvicorn even starts.

## Architecture

### Request flow (active app)

```
React Wizard (GenerationWizard.jsx)
  -> POST /generate/unidad | /generate/sesion   (src/api/routes/generation.py)
  -> bedrock_services.generar_*()               (src/core/bedrock_services.py — thin bridge)
  -> AgentCoordinator.generar_*()                (src/agents/coordinator.py)
       1. GeneratorAgent.generar()                — RAGService context + PromptManager template -> BedrockClient
       2. ValidatorAgent.validar_*()               — StructureValidator (regex/heuristics) + ContentValidator (LLM-as-judge)
       3. if errores_criticos: GeneratorAgent.corregir()  (max 1 retry, see AgentCoordinator.max_correcciones)
       4. FormatterAgent.formatear()               — normalizes Markdown tables, strips stray HTML
  -> parsers split the raw text into sections -> saved as Document.content (JSON) -> returned to Editor.jsx
```

If `_USE_AGENT_PIPELINE` (in `bedrock_services.py`) raises or returns a too-short result, it falls back to `legacy_generator.py` (direct prompt, no agent pipeline). `AgentCoordinator` is a module-level singleton via `get_coordinator()`.

Refinement (`/generate/refine` and the Editor's per-section AI edit) bypasses the full pipeline: it calls `AgentCoordinator.mejorar_documento()` directly, or `bedrock_client.invocar()` as a last-resort fallback — no validation/formatting pass.

### Where business rules live

- **Pedagogical structure rules are in the prompt templates**, not in Python: `src/prompts/*.md` are Markdown files with `{variable}` placeholders rendered by `PromptManager`. E.g. `producto_final` governs the Unidad's rubric; `metodologia` (ERCA / ABP / Aula Invertida) changes the Sesión's Inicio/Desarrollo structure via `_construir_contexto_metodologia()` in `generator_agent.py`.
- **Required sections per document type** are enforced by `StructureValidator` (`src/validators/structure_validator.py`), separately from what the prompt asks for — if you add a section to a prompt template, add it to the validator too, or `ValidationReport.tiene_errores_criticos` will start firing.
- **CNEB catalog data** (áreas, grados, competencias) lives in `src/core/competencias_curriculares.py` and `data/*.json`, served via `GET /data/options` and `GET /data/competencias?area=` (area's own competencias + the 2 transversales).

### RAG

**Structured retrieval comes first.** `RAGEducativoService.buscar_contexto_curricular()` first calls `RecuperadorCurricular` (`src/core/retrieval_estructurado.py`) over `data/programa_curricular_secundaria_2016.json` (the full Programa Curricular, transcribed from the scanned PDF by `scripts/ingesta/`): desempeños are filtered by area + grade (+ the competencia the teacher picked in the wizard, passed by `GeneratorAgent` as `competencia`), followed by that competencia's capacidades and the cycle's estándar. Only then does it append the complementary context (Bedrock KB, or BM25 over the local pedagogy JSONs; `RAG_COMPLEMENTARIO_BM25=0` restores the old keyword scorer). Without the filter ~80% of retrieved desempeños were from the wrong grade. `RAG_ESTRUCTURADO=0` disables it; if it fails the service behaves as before. Evaluation harness: `python -m src.eval.run_retrieval_eval` (metrics in `docs/METRICAS_EFECTIVIDAD.md` §5). The wizard's competencia catalog (`competencias_curriculares.py`, each entry with an `area`) is checked against the same corpus by `test_catalogo_competencias.py`; the 2 transversal competencias are offered in every area, and `numero` ids are never renumbered or reused (they are the wizard's selector value and the `COMPETENCIA N.` prefix sent to the generator).

`src/core/rag_service.py` queries an Amazon Bedrock Knowledge Base and prepends the result to the generation prompt as `"CONTEXTO OFICIAL DEL MINEDU:\n{rag}\n\n{prompt}"`. Failures are swallowed — generation proceeds without curricular context rather than blocking. LLM calls go through `BedrockClient` (`src/core/bedrock_client.py`), which also has an Azure OpenAI fallback path.

### Data model

Supabase Postgres, models in `src/api/models.py`: `User` (`__tablename__ = "profiles"`, **not** `"users"` — deliberately distinct from Supabase's internal `auth.users` table; `id` is the same UUID as `auth.users.id`, `FOREIGN KEY REFERENCES auth.users(id)`) 1:1 `UserStats`, `User` 1:N `Document`, `Document` 1:N `DocumentVersion` (edit history) and 1:1 `PipelineRun` (per-generation metrics — populated from `AgentCoordinator`'s `PipelineMetrics`). User-referencing FK columns (`profiles.id`, `user_stats.user_id`, `documents.user_id`) use `sqlalchemy.dialects.postgresql.UUID(as_uuid=False)` (aliased `UserUUID` in `models.py`) so values stay plain Python `str` — matching what `supabase-py`'s `auth.get_user()` already returns — while still binding correctly against the native Postgres `uuid` column type (a plain `String` column produces a `::VARCHAR` cast that Postgres refuses to compare against `uuid`). `Document.id`/`Document.parent_document_id` are unrelated app-generated UUIDs (`uuid.uuid4()`), stored as plain `String` — not to be confused with the auth UUID type. `Document.content` is a JSON blob whose shape differs by `type` (`unidad` has `situacion_significativa`/`propositos_de_aprendizaje`/`secuencia_de_sesiones`/`rubrica_unidad`; `sesion` has `secuencia_didactica`/`reflexion_sobre_la_actividad`/`rubrica_sesion` — see `docs/DETALLES_TECNICOS.md` §4.2 for full field lists).

**Auth is Supabase Auth**, not a custom JWT/bcrypt system — login/register/password-reset all happen client-side via `supabase-js` (`frontend/src/lib/supabaseClient.js`), never through this backend. `get_current_user` (in `routes/auth.py`) verifies the bearer token by calling `supabase.auth.get_user(token)` server-side via `supabase-py` (not local JWT decoding — Supabase's newer projects default to asymmetric signing keys, so there's no guaranteed shared secret to verify against locally). The first authenticated request for a given Supabase user auto-creates its `profiles`/`user_stats` rows if missing (`_bootstrap_profile` in `routes/auth.py`) — there's no separate "complete registration" endpoint or Postgres trigger; this makes the profile creation self-healing regardless of how/where the Supabase account was created. `gamification_logic.py` recomputes points/level/streak/badges on every `/auth/stats` call (this is also where "record today's use" now happens, since there's no backend `/auth/login` handler anymore to hang that logic off of).

### Frontend

React Router with three routes gated by a Supabase session (`App.jsx`, via `supabase.auth.getSession()` + `onAuthStateChange`): `/login`, `/` (Dashboard), `/editor`, plus an unauthenticated `/reset-password`. `frontend/src/lib/api.js` exports a shared axios instance (`api`) whose request interceptor attaches `Authorization: Bearer <supabase session token>` automatically — use this instead of raw `axios` for any new authenticated call. Its response interceptor calls `supabase.auth.signOut()` on any 401. The one exception is `GenerationWizard.jsx`'s SSE streaming call, which uses native `fetch()` (axios doesn't expose a readable stream the same way) and fetches the current token via `supabase.auth.getSession()` directly before the request. Vite's dev-server proxy (`vite.config.js`) still makes relative `/api/*` calls reach the FastAPI backend — `supabase-js` calls go straight to the Supabase project's absolute URL and bypass this proxy entirely (Supabase's own CORS handles that).
