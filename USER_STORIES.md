# Historias de Usuario — IA-GEN-EDU

Historias de usuario que documentan las funcionalidades **ya implementadas** en la aplicación activa (FastAPI + React, ver `CLAUDE.md`). Cada historia sigue el formato `Como <rol> quiero <acción> para <beneficio>`, con criterios de aceptación derivados del comportamiento real del código (rutas, agentes, modelos) y referencia a los archivos donde vive la lógica.

**Rol principal:** Docente de educación secundaria (usuario final de la plataforma).

---

## Épica 1 — Autenticación y cuenta

### HU-01: Registro de cuenta
**Como** docente, **quiero** registrarme con mi correo y una contraseña, **para** crear mi cuenta y empezar a generar documentos.

**Criterios de aceptación:**
- El sistema rechaza el registro si el correo ya existe (`400 Email already registered`).
- La contraseña se almacena con hash bcrypt (`passlib`), nunca en texto plano.
- Al registrarse se crea automáticamente un registro `UserStats` inicial (puntos, nivel, racha en cero).

**Referencia:** `POST /auth/register` — `src/api/routes/auth.py`

---

### HU-02: Inicio de sesión
**Como** docente, **quiero** iniciar sesión con mi correo y contraseña, **para** acceder a mis documentos y funciones de generación.

**Criterios de aceptación:**
- Devuelve un token JWT (HS256, expira en 24h) si las credenciales son correctas; `403 Invalid Credentials` en caso contrario.
- Registra la fecha de conexión en `dias_uso` (para el cálculo de racha) y actualiza `ultima_conexion`.

**Referencia:** `POST /auth/login` — `src/api/routes/auth.py`, `src/api/auth_utils.py`

---

### HU-03: Sesión persistente en el navegador
**Como** docente, **quiero** que mi sesión se mantenga activa entre visitas, **para** no tener que autenticarme cada vez que abro la aplicación.

**Criterios de aceptación:**
- El token se guarda en `localStorage` y se reutiliza al recargar la app.
- Cualquier respuesta `401` de la API cierra la sesión automáticamente y redirige a `/login`.

**Referencia:** `frontend/src/App.jsx` (interceptor global de axios)

---

### HU-04: Acceso protegido a funciones del sistema
**Como** docente, **quiero** que solo yo pueda ver y generar mis propios documentos, **para** que mi información esté protegida frente a otros usuarios.

**Criterios de aceptación:**
- Todas las rutas de generación, exportación y datos de usuario exigen un token válido (`get_current_user`).
- Un token inválido o ausente responde `401 Could not validate credentials`.

**Referencia:** `get_current_user` en `src/api/routes/auth.py`, usado como dependencia en `generation.py`, `export.py`, `data.py`, `metrics.py`

---

## Épica 2 — Generación de documentos con IA

### HU-05: Generar una Unidad Didáctica
**Como** docente, **quiero** generar una Unidad Didáctica indicando área curricular, grado, competencias, temas, número de sesiones y producto final, **para** obtener un documento alineado al CNEB sin redactarlo desde cero.

**Criterios de aceptación:**
- El wizard de 3 pasos recoge los datos y llama a `POST /generate/unidad`.
- El **producto final** elegido determina el contenido de la rúbrica analítica (C/B/A/AD).
- El documento generado incluye: Título, Situación Significativa, Propósitos de Aprendizaje, Valores y Enfoques Transversales, Secuencia de Sesiones (con la cantidad exacta solicitada) y Rúbrica.

**Referencia:** `GenerationWizard.jsx`, `POST /generate/unidad` → `AgentCoordinator.generar_unidad_didactica()`, prompt `src/prompts/unidad_didactica.md`

---

### HU-06: Generar una Sesión de Aprendizaje con metodología específica
**Como** docente, **quiero** generar una Sesión de Aprendizaje vinculada a una unidad y elegir una metodología (ERCA, ABP o Aula Invertida), **para** obtener una secuencia didáctica coherente con mi enfoque pedagógico.

