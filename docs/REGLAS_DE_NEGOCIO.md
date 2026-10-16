# Reglas de Negocio — IA-GEN-EDU

Este documento describe únicamente las **reglas de negocio** del sistema: qué decide qué, y bajo qué condición. No es una guía de arquitectura (ver `DETALLES_TECNICOS.md`) ni de instalación (ver `README.md`).

Cada regla está verificada contra el código de la app activa (FastAPI + React) a la fecha de este documento, con su archivo/función de origen. Donde el código difiere de lo que otros documentos del proyecto describen, se señala explícitamente — este documento prioriza lo que el sistema **hace hoy** sobre lo que se documentó que debería hacer.

---

## 1. Generación curricular

### 1.1 El Área Curricular es el filtro maestro
Cambiar el Área Curricular en el wizard invalida y limpia las Competencias y el Tema ya seleccionados — nunca se mezclan competencias de un área con otra.
**Origen:** `GenerationWizard.jsx` (`useEffect` sobre `formData.area`).

### 1.2 Las competencias se filtran por área
El selector de competencias solo muestra las vinculadas al área curricular elegida. Además de las propias del área se ofrecen las 2 competencias transversales del CNEB ("Se desenvuelve en entornos virtuales generados por las TIC" y "Gestiona su aprendizaje de manera autónoma"), que aplican a todas las áreas. El catálogo se verifica contra el Programa Curricular (`src/tests/test_catalogo_competencias.py`).
**Origen:** `GET /data/competencias?area=`, `src/core/competencias_curriculares.py`.

### 1.3 Selección múltiple de competencias
El docente puede elegir más de una competencia por Unidad. El frontend las envía como lista; el backend las concatena en un solo texto separado por `", "` antes de pasarlas al generador.

> ⚠️ **Inconsistencia real detectada:** `GeneratorAgent._construir_contexto_competencia()` espera las competencias separadas por salto de línea (`\n`) para tratarlas como una lista y generar la instrucción "USA EXACTAMENTE estas N competencias". Como el backend las une con `", "` (no `\n`), al elegir 2+ competencias llegan como **un solo string**, y el prompt las trata como si fuera una única competencia obligatoria (rama `else`) en vez de una lista explícita. El contenido de ambas competencias sigue llegando al modelo, pero no con la instrucción reforzada que el código fue diseñado para dar cuando hay varias.
> **Origen:** `src/api/services/content_parsers.py`/`generation_service.py` (`", ".join(competencias)`) vs. `src/agents/generator_agent.py::_construir_contexto_competencia` (`competencia.split('\n')`).

### 1.4 El Producto Final gobierna la rúbrica
Si se especifica un Producto Final (ej. "ensayo argumentativo", "maqueta"), el prompt marca ese bloque como **OBLIGATORIO** y exige que la rúbrica evalúe dimensiones de ese producto específico. Si no se especifica, el modelo elige un producto apropiado por su cuenta.
**Origen:** `_construir_contexto_producto` en `generator_agent.py`.

### 1.5 La Metodología cambia la estructura de la Sesión (no de la Unidad)
Solo aplica al generar una Sesión de Aprendizaje:

| Metodología | Regla de Inicio | Regla de Desarrollo |
|---|---|---|
| **ABP** | Presenta un problema real y cercano; no explica teoría | Análisis del problema → investigación → diseño de solución → validación ante pares |
| **Aula Invertida** | No presenta contenido nuevo; verifica lo estudiado en casa (3-4 preguntas); el docente no expone | Debates grupales, análisis de casos, creación colaborativa |
| **ERCA** | Actividad vivencial concreta, sin teoría previa | Reflexión guiada → conceptualización → aplicación práctica |
| *(sin especificar)* | Sin instrucción de estilo particular — el modelo usa la secuencia estándar MINEDU | — |

**Origen:** `GeneratorAgent._construir_contexto_metodologia()`.

### 1.6 El número de sesiones es exacto, no una sugerencia
El prompt exige "EXACTAMENTE N sesiones, numeradas del 1 al N" — no es una cota superior.
**Origen:** `contexto_sesiones` en `generator_agent.py`.

### 1.7 Valores y enfoques transversales: del perfil institucional, con default genérico del CNEB
Los valores y enfoques de la sección "Valores y Enfoques Transversales" se resuelven así (HU-36):
1. Si el docente configuró **valores propios** en su perfil institucional (HU-31), se usan esos.
2. Si no hay perfil, o su lista de valores está vacía o en blanco, se usa el **default genérico del CNEB** (`VALORES_CNEB_DEFAULT`, sin contenido confesional). Lo mismo aplica a los enfoques.
3. La lista de una institución católica (13 valores, incluye *"Encuentro personal con Jesucristo"*, *"Caridad"*) **no es el default**: es un preset que el docente carga de forma explícita desde la pantalla de Institución. Elegirlo solo rellena el campo; se guarda como valores propios cuando pulsa Guardar.

