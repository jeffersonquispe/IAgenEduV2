# 📋 Documentación Técnica — IA-GEN-EDU

**Versión:** 2.0 | **Stack:** FastAPI + React + Amazon Bedrock | **Fecha:** Marzo 2026

---

## 1. Resumen Ejecutivo

IA-GEN-EDU es una plataforma web que automatiza la generación de planificación curricular para docentes peruanos de educación secundaria, alineada al Currículo Nacional de Educación Básica (CNEB/MINEDU). El sistema combina un pipeline de **agentes de IA especializados** con un backend REST en FastAPI y un frontend en React, produciendo documentos `.docx` y `.pdf` listos para uso administrativo.

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de componentes

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND  (React + Vite + TailwindCSS)            │
│                                                                       │
│  Login.jsx → Dashboard.jsx → GenerationWizard.jsx → Editor.jsx       │
│                                                                       │
│  Puerto: 5173  |  Proxy /api/* → http://localhost:8000                │
└──────────────────────────────────┬──────────────────────────────────-┘
                                   │ HTTP/REST (JSON)
┌──────────────────────────────────▼───────────────────────────────────┐
│                     BACKEND (FastAPI + Uvicorn)                        │
│                          Puerto: 8000                                  │
│                                                                       │
│  /auth/*  /generate/*  /export/*  /data/*                            │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    AgentCoordinator                              │  │
│  │                                                                 │  │
│  │  1. GeneratorAgent ←── PromptManager (plantillas .md)          │  │
│  │       └── RAGEducativoService (Bedrock Knowledge Bases)         │  │
│  │  2. ValidatorAgent                                              │  │
│  │       ├── StructureValidator  (regex + heurísticas)             │  │
│  │       └── ContentValidator    (LLM como juez)                   │  │
│  │  3. FormatterAgent            (limpieza de tablas Markdown)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                         │                                              │
│     LLM: Amazon Bedrock (Claude 3 Sonnet)                             │
│     Fallback: Azure OpenAI → AWS Bedrock directo                      │
│                                                                       │
│  SQLite (edu_gen.db)                                                  │
│   users · user_stats · documents                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Flujo de generación end-to-end

```
Docente llena Wizard
       │
       ▼
POST /api/generate/unidad  (o /sesion)
       │
       ▼
bedrock_services.generar_unidad_didactica(
    area, grado, competencias, temas,
    num_sesiones, producto_final          ← nuevo
)
       │
       ├─ _USE_AGENT_PIPELINE = True?
       │     │
       │     ▼
       │  AgentCoordinator.generar_unidad_didactica()
       │     │
       │     ├─ GeneratorAgent.generar()
       │     │     ├─ RAGService.buscar_contexto_curricular()
       │     │     └─ BedrockClient.invocar(prompt)
       │     │
       │     ├─ ValidatorAgent.validar_unidad()
       │     │     ├─ StructureValidator (rápido, programático)
       │     │     └─ ContentValidator (LLM, si no hay errores críticos)
       │     │
       │     ├─ (Si errores críticos) GeneratorAgent.corregir()
       │     │
       │     └─ FormatterAgent.formatear()
       │
       └─ Fallback: prompt directo a Bedrock
       │
       ▼
Parsers extraen secciones del texto crudo
(situacion_significativa, propositos, secuencia_sesiones, rubrica_unidad)
       │
       ▼
DB: Document guardado con content JSON
       │
       ▼
Response JSON → Editor.jsx muestra secciones editables
       │
       ▼
Docente aprueba → POST /api/export/docx  o  /api/export/pdf
```

---

## 3. Estructura de Directorios

```
ia-gen-edu/
│
├── run.py                      # Entry point: levanta Uvicorn/FastAPI en :8000
│
├── src/
│   ├── api/
│   │   ├── main.py             # FastAPI app, CORS, registro de routers
│   │   ├── database.py         # SQLAlchemy engine (SQLite: edu_gen.db)
│   │   ├── models.py           # ORM: User, UserStats, Document
│   │   ├── schemas.py          # Pydantic schemas de entrada/salida
│   │   ├── auth_utils.py       # Hash de contraseñas, JWT
│   │   ├── gamification_logic.py  # Cálculo de puntos, badges, racha
│   │   └── routes/
│   │       ├── auth.py         # POST /auth/login, /auth/register, GET /auth/me
│   │       ├── generation.py   # POST /generate/unidad, /generate/sesion, /generate/refine
│   │       ├── export.py       # POST /export/pdf, /export/docx
│   │       └── data.py         # GET /data/options, /data/documents
│   │
│   ├── agents/
│   │   ├── coordinator.py      # Orquesta pipeline: Generator→Validator→Formatter
│   │   ├── generator_agent.py  # Genera contenido con RAG + prompts
│   │   ├── validator_agent.py  # Valida estructura y calidad
│   │   └── formatter_agent.py  # Limpia y normaliza tablas Markdown
│   │
│   ├── core/
│   │   ├── bedrock_client.py   # Wrapper de Amazon Bedrock con fallback
│   │   ├── bedrock_services.py # Funciones públicas de generación (bridge viejo→nuevo)
│   │   ├── prompt_manager.py   # Carga y renderiza plantillas .md con {variables}
│   │   ├── rag_service.py      # Consulta Bedrock Knowledge Bases
│   │   ├── pdf_generator.py    # Genera PDF con WeasyPrint
│   │   └── competencias_curriculares.py  # Catálogo CNEB (áreas, grados, competencias)
│   │
│   ├── prompts/
│   │   ├── unidad_didactica.md     # Prompt de generación de unidad
│   │   ├── sesion_aprendizaje.md   # Prompt de generación de sesión
│   │   ├── mejora_documento.md     # Prompt de refinamiento por campo
│   │   └── validacion.md           # Prompt para ContentValidator (LLM-as-judge)
│   │
│   ├── validators/
│   │   ├── structure_validator.py  # Valida secciones, formato, HTML residual
│   │   ├── content_validator.py    # Validación semántica con LLM
│   │   └── format_cleaner.py       # Limpieza de caracteres extraños
│   │
│   └── utils/
│       └── ...
│
├── frontend/
│   ├── vite.config.js          # Proxy: /api/* → http://localhost:8000
│   └── src/
│       ├── App.jsx             # Router (Login / Dashboard / Editor)
│       ├── pages/
│       │   ├── Login.jsx       # Formulario auth + registro
│       │   ├── Dashboard.jsx   # Lista de documentos + botones de nuevo doc
│       │   └── Editor.jsx      # Visualización editable + refinamiento IA + export
│       └── components/
│           ├── GenerationWizard.jsx  # Modal 3 pasos para crear doc
│           └── Sidebar.jsx           # Navegación + stats del usuario
│
└── data/
    ├── curriculo_nacional_secundaria.json
    └── orientaciones_pedagogicas_cneb.json
```

---

## 4. Base de Datos

### 4.1 Esquema (SQLite — `edu_gen.db`)

```
┌────────────────────────────────┐
│           users                │
├────────────────────────────────┤
│ id          INTEGER PK         │
│ email       STRING UNIQUE      │
│ hashed_password STRING         │
│ full_name   STRING             │
│ is_active   BOOLEAN            │
│ created_at  DATETIME           │
└────────────┬───────────────────┘
             │ 1:1
┌────────────▼───────────────────┐
│         user_stats             │
├────────────────────────────────┤
│ id          INTEGER PK         │
│ user_id     FK → users         │
│ docs_generados   INTEGER       │
│ unidades_generadas INTEGER     │
│ sesiones_generadas INTEGER     │
│ mejoras_realizadas INTEGER     │
│ exportaciones_docx INTEGER     │
│ exportaciones_pdf  INTEGER     │
│ nivel        INTEGER           │
│ puntos       INTEGER           │
│ racha_manual INTEGER           │
│ badges_desbloqueados JSON[]    │
│ areas_usadas JSON[]            │
│ grados_usados    JSON[]        │
│ dias_uso     JSON[]  (YYYY-MM-DD) │
│ ultima_conexion  DATETIME      │
│ primera_visita   BOOLEAN       │
└────────────────────────────────┘

┌────────────────────────────────┐
│          documents             │
├────────────────────────────────┤
│ id         STRING PK (UUID)    │
│ user_id    FK → users          │
│ type       STRING  (unidad|sesion) │
│ title      STRING              │
│ content    JSON                │
│ created_at DATETIME            │
└────────────────────────────────┘
```

### 4.2 Estructura del campo `content` (JSON)

**Unidad Didáctica:**
```json
{
  "titulo": "Unidad Didáctica - Comunicación",
  "situacion_significativa": "...",
  "propositos_de_aprendizaje": "...",
  "valores_y_enfoques_transversales": "...",
  "secuencia_de_sesiones": "...",
  "rubrica_unidad": "..."
}
```

**Sesión de Aprendizaje:**
```json
{
  "titulo": "Sesión - El ecosistema",
  "datos_informativos": "...",
  "propositos_de_aprendizaje": "...",
  "secuencia_didactica": "...",
  "reflexion_sobre_la_actividad": "...",
  "rubrica_sesion": "..."
}
```

---

## 5. API REST — Endpoints

### Autenticación

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/auth/register` | Registrar usuario nuevo | No |
| `POST` | `/auth/login` | Login, retorna JWT | No |
| `GET` | `/auth/me` | Datos del usuario actual | Bearer |
| `GET` | `/auth/stats` | Stats + badges + nivel | Bearer |

### Generación

| Método | Ruta | Descripción | Body clave |
|---|---|---|---|
| `POST` | `/generate/unidad` | Genera Unidad Didáctica completa | `area`, `grado`, `competencias[]`, `temas`, `num_sesiones`, **`producto_final`** |
| `POST` | `/generate/sesion` | Genera Sesión de Aprendizaje | `area`, `grado`, `titulo_unidad`, `tema`, **`metodologia`** |
| `POST` | `/generate/refine` | Refina un campo con IA | `content`, `instruction` |

### Exportación

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/export/pdf` | Genera PDF del documento |
| `POST` | `/export/docx` | Genera DOCX del documento |

### Datos Curriculares

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/data/options` | Áreas, grados, competencias, temas del CNEB |
| `GET` | `/data/documents` | Últimos 10 documentos del usuario |

---

## 6. Pipeline de Agentes IA

### 6.1 Descripción de cada agente

| Agente | Archivo | Responsabilidad |
|---|---|---|
| **GeneratorAgent** | `agents/generator_agent.py` | Genera el contenido educativo usando el prompt cargado desde `prompts/*.md`, enriquecido con RAG. Tiene método `corregir()` para auto-corrección. |
| **ValidatorAgent** | `agents/validator_agent.py` | Orquesta dos tipos de validación: estructural (programática, rápida) y semántica (LLM como juez, opcional). Retorna `ValidationReport`. |
| **FormatterAgent** | `agents/formatter_agent.py` | Limpia el texto Markdown: normaliza tablas, elimina HTML residual, corrige viñetas. |
| **AgentCoordinator** | `agents/coordinator.py` | Orquesta el pipeline. Si el validador detecta errores críticos, solicita al generador 1 ciclo de corrección antes de formatear. |

### 6.2 ValidationReport

```python
@dataclass
class ValidationReport:
    errores: List[ValidationError]  # tipo: CRITICO | ADVERTENCIA | INFO
                                    # categoria: ESTRUCTURA | FORMATO | CONTENIDO
    puntaje: int          # 0-100 (CRITICO: -25, ADVERTENCIA: -10)
    tiene_errores_criticos: bool
    es_valido: bool
```

### 6.3 Secciones requeridas por documento

| Documento | Secciones obligatorias |
|---|---|
| Unidad Didáctica | TÍTULO, SITUACIÓN SIGNIFICATIVA, PROPÓSITOS, EVIDENCIAS, INSTRUMENTOS, VALORES, SECUENCIA |
| Sesión | DATOS INFORMATIVOS, SITUACIÓN SIGNIFICATIVA, PROPÓSITOS, SECUENCIA DIDÁCTICA, MATERIALES |

---

## 7. Prompts y Plantillas

Los prompts viven en `src/prompts/*.md` como plantillas con variables `{nombre_variable}`.

### 7.1 Variables de `unidad_didactica.md`

| Variable | Fuente | Propósito |
|---|---|---|
| `{area_curricular}` | Wizard | Filtro maestro del contenido |
| `{grado}` | Wizard | Nivel de desempeños CNEB |
| `{contexto_competencia}` | `_construir_contexto_competencia()` | Competencias obligatorias |
| `{contexto_temas}` | Wizard | Temas a incluir (índice) |
| `{contexto_sesiones}` | Wizard | Nº de sesiones exacto |
| `{contexto_producto}` | **Nuevo** — Wizard | Gobierna la rúbrica analítica |
| `{num_sesiones}` | Wizard | Repetido para regla de cardinalidad |
| `{valores_texto}` | Hardcoded | 13 valores institucionales permitidos |
| `{enfoques_texto}` | Hardcoded | 8 enfoques transversales MINEDU |

### 7.2 Variables de `sesion_aprendizaje.md`

| Variable | Fuente | Propósito |
|---|---|---|
| `{titulo_unidad}` | Wizard | Vincula con la unidad padre |
| `{titulo_sesion}` | Wizard | Título de la sesión |
| `{nivel}` / `{grado}` / `{seccion}` | Wizard | Datos informativos |
| `{duracion}` | Wizard / default 90 min | Distribuye tiempos por momento |
| `{texto_competencias}` | Unidad padre | Competencias a reutilizar |
| `{contexto_tema}` | Wizard | Tema específico de la sesión |
| `{contexto_metodologia}` | **`_construir_contexto_metodologia()`** | Instrucción de estilo por metodología |

### 7.3 Metodologías soportadas

| Metodología | Instrucción de estilo |
|---|---|
| **ERCA** | Inicio = vivencia concreta; Desarrollo = reflexión→conceptualización→aplicación |
| **ABP** | Inicio = problema real; Desarrollo = análisis→investigación→diseño→validación |
| **Aula Invertida** | Inicio = verificar tarea previa (NO explicar); Desarrollo = debate + análisis |
| *(sin especificar)* | Secuencia estándar MINEDU: motivación→saberes previos→conflicto→cierre |

---

## 8. Seguridad y Autenticación

- **Hash de contraseñas:** `bcrypt` via `passlib`.
- **Tokens:** JWT (HS256) via `python-jose`. Expiración configurable en `auth_utils.py`.
- **Protección de endpoints:** Dependency `get_current_user` en todos los routes de generación, exportación y datos del usuario.
- **CORS:** Configurado explícitamente para `http://localhost:5173` (Vite dev server).

---

## 9. Gamificación

El módulo `gamification_logic.py` calcula automáticamente en cada login:

| Elemento | Lógica |
|---|---|
| **Puntos** | +10 por documento generado, +5 por mejora, +15 por exportación |
| **Nivel** | Calculado por umbrales de puntos acumulados |
| **Racha** | Días consecutivos de uso (lista `dias_uso` en `UserStats`) |
| **Badges** | Desbloqueados al alcanzar hitos (primer doc, 10 docs, etc.) |

---

## 10. Exportación de Documentos

| Formato | Implementación | Estado |
|---|---|---|
| **PDF** | `core/pdf_generator.py` (WeasyPrint) | ✅ Funcional |
| **DOCX** | `export.py` → `python-docx` | ⚠️ Simplificado (sin estilos institucionales) |

El PDF distingue automáticamente entre Unidad y Sesión por las claves presentes en el JSON.

---

## 11. RAG (Retrieval-Augmented Generation)

- **Servicio:** `core/rag_service.py` → consulta **Amazon Bedrock Knowledge Bases**.
- **Query tipo:** `"programación curricular {área} {grado} grado secundaria {temas}"`.
- **Integración:** El `GeneratorAgent` prepende el contexto RAG al prompt principal: `"CONTEXTO OFICIAL DEL MINEDU:\n{rag}\n\n{prompt}"`.
- **Fallo silencioso:** Si el RAG no responde, la generación continúa sin él (no bloquea el flujo).

---

## 12. Variables de Entorno (`.env`)

| Variable | Requerida | Descripción |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Sí | Acceso a Bedrock |
| `AWS_SECRET_ACCESS_KEY` | Sí | Acceso a Bedrock |
| `AWS_REGION` | Sí (default: `us-east-1`) | Región de Bedrock |
| `DATABASE_URL` | No (default: SQLite local) | URL de base de datos |
| `SECRET_KEY` | Sí | Clave para firmar JWT |
| `AZURE_OPENAI_ENDPOINT` | No | Fallback LLM |
| `AZURE_OPENAI_KEY` | No | Fallback LLM |
| `AZURE_OPENAI_DEPLOYMENT` | No | Nombre del deployment Azure |

---

## 13. Instalación y Ejecución

```bash
# 1. Clonar y entrar al proyecto
git clone https://github.com/jeffersonquispe/ia-gen-edu.git
cd ia-gen-edu

# 2. Backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
python run.py               # Levanta FastAPI en :8000

# 3. Frontend (otra terminal)
cd frontend
npm install
npm run dev                 # Levanta React en :5173
```

URL del sistema: `http://localhost:5173`
URL de la API (docs): `http://localhost:8000/docs`

---

## 14. Dependencias Principales

### Backend
| Paquete | Versión | Uso |
|---|---|---|
| `fastapi` | latest | Framework API REST |
| `uvicorn` | latest | Servidor ASGI |
| `sqlalchemy` | latest | ORM base de datos |
| `boto3` | latest | Cliente AWS (Bedrock) |
| `python-jose` | latest | JWT |
| `passlib[bcrypt]` | latest | Hash de contraseñas |
| `python-docx` | latest | Generación DOCX |
| `weasyprint` | latest | Generación PDF |
| `pydantic` | v2 | Validación de schemas |

### Frontend
| Paquete | Versión | Uso |
|---|---|---|
| `react` | 18 | UI |
| `vite` | latest | Build tool + dev server |
| `tailwindcss` | 3 | Estilos utilitarios |
| `axios` | latest | HTTP client |
| `react-router-dom` | 6 | Navegación SPA |
| `lucide-react` | latest | Iconografía |

---

## 15. Limitaciones Conocidas

| Limitación | Impacto | Solución futura |
|---|---|---|
| Exportación DOCX simplificada | No aplica estilos institucionales del MINEDU | Integrar `docx_generator.py` (versión Streamlit) |
| RAG depende de KB en Bedrock | Sin KB activo, genera sin contexto oficial | Continúa funcionando con prompts internos |
| SQLite no escala en producción | No apto para múltiples usuarios concurrentes en servidor | Migrar a PostgreSQL |
| Max 1 ciclo de autocorrección | Puede no resolver todos los errores estructurales | Aumentar `max_correcciones` o implementar retry exponencial |
| Sesión no recuerda la unidad padre automáticamente | El docente debe copiar el título de unidad manualmente | Implementar selector de unidades guardadas en el wizard |
