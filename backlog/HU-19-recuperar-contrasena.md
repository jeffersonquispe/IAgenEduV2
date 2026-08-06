# HU-19: Recuperar contraseña olvidada

> ✅ **Implementado — vía Supabase Auth, reemplazando el enfoque original de esta historia.** La primera versión (tabla `password_reset_tokens` propia + log del servidor en vez de email real, ver commit anterior) funcionaba pero nunca enviaba un correo de verdad. Se decidió migrar la autenticación completa a Supabase Auth (ver HU-21/HU-27, superadas por el mismo cambio), que maneja el envío de email de recuperación de forma nativa. La tabla `password_reset_tokens` y los endpoints `/auth/forgot-password`/`/auth/reset-password` fueron eliminados — ahora es 100% client-side: `Login.jsx` llama `supabase.auth.resetPasswordForEmail()`, y `ResetPassword.jsx` detecta la sesión de recuperación que llega en la URL del link y llama `supabase.auth.updateUser({password})`. **Decisión tomada:** se desactivó "Confirm email" (`mailer_autoconfirm=true`, ver HU-20) para simplificar demos, ya que el proyecto no tiene proveedor SMTP configurado. Esto resuelve el registro (ya no depende de que salga un correo), pero **el reseteo de contraseña de esta historia sigue sin poder enviar el email real** — `resetPasswordForEmail()` sigue necesitando SMTP configurado en Supabase para que el link de recuperación llegue de verdad. Configurar un proveedor SMTP en el dashboard (Authentication → Settings → SMTP) es el paso pendiente para cerrar esto del todo.

**Épica:** Autenticación | **Prioridad:** Alta | **Esfuerzo:** M

**Como** docente, **quiero** poder recuperar el acceso a mi cuenta si olvido mi contraseña, **para** no quedar bloqueado y depender de que alguien la resetee manualmente en la base de datos.

## Contexto

Hoy no existe ningún flujo de recuperación: `POST /auth/login` solo compara contra el hash almacenado y no hay endpoint de reseteo. La única forma actual de recuperar el acceso es reescribir `hashed_password` directamente en `edu_gen.db`.

## Criterios de aceptación

- `POST /auth/forgot-password` recibe un email y, si existe, genera un token de un solo uso con expiración corta (p. ej. 30 min) — no revela si el correo existe o no en la respuesta.
- `POST /auth/reset-password` recibe el token + nueva contraseña, valida vigencia/uso único del token, y actualiza `hashed_password` con `auth_utils.get_password_hash()`.
- El token de reseteo no reutiliza el JWT de sesión (no debe poder generarse un token de acceso a partir de él).
- Pantalla en el frontend (`Login.jsx` o nueva ruta) para solicitar el reseteo e ingresar la nueva contraseña.

## Notas de implementación

- Requiere un mecanismo de envío de correo (hoy no existe ninguno en el proyecto) o, como alternativa mínima para el alcance de tesis, un modo "admin" que genere el link/token para entregarlo manualmente sin depender de SMTP.
- Guardar el token hasheado (no en texto plano) si se persiste en base de datos, igual que la contraseña.

**Archivos relevantes:** `src/api/routes/auth.py`, `src/api/auth_utils.py`, `src/api/models.py`, `frontend/src/pages/Login.jsx`
