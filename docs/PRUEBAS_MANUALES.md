# Manual de Pruebas Manuales - Streaming Unificado

Este documento guía las pruebas manuales del nuevo sistema de generación unificado en streaming.
Reemplaza las dos rutas antiguas (bloqueante + streaming para Unidad, solo bloqueante para Sesión) con un único camino de streaming para ambas.

## Pre-requisitos

1. ✅ Backend corriendo: `python run.py` en :8000
2. ✅ Frontend corriendo: `npm run dev` en frontend/ (:5173)
3. ✅ Usuario registrado e iniciar sesión en http://localhost:5173/login
4. ✅ Dashboard visible en http://localhost:5173

## Sección 1: Generar Unidad Didáctica (Streaming Completo)

### Paso 1: Navegar al Wizard

1. En Dashboard, hacer clic en **"Crear Unidad"**
2. Debería abrirse el GenerationWizard con 3 pasos

### Paso 2: Rellenar formulario (Paso 1)

Datos de ejemplo:

| Campo | Valor |
|-------|-------|
| Área Curricular | `Comunicación` |
| Grado | `3°` |
| Competencias | ✅ `Estándares de Aprendizaje` (seleccionar 2) |
| Temas Centrales | `El ensayo argumentativo y su estructura` |
| Número de sesiones | `4` |
| Producto Final | `Ensayo argumentativo sobre un tema relevante` |

Hacer clic en **"Siguiente →"**

### Paso 3: Confirmar datos (Paso 2)

Revisar el resumen, debe mostrar todos los campos ingresados.
Hacer clic en **"Siguiente →"**

### Paso 4: Generar (Paso 3 - El cambio clave)

**❌ Antes:** Había dos botones:
- "Generar" (bloqueante, con validación, pero lento/timeout)
- "Streaming" (rápido, sin validación)

**✅ Después:** Hay un solo botón:
- "Generar" (streaming, con validación automática)

1. Hacer clic en **"Generar"**
2. Debería ver:
   - ✅ Texto en vivo apareciendo en el preview (izquierda)
   - ✅ Texto sin Markdown literal (sin `**`, `#`, `|` visibles - todo limpio)
   - ✅ Mensaje "Generando con IA..." en la esquina superior
   - ⏳ Después de ~30-60 segundos, debería cambiar a "Validando y estructurando..."

### Paso 5: Validar resultado

Después de que termine el streaming + validación:

1. ✅ El Editor debe abrirse con **4 secciones editables**:
   - Situación Significativa
   - Propósitos de Aprendizaje
   - Secuencia de Sesiones
   - Rúbrica de la Unidad

2. ✅ Cada sección debe tener:
   - Contenido completo (no vacío)
   - Botón "Editar" funcional
   - Historial de versiones disponible

3. ✅ En la parte superior, debe mostrar:
   - Título de la unidad
   - Botones: "Guardar", "Exportar", "Volver"

### Paso 6: Editar y refinar (opcional)

1. Hacer clic en "Editar" en una sección
2. Modificar el contenido
3. Hacer clic en "Guardar"
4. Debería guardarse sin errores

## Sección 2: Generar Sesión de Aprendizaje (NUEVO - Streaming)

### Paso 1: Navegar al Wizard

1. En Dashboard, hacer clic en **"Crear Sesión"**
2. Debería abrirse el GenerationWizard (mismo componente que Unidad)

### Paso 2: Rellenar formulario

| Campo | Valor |
|-------|-------|
| Unidad Didáctica | `[Seleccionar de la lista]` |
| Tema | `Estructura del ensayo argumentativo` |
| Grado | `3°` |
| Metodología | `ERCA` |

Hacer clic en **"Siguiente →"** (igual que Unidad)

### Paso 3: Confirmar datos

Revisar el resumen.
Hacer clic en **"Siguiente →"**

### Paso 4: Generar (El cambio clave para Sesión)

**❌ Antes:** Solo había un botón "Generar" (bloqueante, sin streaming)

**✅ Después:** Mismo botón "Generar" pero ahora:
- Usa streaming (como Unidad)
- Muestra preview en vivo
- Emite evento "Validando y estructurando..." al terminar
- Muestra secciones parseadas en el Editor