> Antes de HU-36 esa lista católica estaba fija en el código (`VALORES_PERMITIDOS`) y se aplicaba a todo documento, sin importar el colegio.
> **Origen:** `resolver_valores_institucionales()` / `resolver_enfoques_transversales()` en `core/valores_institucionales.py`; presets en `GET /institucion/presets-valores`.

### 1.8 El contexto RAG enriquece pero nunca bloquea
Si la consulta a la Knowledge Base de Bedrock falla o no devuelve resultados, la generación continúa igual, solo que sin ese contexto adicional — nunca es un error fatal.
**Origen:** `RAGService`, invocado desde `GeneratorAgent`.

---

## 2. Validación y calidad estructural

### 2.1 Secciones obligatorias por tipo de documento

| Unidad Didáctica | Sesión de Aprendizaje |
|---|---|
| TÍTULO | DATOS INFORMATIVOS |
| SITUACIÓN SIGNIFICATIVA | SITUACIÓN SIGNIFICATIVA |
| PROPÓSITOS | PROPÓSITOS |
| EVIDENCIAS | SECUENCIA DIDÁCTICA |
| INSTRUMENTOS | MATERIALES |
| VALORES | |
| SECUENCIA | |

Si falta cualquiera de estas, se registra como error **CRÍTICO**.
**Origen:** `StructureValidator.SECCIONES_UNIDAD` / `SECCIONES_SESION`.

### 2.2 El contenido debe vivir en tablas Markdown, formato ITEM | CONTENIDO
- Debe existir al menos una tabla (mínimo 2 filas × 2 columnas) — si no, error **CRÍTICO**.
- El orden de columnas debe ser `ITEM | CONTENIDO`; si aparece invertido (`CONTENIDO | ITEM`), es **ADVERTENCIA** (y se corrige automáticamente en el formateo, ver §3).
- Más de 3 líneas de contenido fuera de cualquier tabla → **ADVERTENCIA**.
- Etiquetas HTML residuales (`<br>`, `<p>`, `<div>`, etc.) → **ADVERTENCIA**.
- Para Sesión específicamente: la secuencia didáctica debe mencionar los tres momentos INICIO, DESARROLLO y CIERRE — cada uno ausente es una **ADVERTENCIA** separada.

**Origen:** `StructureValidator` (`src/validators/structure_validator.py`).

### 2.3 Puntaje de validación
Empieza en 100 y descuenta: **-25** por error crítico, **-10** por advertencia, **-2** por error informativo. El documento se considera "válido" (`es_valido`) si y solo si **no tiene ningún error crítico** — el puntaje en sí no define validez, solo la presencia de críticos.
**Origen:** `ValidationReport.puntaje` / `.es_valido`.

### 2.4 Autocorrección: un solo intento
Si la validación encuentra errores críticos, el sistema le devuelve esos errores al generador y le pide corregir — **una sola vez** (`max_correcciones = 1`). Si tras ese intento persisten errores críticos, el documento se entrega igual, sin un segundo intento.
**Origen:** `AgentCoordinator.max_correcciones`.

### 2.5 El camino de generación con streaming NO se valida
`POST /generate/unidad/stream` no pasa por `ValidatorAgent` ni `FormatterAgent` — llama a Bedrock directo y guarda el resultado crudo. Es una divergencia real de calidad entre generar con streaming (más rápido de ver, sin garantías estructurales) y generar sin streaming (más lento, con validación y autocorrección).
**Origen:** `GenerationService.generar_unidad_stream_events()` vs. `crear_unidad()`.

---

## 3. Formato y limpieza automática del contenido

- Si el modelo devuelve texto sin ninguna tabla, el sistema **lo envuelve automáticamente** en una tabla `| ITEM | CONTENIDO |`, detectando encabezados por patrones (`**Negrita**`, líneas en MAYÚSCULAS cortas, `Etiqueta: texto`).
- Cualquier línea suelta que aparezca dentro de una zona de tabla ya iniciada se convierte en una fila `|  | contenido_suelto |` — nunca queda texto libre "colgando" dentro de una tabla.
- Las viñetas (`•`, `-`, `*`, `→`, etc.) se eliminan dentro de las celdas; `<br>` se convierte en salto de línea real.

**Origen:** `src/utils/table_utils.py` (`asegurar_tabla`, `forzar_contenido_en_tabla`, `limpiar_html`), orquestado por `FormatterAgent`.

---

## 4. Cuentas y acceso

- El registro exige correo único; la contraseña se guarda como hash bcrypt, nunca en texto plano.
- El token de sesión (JWT, HS256) expira a las **24 horas**.
- Toda ruta de generación, exportación o datos de usuario exige un token válido — sin excepción.
- Cualquier respuesta `401` cierra la sesión del lado del cliente automáticamente (interceptor global de axios).
- **No hay verificación de correo ni recuperación de contraseña hoy** — cualquier correo sintácticamente válido puede registrarse, y si se olvida la contraseña no hay forma de recuperarla desde la aplicación (ver backlog HU-19, HU-20).

