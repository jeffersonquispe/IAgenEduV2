# 📘 IA-GEN-EDU — Generador de Planificación Curricular con IA

Plataforma web que permite a docentes peruanos generar **Unidades Didácticas** y **Sesiones de Aprendizaje** alineadas al Currículo Nacional (CNEB/MINEDU) utilizando Inteligencia Artificial Generativa.

---

## 🎯 ¿Qué hace?

| Documento | Qué genera |
|---|---|
| **Unidad Didáctica** | Título motivador, Situación Significativa, Propósitos de Aprendizaje, Secuencia de Sesiones, Rúbrica Analítica (C/B/A/AD) vinculada al Producto Final |
| **Sesión de Aprendizaje** | Secuencia Didáctica adaptada a la metodología elegida (ERCA / ABP / Aula Invertida), Rúbrica Simplificada, Materiales, Reflexión docente |

Todos los documentos se exportan como **`.docx`** o **`.pdf`** listos para uso administrativo.

---

## ✨ Características clave

- 🧠 **Pipeline de Agentes IA**: Generador → Validador → Formateador, con autocorrección de errores estructurales.
- 📐 **Reglas de negocio pedagógicas**: el Producto Final gobierna la rúbrica; la Metodología cambia la estructura de la sesión.
- 📚 **RAG curricular**: las generaciones se enriquecen con documentos oficiales del MINEDU indexados en Amazon Bedrock Knowledge Bases.
- ✏️ **Editor interactivo por sección**: cada campo del documento es editable y refinable con IA mediante instrucción libre.
- 💾 **Historial persistente**: los documentos generados se guardan en base de datos por usuario.
- 🔐 **Autenticación JWT**: sistema de usuarios con roles y estadísticas de uso.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────┐
│              Frontend (React + Vite)         │
│  GenerationWizard → Editor → Export Buttons  │
└────────────────┬────────────────────────────┘
                 │ REST API (FastAPI)
┌────────────────▼────────────────────────────┐
│           Backend (Python / FastAPI)         │
│                                             │
│  AgentCoordinator                           │
│  ├── GeneratorAgent  ←── PromptManager      │
│  │     └── RAGService (Bedrock KB)          │
│  ├── ValidatorAgent                         │
│  │     ├── StructureValidator               │
│  │     └── ContentValidator (LLM)           │
│  └── FormatterAgent                         │
│                                             │
│  LLM Provider: Amazon Bedrock (Claude 3)    │
│  Fallback: Azure OpenAI → AWS Bedrock       │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│           SQLite (edu_gen.db)                │
│  Users · Documents · Stats                  │
└─────────────────────────────────────────────┘
```

---

## 📂 Estructura del proyecto

```
ia-gen-edu/
├── frontend/               # React + Vite + TailwindCSS
│   └── src/
│       ├── components/     # GenerationWizard, Sidebar
│       └── pages/          # Dashboard, Editor, Login
├── src/
│   ├── agents/             # coordinator, generator, validator, formatter
│   ├── api/                # FastAPI routes (auth, generation, export, data)
│   ├── core/               # bedrock_client, prompt_manager, rag_service, pdf_generator
│   ├── prompts/            # Plantillas de prompt en Markdown
│   ├── utils/              # Helpers
│   └── validators/         # structure_validator, content_validator
├── data/                   # Documentos curriculares MINEDU
├── .env                    # Variables de entorno (no se versiona)
├── requirements.txt
└── run.py                  # Punto de entrada del servidor
```

---

## ⚙️ Instalación

### Prerrequisitos

- Python 3.10+
- Node.js 18+
- Credenciales de AWS (para Amazon Bedrock)

### 1. Clonar el repositorio

```bash
git clone https://github.com/jeffersonquispe/ia-gen-edu.git
cd ia-gen-edu
```

### 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# AWS Bedrock
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Base de datos
DATABASE_URL=sqlite:///./edu_gen.db

# JWT
SECRET_KEY=your_secret_key_here

# Opcional: Azure OpenAI (fallback)
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_DEPLOYMENT=...
```

### 3. Instalar dependencias del backend

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 4. Instalar dependencias del frontend

```bash
cd frontend
npm install
```

### 5. Ejecutar

**Backend** (desde la raíz):
```bash
python run.py
```

**Frontend** (en otra terminal):
```bash
cd frontend
npm run dev
```

La aplicación estará disponible en `http://localhost:5173`.

---

## 🕹️ Flujo de uso

1. **Login** → Crear cuenta o ingresar.
2. **Dashboard** → Botón *Nueva Unidad* o *Nueva Sesión*.
3. **Wizard (3 pasos)**:
   - Paso 1: Área Curricular + Grado.
   - Paso 2 (Unidad): Competencias, Temáticas, **Producto Final**.
   - Paso 2 (Sesión): Título de Unidad, Tema, **Metodología** (ERCA / ABP / Aula Invertida).
   - Paso 3: Resumen y confirmación → *Generar Documento*.
4. **Editor** → Revisar, editar y refinar cada sección con IA.
5. **Aprobar** → Descargar como `.docx` o `.pdf`.

---

## 🧠 Metodologías soportadas en Sesión

| Metodología | Comportamiento del sistema |
|---|---|
| **ERCA** | Inicio: actividad vivencial. Desarrollo: reflexión → conceptualización → aplicación |
| **ABP** | Inicio: planteamiento de problema real. Desarrollo: análisis → diseño → validación |
| **Aula Invertida** | Inicio: verificar lectura/vídeo previo (sin explicar contenido nuevo). Desarrollo: debate y análisis profundo |

---

## 🐳 Docker (opcional)

```bash
docker-compose up --build
```

---

## 📋 Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | React 18, Vite, TailwindCSS |
| Backend API | FastAPI, SQLAlchemy, SQLite |
| IA | Amazon Bedrock (Claude 3 Sonnet), Bedrock Knowledge Bases |
| Exportación | python-docx, WeasyPrint |
| Auth | JWT (python-jose) |
| Contenedores | Docker, Docker Compose |

---

## 📘 Contexto académico

Este proyecto forma parte de una tesis de investigación sobre el uso de **IA Generativa en educación**, con enfoque en la reducción de la carga administrativa docente y la mejora de la calidad pedagógica mediante alineación automática con el Currículo Nacional de Educación Básica (CNEB) del MINEDU Perú.

La arquitectura implementa técnicas de **auto-crítica y corrección iterativa** (RSIP), **Retrieval-Augmented Generation (RAG)** con documentos oficiales, y un **pipeline de agentes** especialistas (Generador, Validador, Formateador) para garantizar la coherencia y calidad de los documentos producidos.