1. Hacer clic en **"Generar"**
2. Debería ver el mismo comportamiento que Unidad:
   - ✅ Texto en vivo
   - ✅ Texto plano (sin Markdown literal)
   - ✅ "Generando con IA..." → "Validando y estructurando..."

### Paso 5: Validar resultado

El Editor debe abrirse con **3 secciones editables**:
- Datos Informativos
- Secuencia Didáctica
- Rúbrica de la Sesión

(Nota: Sesión tiene 3 secciones, Unidad tiene 4 — diferente estructura)

## Sección 3: Pruebas de Comportamiento Esperado

### ✅ Test 1: Texto en vivo limpio (stripMarkdownForPreview)

**Escenario:** Generar una Unidad

**Esperado:**
- El preview en vivo debe mostrar texto plano limpio
- ❌ NO debe haber: `**texto en negrita**`, `# Encabezado`, `| a | b |`, `---`, `* viñeta`
- ✅ SÍ debe haber: Texto leíble, cambios de línea, párrafos bien formateados

**Validación:**
- Mientras se genera, ver el preview izquierdo
- Confirmar que el texto es legible, sin sintaxis Markdown

### ✅ Test 2: Evento "validando" aparece

**Escenario:** Generar una Unidad en modo completo (default)

**Esperado:**
- Después de terminar el streaming de texto
- El mensaje cambia de "Generando con IA..." a "Validando y estructurando..."
- Esto ocurre mientras el backend valida y formatea

**Validación:**
- Ver en el console del navegador (`F12` → Network):
  - Múltiples eventos SSE con chunks de texto
  - Un evento con `{"validando": true}`
  - Un evento final con `{"done": true, "id": "...", "situacion_significativa": "...", ...}`

### ✅ Test 3: Evento final tiene campos parseados

**Escenario:** Generar una Unidad

**Esperado en el evento final:**
```json
{
  "done": true,
  "id": "doc-uuid-aqui",
  "situacion_significativa": "Contenido...",
  "propositos_de_aprendizaje": "Contenido...",
  "secuencia_de_sesiones": "Contenido...",
  "rubrica_unidad": "Contenido..."
}
```

