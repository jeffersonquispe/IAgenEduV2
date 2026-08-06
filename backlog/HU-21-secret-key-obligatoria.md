# HU-21: `SECRET_KEY` obligatoria por entorno

> ✅ **Implementado.** `src/api/auth_utils.py` ya no tiene valor por defecto: `SECRET_KEY = os.getenv("SECRET_KEY")` + `RuntimeError` explícito si falta, con `load_dotenv()` en el propio módulo (no depende de que `run.py` lo haya cargado antes). Documentada en `.env.example` (nuevo archivo). El valor hardcodeado que estaba expuesto en el repo fue rotado — sesiones/tokens emitidos antes de este cambio quedaron invalidados.

**Épica:** Seguridad | **Prioridad:** Alta | **Esfuerzo:** S

**Como** administrador del sistema, **quiero** que la aplicación exija una `SECRET_KEY` propia por entorno, **para** que los tokens JWT no puedan falsificarse usando un valor por defecto conocido y público (presente en el propio repositorio).

## Contexto

```python
# src/api/auth_utils.py
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
```

Si `SECRET_KEY` no está definida en `.env`, se usa este valor hardcodeado — que además queda expuesto en el historial de git. Cualquiera que lea el código puede firmar tokens JWT válidos para cualquier usuario si un despliegue llega a correr sin la variable configurada.

## Criterios de aceptación

- Al arrancar sin `SECRET_KEY` en el entorno, la aplicación falla explícitamente (o registra un warning claro) en vez de usar un valor por defecto silencioso.
- El valor hardcodeado actual se retira del código.
- `.env`/`env.example` documentan `SECRET_KEY` como variable obligatoria (ver también HU-26, sobre mantener la documentación de variables de entorno al día).
- Si el valor hardcodeado ya se usó en algún ambiente real, rotarlo invalida las sesiones existentes (documentar este efecto secundario).

## Notas de implementación

- Cambio pequeño y de bajo riesgo, pero de impacto de seguridad alto — buen candidato para resolver antes que las demás historias de esta lista.

**Archivos relevantes:** `src/api/auth_utils.py`, `.env`