**Criterios de aceptación:**
- La metodología elegida cambia la estructura de Inicio/Desarrollo (p. ej. ABP inicia con un problema real; Aula Invertida verifica lectura previa en vez de explicar contenido nuevo).
- Si no se especifica metodología, se usa la secuencia estándar MINEDU (motivación → saberes previos → conflicto cognitivo → cierre).
- El documento incluye Datos Informativos, Propósitos, Secuencia Didáctica, Materiales y Rúbrica Simplificada.

**Referencia:** `POST /generate/sesion` → `AgentCoordinator.generar_sesion_aprendizaje()`, `_construir_contexto_metodologia()` en `src/agents/generator_agent.py`, prompt `src/prompts/sesion_aprendizaje.md`

---

### HU-07: Recibir contenido enriquecido con fuentes oficiales del MINEDU
**Como** docente, **quiero** que el contenido generado se apoye en documentos curriculares oficiales, **para** confiar en que está alineado al Currículo Nacional y no es solo texto genérico de IA.

**Criterios de aceptación:**
- Antes de generar, el sistema consulta la Knowledge Base de Amazon Bedrock con una query basada en área/grado/temas y antepone ese contexto al prompt.
- Si la consulta RAG falla, la generación continúa igualmente sin bloquear al usuario (degradación silenciosa).

**Referencia:** `src/core/rag_service.py`, invocado desde `GeneratorAgent`

---

### HU-08: Corrección automática de errores estructurales
**Como** docente, **quiero** que el sistema detecte y corrija automáticamente errores estructurales graves del documento generado, **para** recibir un resultado utilizable sin tener que detectar yo esos problemas.

**Criterios de aceptación:**
- `StructureValidator` valida que estén todas las secciones obligatorias y el formato correcto; `ContentValidator` (LLM) evalúa calidad semántica cuando no hay errores críticos.
- Si hay errores críticos, el `GeneratorAgent` reintenta una corrección (`max_correcciones = 1`) antes de continuar.
- El resultado de la validación (puntaje 0-100, errores críticos/advertencia, correcciones aplicadas) queda registrado por generación.

**Referencia:** `src/agents/coordinator.py` (`AgentCoordinator`), `src/validators/structure_validator.py`, `src/validators/content_validator.py`, tabla `pipeline_runs`

---

## Épica 3 — Edición y refinamiento del documento

### HU-09: Editar manualmente cualquier sección
**Como** docente, **quiero** editar directamente el texto de cualquier sección del documento generado, **para** ajustarlo a la realidad específica de mi aula.

**Criterios de aceptación:**
- Cada campo del documento (situación significativa, secuencia, rúbrica, etc.) es editable individualmente en `Editor.jsx`.

**Referencia:** `frontend/src/pages/Editor.jsx`

---

### HU-10: Refinar una sección con una instrucción en lenguaje natural
**Como** docente, **quiero** pedirle a la IA que mejore una sección con una instrucción libre (ej. "hazla más breve"), **para** ahorrar tiempo de reescritura manual.

**Criterios de aceptación:**
- `POST /generate/refine` aplica la instrucción sobre el contenido actual vía `AgentCoordinator.mejorar_documento()` (o `BedrockClient` directo como último recurso) y devuelve el texto modificado.
- Este flujo no pasa por el pipeline completo de validación/formateo (es una mejora puntual, no una generación completa).

**Referencia:** `POST /generate/refine` — `src/api/routes/generation.py`, `bedrock_services.mejorar_documento_con_instruccion()`

---

### HU-11: Consultar el historial de versiones de un documento
**Como** docente, **quiero** ver las versiones anteriores de un documento que he editado, **para** poder comparar o recuperar una versión previa si una edición no resultó como esperaba.

**Criterios de aceptación:**
- Cada edición guarda un snapshot completo del contenido en `document_versions`, con una etiqueta descriptiva del cambio (`change_label`) y su número de versión.
- El documento conserva `current_version` para saber cuál es la versión vigente.

**Referencia:** modelo `DocumentVersion` — `src/api/models.py`

---

## Épica 4 — Exportación