**Validación:**
- Abrir DevTools (`F12`)
- Ir a Network → Buscar la solicitud a `/api/generate/unidad/stream`
- Expandir la respuesta (Response tab)
- Ver el último evento SSE
- Confirmar que tiene todos los campos (no solo `{"done": true, "id": "..."}`

### ✅ Test 4: Base de datos se actualiza correctamente

**Escenario:** Generar una Unidad

**Esperado:**
- Tabla `documents`: Nueva fila con `type="unidad"`
- Tabla `document_versions`: Nueva versión con el contenido completo
- Tabla `pipeline_runs`: Nueva fila con métricas (puntaje_validacion, errores, etc)
- Tabla `user_stats`: Incrementa `docs_generados`, `unidades_generadas`

**Validación:**
- Abrir SQLite: `sqlite3 edu_gen.db`
- Ejecutar:
  ```sql
  SELECT COUNT(*) FROM documents;
  SELECT * FROM documents ORDER BY created_at DESC LIMIT 1;
  SELECT COUNT(*) FROM document_versions;
  SELECT COUNT(*) FROM pipeline_runs;
  SELECT docs_generados, unidades_generadas FROM user_stats LIMIT 1;
  ```
- Verificar que los números incrementan tras cada generación

## Sección 4: Pruebas de Regresión (Funcionalidades que no deben romperse)

### ✅ Test 5: Refinar documento (Editor AI)

**Escenario:** Abrir un documento generado, hacer clic en "Editar", escribir un prompt de mejora

**Esperado:** El campo se mejora con IA sin afectar otras secciones

**Validación:**
- Generar Unidad
- Hacer clic en "Editar" en una sección
- Escribir: "Hazlo más conciso"
- Ver que la sección se mejora sin cambiar otras

### ✅ Test 6: Exportar documento

**Escenario:** Generar Unidad, hacer clic en "Exportar"

**Esperado:** Se descarga un archivo Word/PDF con la Unidad formateada

**Validación:**
- Ver que el archivo se descarga
- Abrirlo y confirmar que tiene todas las secciones

### ✅ Test 7: Ver historial de versiones

**Escenario:** Generar Unidad, editar una sección, ver versiones anteriores

**Esperado:** Historial muestra versiones anteriores con timestamps

**Validación:**
- Hacer clic en versión anterior
- Ver que muestra el contenido antiguo
- Volver a versión actual

## Sección 5: Pruebas de Error (Edge cases)

### ⚠️ Test 8: Timeout de Bedrock (no debería ocurrir tras fix)

**Antes:** Generación lenta (>60s) fallaba con "Read timeout on endpoint"

**Después:** Debería funcionar porque:
- BedrockClient ahora tiene `read_timeout=180`
- Configuración en `src/core/bedrock_client.py`

**Validación:**
- Generar una Unidad (puede tomar 2+ minutos si Bedrock está lento)
- ❌ NO debe dar error de timeout
- ✅ Debe completar exitosamente

### ⚠️ Test 9: Usuario sin sesión (seguridad)

**Escenario:** Intentar generar sin estar logueado

**Esperado:** Redirigir a login o error 401

**Validación:**
- Limpiar cookies/localStorage
- Intentar POST a `/api/generate/unidad/stream`
- Debería retornar 401 o redirigir

## Sección 6: Checklist Final

Antes de considerar completa la prueba, verificar:

- [ ] Generar Unidad: streaming con preview limpio
- [ ] Evento "validando" aparece
- [ ] Evento final tiene campos parseados
- [ ] Editor abre con 4 secciones para Unidad
- [ ] Generar Sesión: streaming funciona (es nuevo)
- [ ] Editor abre con 3 secciones para Sesión
- [ ] Refinar documento funciona
- [ ] Exportar documento funciona
- [ ] Base de datos se actualiza
- [ ] No hay errores en console del navegador
- [ ] No hay errores en logs del backend
- [ ] No timeout de Bedrock

## Notas sobre cambios internos

Para referencia (no necesita probar, pero explica qué cambió):

### Código eliminado ❌

- `src/api/routes/generation.py`: `POST /generate/unidad` (bloqueante)
- `src/api/routes/generation.py`: `POST /generate/sesion` (bloqueante)
- `src/api/services/generation_service.py`: Método `crear_unidad()`
- `src/api/services/generation_service.py`: Método `crear_sesion()`
- `frontend/src/components/GenerationWizard.jsx`: Botón "Streaming" (ahora el único es "Generar")
- `frontend/src/components/GenerationWizard.jsx`: `handleGenerate()` bloqueante para Sesión

### Código nuevo ✅

- `src/agents/generator_agent.py`: Métodos `construir_prompt_unidad()` y `construir_prompt_sesion()`
- `src/agents/coordinator.py`: Métodos `validar_y_formatear_unidad()` y `validar_y_formatear_sesion()`
- `src/api/services/generation_service.py`: Método `generar_sesion_stream_events()` (Sesión streaming)
- `src/api/routes/generation.py`: Ruta `POST /generate/sesion/stream` (Sesión streaming)
- `frontend/src/components/GenerationWizard.jsx`: Función `stripMarkdownForPreview()` (texto plano)
- `frontend/src/components/GenerationWizard.jsx`: Estado `validando` (muestra "Validando..." mensaje)
- `src/core/bedrock_client.py`: Config con `read_timeout=180` (fix de timeout)

### Cambios de comportamiento 🔄

| Aspecto | Antes | Después |
|--------|-------|---------|
| **Ruta Unidad** | 2 botones: "Generar" (bloqueante) + "Streaming" | 1 botón: "Generar" (streaming) |
| **Ruta Sesión** | 1 botón: "Generar" (bloqueante) | 1 botón: "Generar" (streaming) |
| **Preview texto** | Markdown literal (`**bold**`, etc) | Texto plano limpio |
| **Validación visual** | No hay indicación intermedia | "Validando..." tras streaming |
| **Evento final** | Solo `{"done": true, "id": "..."}` | `{"done": true, "id": "...", ...secciones}` |
| **Timeout Bedrock** | Falla en ~60s para generaciones lentas | Soporta hasta 180s |
