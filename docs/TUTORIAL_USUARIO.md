# Tutorial de usuario — Camino feliz (happy path)

Guion paso a paso para probar la aplicación de punta a punta: crear cuenta, generar una Unidad Didáctica, editarla y refinarla con IA, aprobarla, exportarla, y generar una Sesión de Aprendizaje. Pensado para seguirse **con la app corriendo en vivo**, no como referencia teórica.

No cubre casos límite ni errores — para eso está `REGLAS_DE_NEGOCIO.md` y el `backlog/`. Esto es únicamente el camino que funciona hoy, de principio a fin.

---

## 0. Antes de empezar

Dos servidores deben estar corriendo:

```bash
# Terminal 1 — backend, desde la raíz del proyecto
python run.py                    # http://localhost:8000

# Terminal 2 — frontend
cd frontend && npm run dev       # http://localhost:5173
```

Abre **http://localhost:5173** en el navegador. Si ves la pantalla de login, ambos servidores están listos.

---

## 1. Crear una cuenta

1. En la pantalla de login, haz clic en **"¿No tienes cuenta? Regístrate aquí"**.
2. Completa:
   - **Nombre completo**: cualquier nombre (ej. `Docente de Prueba`).
   - **Email**: cualquier correo con formato válido — no se verifica que exista de verdad (ej. `docente.prueba@ejemplo.com`).
   - **Contraseña**: la que quieras, sin reglas de complejidad exigidas.
3. Clic en **"Registrarse"**. Debe aparecer una alerta: *"Registro exitoso. Ahora puedes iniciar sesión."*
4. Vuelves automáticamente al formulario de login. Ingresa el mismo email/contraseña y clic en **"Ingresar"**.

Deberías caer en el **Dashboard** ("¡Hola Maestro! 👋").

> Si algo falla acá, revisa que el backend esté realmente arriba en :8000 — el frontend no avisa con claridad si no encuentra la API.

---

## 2. Generar una Unidad Didáctica

1. En el Dashboard, clic en la tarjeta **"Unidad Didáctica"** ("Genera una planificación curricular completa...").
2. Se abre el asistente de 3 pasos:

   **Paso 1 — Área y Grado**
   - Área Curricular: elige, por ejemplo, `Comunicación`.
   - Grado: elige, por ejemplo, `3°`.
   - Verás un aviso: "Las competencias disponibles se cargarán automáticamente para Comunicación". Clic en **Siguiente**.

   **Paso 2 — Competencias y Contexto**
   - Selecciona una o más competencias de la lista (mantén Ctrl/Cmd para elegir varias).
   - Si aparecen "Temas sugeridos", puedes elegir uno, o escribir los tuyos en "Temáticas / Contenidos adicionales" (ej. `El ensayo argumentativo`).
   - Cantidad de Sesiones: por ejemplo `2` (mientras más bajo, más rápido se genera).
   - Producto Final de Unidad: ej. `Ensayo argumentativo` — este campo determina cómo sale la rúbrica, vale la pena no dejarlo vacío para ver el efecto.
   - Clic en **Siguiente**.

   **Paso 3 — Confirmar y Generar**
   - Revisa el resumen.
   - Tienes dos botones: **Streaming** (ves el texto aparecer en tiempo real, pero el documento se guarda sin secciones separadas — ver nota abajo) y **Generar** (espera a que termine todo el pipeline, con validación automática de calidad).
   - Para el camino feliz completo, usa **Generar**.

3. Espera. El aviso dice "hasta 30 segundos", pero en pruebas reales el camino con validación completa tomó **hasta 2-3 minutos** — es normal, está pasando por generación + validación + una posible corrección automática antes de responder. No cierres la pestaña.

Al terminar, caes directo en el **Editor** con el documento recién creado.

> **Nota sobre Streaming:** si en el paso 3 usas el botón "Streaming" en vez de "Generar", el documento se guarda sin las secciones parseadas (solo el texto crudo) y sin pasar por el validador — es una vía más rápida de ver resultado, pero de menor garantía de estructura. Para probar el camino feliz completo, usa "Generar".

