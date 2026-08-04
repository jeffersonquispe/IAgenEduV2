# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

IA-GEN-EDU generates curriculum planning documents (**Unidad Didáctica** and **Sesión de Aprendizaje**) for Peruvian secondary-school teachers, aligned to the CNEB/MINEDU national curriculum, using Amazon Bedrock (Claude). This is a thesis project (`docs/RESUMEN_PROYECTO.md`, `docs/DETALLES_TECNICOS.md` document it in depth in Spanish).

Repo layout: root has the app entry points (`run.py`, `frontend/`, `src/`) plus project-management docs (`README.md`, `CLAUDE.md`, `USER_STORIES.md`, `backlog/`). Reference documentation lives in `docs/`, one-off AWS/Bedrock Knowledge Base setup scripts in `scripts/aws/`, and the exploratory baseline notebook in `notebooks/`.

**There are two separate applications in this repo — know which one you're working on:**

1. **Active app (v2.0): FastAPI + React**, in `src/api/` and `frontend/`. This is where new work happens: JWT auth, a multi-agent generation pipeline, per-section editing/refinement, document history, gamification.
2. **Legacy app (v1.0): Streamlit**, in `src/app/app.py`. Single-file UI with tabs for Unidad/Sesión and a chat-style refinement box. Only `requirements.txt` and the Dockerfile target this app — the FastAPI/React stack's dependencies (fastapi, sqlalchemy, uvicorn, pydantic, python-jose, passlib, python-docx, fpdf2, weasyprint) are installed in the venv but **not** listed in `requirements.txt`.

Both apps ultimately call into the same `src/core/` and `src/agents/` generation logic, but through different entry points (`bedrock_services.py` for the API, direct calls for Streamlit's `legacy_generator.py` path).

## Commands

### Active app (FastAPI backend + React frontend)

```bash
# Backend — from repo root, venv already has the needed packages
python run.py                    # Uvicorn on :8000, reload=True, docs at /docs

# Frontend — separate terminal
cd frontend
npm install
npm run dev                      # Vite on :5173, proxies /api/* -> http://localhost:8000
```

Run `python migrate_db.py` once after pulling schema changes and before starting the server — `Base.metadata.create_all()` in `main.py` only creates missing tables, it does not add columns to existing ones (e.g. `documents.current_version`, or new tables like `document_versions`/`pipeline_runs`) or alter them. Add new incremental migrations to `migrate_db.py` following the existing `column_exists`/`table_exists` pattern rather than relying on `models.py` alone.

### Legacy Streamlit app

```bash
streamlit run src/app/app.py     # or ./run_streamlit.sh — :8501
```

### Docker

`docker-compose up --build` only builds and runs the **legacy Streamlit app** (port 8501, from `Dockerfile`/`docker-compose.yml`). There is no containerization for the FastAPI/React stack.

### Tests

There is no test runner/framework configured. `src/test_docx.py` is a standalone manual script (`python src/test_docx.py`), not part of a pytest suite.

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
- **CNEB catalog data** (áreas, grados, competencias) lives in `src/core/competencias_curriculares.py` and `data/*.json`, served via `GET /data/options`.

### RAG

`src/core/rag_service.py` queries an Amazon Bedrock Knowledge Base and prepends the result to the generation prompt as `"CONTEXTO OFICIAL DEL MINEDU:\n{rag}\n\n{prompt}"`. Failures are swallowed — generation proceeds without curricular context rather than blocking. LLM calls go through `BedrockClient` (`src/core/bedrock_client.py`), which also has an Azure OpenAI fallback path.

### Data model

SQLite (`edu_gen.db`), models in `src/api/models.py`: `User` 1:1 `UserStats`, `User` 1:N `Document`, `Document` 1:N `DocumentVersion` (edit history) and 1:1 `PipelineRun` (per-generation metrics: validation score, error counts, corrections applied, duration — populated from `AgentCoordinator`'s `PipelineMetrics`). `Document.content` is a JSON blob whose shape differs by `type` (`unidad` has `situacion_significativa`/`propositos_de_aprendizaje`/`secuencia_de_sesiones`/`rubrica_unidad`; `sesion` has `secuencia_didactica`/`reflexion_sobre_la_actividad`/`rubrica_sesion` — see `docs/DETALLES_TECNICOS.md` §4.2 for full field lists).

Auth is JWT (HS256, `python-jose`) with `passlib`/bcrypt password hashing; `get_current_user` (in `routes/auth.py`) is the shared dependency guarding generation/export/data routes. `gamification_logic.py` recomputes points/level/streak/badges on every login and on `/auth/stats`.

### Frontend

React Router with three routes gated by a token in `localStorage` (`App.jsx`): `/login`, `/` (Dashboard), `/editor`. A global axios response interceptor logs the user out on any 401. Vite's dev-server proxy (`vite.config.js`) is what makes relative `/api/*` calls from `axios` reach the FastAPI backend — if you add a new API call, no absolute URL/base is needed in dev.