### HU-12: Exportar el documento como PDF
**Como** docente, **quiero** descargar la Unidad o Sesión final en formato PDF, **para** compartirla o imprimirla lista para uso administrativo.

**Criterios de aceptación:**
- `POST /export/pdf` genera el archivo distinguiendo automáticamente si el contenido corresponde a una Unidad o una Sesión, según las claves presentes en el JSON.

**Referencia:** `src/core/pdf_generator.py` (WeasyPrint), `POST /export/pdf` — `src/api/routes/export.py`

---

### HU-13: Exportar el documento como DOCX
**Como** docente, **quiero** descargar el documento en formato Word (.docx), **para** poder editarlo posteriormente en un procesador de texto institucional.

**Criterios de aceptación:**
- `POST /export/docx` genera un archivo `.docx` descargable con el contenido del documento.
- *Limitación conocida:* la exportación DOCX actual es simplificada y no aplica los estilos institucionales del MINEDU (a diferencia de `docx_generator.py`, versión más completa usada por la app Streamlit legacy).

**Referencia:** `POST /export/docx` — `src/api/routes/export.py`

---

## Épica 5 — Historial y datos curriculares

### HU-14: Ver mis documentos recientes
**Como** docente, **quiero** ver mis últimos documentos generados al entrar al Dashboard, **para** retomar o exportar trabajo anterior sin tener que regenerarlo.

**Criterios de aceptación:**
- `GET /data/documents` devuelve los últimos 10 documentos del usuario autenticado.

**Referencia:** `GET /data/documents` — `src/api/routes/data.py`

---

### HU-15: Elegir datos curriculares desde catálogos oficiales
**Como** docente, **quiero** seleccionar área curricular, grado, competencias y temas desde listas predefinidas del CNEB, **para** no tener que escribirlos manualmente ni arriesgarme a usar una nomenclatura incorrecta.

**Criterios de aceptación:**
- `GET /data/options` expone las áreas, grados, competencias y temas disponibles, usados para poblar el wizard.

**Referencia:** `GET /data/options` — `src/api/routes/data.py`, `src/core/competencias_curriculares.py`, `data/*.json`

---

## Épica 6 — Gamificación

### HU-16: Acumular puntos y subir de nivel
**Como** docente, **quiero** ganar puntos por generar documentos, mejorarlos y exportarlos, **para** sentirme motivado a usar la herramienta regularmente en mi planificación.

**Criterios de aceptación:**
- Se otorgan puntos por documento generado, por mejora aplicada y por exportación; el nivel se calcula según umbrales acumulados de puntos.

**Referencia:** `src/api/gamification_logic.py`, `GET /auth/stats`

---

### HU-17: Mantener una racha de uso
**Como** docente, **quiero** ver cuántos días consecutivos he usado la plataforma, **para** mantener el hábito de planificar mis clases con anticipación.

**Criterios de aceptación:**
- La racha se calcula a partir de la lista de días de uso (`dias_uso`) registrada en cada login.

**Referencia:** `calcular_racha()` — `src/api/gamification_logic.py`

---

### HU-18: Desbloquear insignias por hitos
**Como** docente, **quiero** desbloquear insignias al alcanzar hitos de uso (primer documento generado, 10 documentos, etc.), **para** tener un reconocimiento visible de mi progreso con la herramienta.

**Criterios de aceptación:**
- `GET /auth/stats` calcula insignias nuevas en cada consulta y las persiste en `badges_desbloqueados`, sumando puntos adicionales por cada una desbloqueada.

**Referencia:** `check_new_badges()` — `src/api/gamification_logic.py`, `GET /auth/stats` — `src/api/routes/auth.py`

---

## Notas para nuevas historias (backlog no incluido aquí)

Este documento cubre solo lo **implementado**. Limitaciones conocidas que podrían convertirse en historias futuras (ver `docs/DETALLES_TECNICOS.md` §15): estilos institucionales en DOCX, selector de unidad padre en el wizard de Sesión (hoy se copia el título manualmente), migración de SQLite a PostgreSQL para concurrencia real, y reintentos configurables en la autocorrección del pipeline.
