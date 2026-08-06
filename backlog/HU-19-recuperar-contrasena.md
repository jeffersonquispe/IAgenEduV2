# HU-19: Recuperar contraseña olvidada

> ✅ **Implementado.** Nueva tabla `password_reset_tokens` (`src/api/models.py` + `migrate_db.py`) guarda el hash SHA-256 del token (nunca el valor en texto plano), con expiración de 30 min y bandera `used`. `POST /auth/forgot-password` responde siempre el mismo mensaje genérico exista o no el correo (verificado: respuestas idénticas para email real vs. inexistente). Sin servicio de email configurado en el proyecto, el link de reseteo se registra en el log del servidor (`logger.warning`) en vez de enviarse por correo — alternativa mínima documentada en la propia historia; reemplazar por envío real de email en un despliegue de producción. `POST /auth/reset-password` valida token no usado + no expirado + contraseña ≥ 8 caracteres, y marca el token como usado (no reutilizable). El token de reseteo es independiente del JWT de sesión. Frontend: `Login.jsx` tiene un enlace "¿Olvidaste tu contraseña?" con formulario inline, y `ResetPassword.jsx` (ruta `/reset-password?token=...`) para completar el cambio. Verificado end-to-end: token inválido → 400, contraseña corta → 400, reset válido → 200 + login exitoso con la nueva contraseña, reintento del mismo token → 400.

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