---

## 3. Revisar y refinar con IA en el Editor

El documento se muestra en secciones editables: Situación Significativa, Propósitos de Aprendizaje, Valores y Enfoques Transversales, Secuencia de Sesiones, Rúbrica Analítica.

1. Lee la **Situación Significativa** generada.
2. Al lado del título de cualquier sección hay un ícono de chispa (✨ "Asistente IA"). Haz clic ahí.
3. Aparece un campo de texto. Escribe una instrucción en lenguaje natural, por ejemplo: `Hazlo más breve` o `Usa un lenguaje más sencillo para adolescentes`.
4. Clic en **Refinar**. Espera unos segundos — el texto de esa sección se reemplaza con la versión mejorada.
5. También puedes editar cualquier sección directamente escribiendo en el cuadro de texto, sin usar IA.

Repite en 1-2 secciones más si quieres ver el refinamiento en acción varias veces.

---

## 4. Aprobar y exportar

1. Cuando estés conforme, clic en **"Aprobar Documento"** (botón verde, arriba a la derecha).
2. Las secciones pasan a modo solo-lectura y aparecen dos botones nuevos: **DOCX** y **PDF**.
3. Clic en **PDF** (o **DOCX**) — el navegador descarga el archivo directamente.
4. Abre el archivo descargado y confirma que el contenido coincide con lo que viste en el Editor.

Si quieres seguir editando después de aprobar, hay un enlace **"Editar de nuevo"** junto a los botones de exportación que vuelve al modo edición.

---

## 5. Volver al Dashboard y ver el documento guardado

1. Clic en **"← Volver al Dashboard"** (arriba a la izquierda del Editor).
2. En la sección **"Recientes"** del Dashboard debería aparecer la Unidad Didáctica que acabas de generar, con su tipo y fecha.
3. Clic sobre esa tarjeta — te vuelve a llevar al Editor con ese mismo documento (así se revisita un documento ya generado, sin tener que regenerarlo).

---

## 6. Generar una Sesión de Aprendizaje

1. Desde el Dashboard, clic en la tarjeta **"Sesión de Aprendizaje"**.
2. Wizard de 3 pasos:
   - **Paso 1**: Área y Grado (igual que para la Unidad).
   - **Paso 2**: **Título de la Unidad** — escribe el título de la Unidad que generaste en el paso 2 (esto es texto libre, no un selector — hoy no hay vínculo automático con unidades ya generadas). Tema de la Sesión, y **Metodología Activa**: elige entre `ERCA`, `ABP` o `Aula Invertida` — cada una cambia cómo se redacta el Inicio/Desarrollo de la clase.
   - **Paso 3**: Confirmar y **Generar**.
3. Espera (mismo orden de tiempo que la Unidad). Caes en el Editor con las secciones propias de una Sesión: Datos Informativos, Propósitos, Secuencia Didáctica, Reflexión sobre la Actividad, Rúbrica de Sesión.
4. Repite refinamiento/aprobación/exportación igual que en los pasos 3 y 4.

> Prueba generar la misma Sesión dos veces cambiando solo la Metodología (ej. ABP vs. Aula Invertida) para ver cómo cambia la Secuencia Didáctica — es una buena forma de validar que esa regla de negocio realmente funciona.

---

## 7. Cerrar sesión

En la barra lateral, al final, **"Cerrar Sesión"**. Vuelve a la pantalla de login y el token se borra del navegador.

---

## Resumen del camino feliz

```
Registro → Login → Dashboard
  → Generar Unidad (wizard 3 pasos) → Editor → refinar con IA → Aprobar → exportar PDF/DOCX
  → Volver al Dashboard → ver la Unidad en Recientes
  → Generar Sesión (wizard 3 pasos, distinta metodología) → Editor → Aprobar → exportar
  → Cerrar sesión
```

Si todo esto funciona sin errores, la aplicación está operativa de punta a punta. Cualquier fricción encontrada en el camino que no esté ya listada en `REGLAS_DE_NEGOCIO.md` o `backlog/` vale la pena documentarla como hallazgo nuevo.
