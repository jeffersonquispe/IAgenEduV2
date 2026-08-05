# HU-38: Definir e implementar (o retirar de la documentación) los puntos por acción directa

**Épica:** Gamificación | **Prioridad:** Baja | **Esfuerzo:** S

**Como** docente, **quiero** ganar puntos de forma predecible al generar, mejorar o exportar documentos, **para** que la gamificación se sienta activa y no dependa únicamente de alcanzar hitos de insignias.

## Contexto

Documentado en `docs/REGLAS_DE_NEGOCIO.md` §6.1. `docs/DETALLES_TECNICOS.md` §9 describe la regla *"+10 por documento generado, +5 por mejora, +15 por exportación"*, pero en la app activa la única línea que suma `puntos` es:

```python
stats.puntos += len(nuevos_badges) * 20
```

dentro de `GET /auth/stats` — es decir, **los puntos hoy solo vienen de desbloquear insignias**, nunca de la acción directa de generar/mejorar/exportar. Esta historia es una decisión de producto tanto como técnica: hay que elegir entre implementar la regla documentada o corregir la documentación para reflejar el comportamiento real (insignias como único mecanismo de puntos).

## Criterios de aceptación

Elegir una de las dos direcciones (no ambas):

- **Opción A — implementar la regla documentada:** `GenerationService` otorga +10 puntos al generar un documento, +5 al refinar (`refinar()`), y `export.py` +15 al exportar — de forma consistente con lo que ya describe `DETALLES_TECNICOS.md`.
- **Opción B — alinear la documentación con el código:** actualizar `DETALLES_TECNICOS.md` §9 para reflejar que los puntos provienen exclusivamente de insignias, retirando la afirmación de puntos por acción directa.

## Notas de implementación

- Baja prioridad frente a **HU-37** (que sí es un bug que bloquea insignias alcanzables) — esta historia es más una inconsistencia entre documentación e implementación que un defecto funcional grave, ya que el sistema de puntos actual (vía insignias) funciona, solo que de forma distinta a lo documentado.
- Si se elige la Opción A, revisar el balance de puntos junto con los umbrales de nivel en `calcular_nivel()` para que no se vuelva trivialmente fácil subir de nivel.

**Archivos relevantes:** `src/api/services/generation_service.py`, `src/api/routes/export.py`, `src/api/gamification_logic.py`, `docs/DETALLES_TECNICOS.md`

**Fuente:** `docs/REGLAS_DE_NEGOCIO.md` §6.1
