# HU-20: Verificación de correo al registrarse

**Épica:** Autenticación | **Prioridad:** Media | **Esfuerzo:** M

**Como** administrador del sistema, **quiero** que los docentes confirmen que son dueños del correo con el que se registran, **para** evitar cuentas con correos falsos o de terceros y reducir el riesgo de spam de registros.

## Contexto

`POST /auth/register` (`src/api/routes/auth.py`) crea la cuenta de inmediato con cualquier correo, sin verificación. No hay campo `is_verified`/`email_verified` en el modelo `User`.

## Criterios de aceptación

- El modelo `User` incorpora un campo `email_verified` (booleano, `default=False`).
- Al registrarse, se genera un token de verificación de un solo uso y se envía (o se expone, ver nota) un link de confirmación.
- `GET /auth/verify-email?token=...` marca la cuenta como verificada.
- Definir explícitamente si una cuenta no verificada puede o no iniciar sesión/generar documentos (recomendado: sí puede loguearse, pero se le muestra un aviso persistente hasta verificar).

## Notas de implementación

- Depende de la misma pieza faltante que HU-19: un mecanismo de envío de correo. Evaluar resolver ambas historias juntas compartiendo esa infraestructura (SMTP, o un servicio como SES ya que el proyecto usa AWS).

**Archivos relevantes:** `src/api/routes/auth.py`, `src/api/models.py`, `src/api/schemas.py`