**Origen:** `src/api/routes/auth.py`, `src/api/auth_utils.py`, `frontend/src/App.jsx`.

---

## 5. Documentos y versiones

- Cada refinamiento con IA sobre un documento existente guarda automáticamente un snapshot de la versión **anterior** (no la nueva) antes de aplicar el cambio, con una etiqueta derivada de la instrucción usada (ej. "Antes de refinar: hazlo más breve...").
- `Document.current_version` se incrementa en cada refinamiento — es el número de versión vigente, no un conteo de ediciones.
- El Dashboard solo muestra los **últimos 10** documentos del usuario — no hay búsqueda ni paginación (ver backlog HU-24).

**Origen:** `GenerationService._save_version`, `GET /data/documents`.

---

## 6. Gamificación

### 6.1 Puntos por acción directa e insignias
Los puntos se **calculan** a partir de los contadores del usuario (HU-38), no se acumulan con incrementos sueltos:

| Acción | Puntos |
|---|---|
| Documento generado | +10 |
| Mejora con IA | +5 |
| Exportación (DOCX o PDF) | +15 |
| Insignia desbloqueada | +20 |

`puntos = docs_generados×10 + mejoras_realizadas×5 + (exportaciones_docx + exportaciones_pdf)×15 + insignias×20`, recalculado y persistido en cada `GET /auth/stats`. Es la misma fórmula que ya usaba la app Streamlit legacy, ampliada con las exportaciones.
**Origen:** `calcular_puntos()` en `gamification_logic.py`.

> ⚠️ Cada mejora y cada exportación suma, sin tope por documento: repetir una exportación vuelve a sumar +15. Si el balance de niveles se vuelve trivial, el ajuste natural es contar a lo sumo una exportación por documento.

### 6.2 Nivel por umbral de puntos acumulados

| Nivel | Rango de puntos |
|---|---|
| Principiante 🌱 | 0–99 |
| Intermedio 🌿 | 100–299 |
| Avanzado 🌳 | 300–599 |
| Experto 👑 | 600–999 |
| Maestro 💎 | 1000+ |

**Origen:** `calcular_nivel()` en `gamification_logic.py`.

### 6.3 Racha de uso
Cuenta días **consecutivos** hacia atrás desde hoy o ayer (si no se usó hoy ni ayer, la racha es 0 — no se "perdona" un día salteado).
**Origen:** `calcular_racha()`.

### 6.4 Ocho insignias — dos de ellas inalcanzables hoy en la app activa

| Insignia | Condición | ¿Alcanzable hoy? |
|---|---|---|
| Primer Paso 🌱 | 1 documento generado | ✅ |
| Explorador Curricular 🗺️ | 3 áreas curriculares distintas usadas | ❌ — ver nota |
| Maestro del Detalle ✨ | 5 mejoras con IA | ✅ |
| Multi-grado 📚 | 3 grados distintos usados | ❌ — ver nota |
| Prolífico 🏅 | 10 documentos generados | ✅ |
| Exportador Pro 📄 | 5 exportaciones (DOCX o PDF) | ✅ |
| Maratón 🔥 | Racha de 3 días de uso | ✅ |
| Perfeccionista 💎 | 10 mejoras con IA | ✅ |

> ⚠️ **Explorador Curricular** y **Multi-grado** dependen de `UserStats.areas_usadas`/`grados_usados`, pero `GenerationService` (la app activa) nunca escribe en esos campos al generar un documento — solo la app Streamlit legacy (`src/app/gamification.py`) lo hace. Un docente que use exclusivamente la app activa (React) no puede desbloquear estas dos insignias sin importar cuántas áreas o grados distintos use.

**Origen:** `BADGES`, `check_new_badges()` en `gamification_logic.py`; comparar con `src/app/gamification.py` (legacy).

---

## 7. Reglas declaradas en otros documentos pero no implementadas

`FLUJO_APLICATIVO(2).md` describe varias reglas de negocio como si ya existieran; al contrastarlas contra el código, estas **no están implementadas** hoy y viven como historias en `backlog/`:

| Regla declarada | Historia | Estado |
|---|---|---|
| La Sesión "recuerda" la Unidad automáticamente | HU-22 | El docente escribe el título de la unidad a mano, sin vínculo real |
| No debe haber temas repetidos entre sesiones de una unidad | HU-29 | Sin ninguna validación de duplicados |
| El botón de descarga solo aparece si la validación pasa | HU-30 | Implementado como aviso + confirmación explícita (no bloqueo total); la validación se actualiza al editar o refinar |
| Datos de la institución (nombre, visión, contexto) | HU-31, HU-32 | Implementado: perfil institucional que contextualiza la generación — ver §1.7 |

---

*Documento generado a partir de una lectura directa del código en `src/` y `frontend/`, no de la documentación funcional previa — donde ambas difieren, se preferió el comportamiento real verificado.*
