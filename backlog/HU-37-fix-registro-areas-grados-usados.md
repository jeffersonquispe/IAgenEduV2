# HU-37: Registrar áreas y grados usados en la app activa

**Épica:** Gamificación | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** poder desbloquear las insignias "Explorador Curricular" y "Multi-grado" usando la aplicación web (React), **para** que la gamificación funcione igual de bien que en la app anterior.

## Contexto

Documentado en `docs/REGLAS_DE_NEGOCIO.md` §6.4. Las insignias **Explorador Curricular** (3 áreas curriculares distintas) y **Multi-grado** (3 grados distintos) dependen de `UserStats.areas_usadas`/`grados_usados`, pero `GenerationService` (la app activa, FastAPI + React) **nunca escribe en esos campos** al generar un documento. Solo la app Streamlit legacy (`src/app/gamification.py`, líneas 106-109) lo hace:

```python
if area and area not in stats["areas_usadas"]:
    stats["areas_usadas"].append(area)
if grado and grado not in stats["grados_usados"]:
    stats["grados_usados"].append(grado)
```

Como consecuencia, un docente que use exclusivamente la app activa **no puede desbloquear estas dos insignias sin importar cuántas áreas o grados distintos use** — quedan inalcanzables en la práctica, aunque `check_new_badges()` sigue evaluando su condición en cada llamada a `/auth/stats`.

## Criterios de aceptación

- `GenerationService.crear_unidad()` y `crear_sesion()` agregan el área y el grado usados a `UserStats.areas_usadas`/`grados_usados` (sin duplicados), igual que ya hace `docs_generados`/`unidades_generadas`/`sesiones_generadas`.
- Tras generar documentos en 3 áreas distintas, la insignia "Explorador Curricular" se desbloquea la próxima vez que se consulta `GET /auth/stats` — mismo criterio para "Multi-grado" con 3 grados.
- No se requiere backfill de datos históricos: los documentos ya generados antes de este fix no necesitan "contarse" retroactivamente, solo los generados después.

## Notas de implementación

- Cambio pequeño y acotado: añadir dos líneas de actualización de listas (con chequeo de duplicados) en los mismos puntos donde `GenerationService` ya actualiza `UserStats` tras una generación exitosa.
- Buen candidato para cubrir con un test (ver **HU-25**), ya que es lógica pura fácil de verificar sin mockear Bedrock.

**Archivos relevantes:** `src/api/services/generation_service.py`, `src/api/gamification_logic.py` (referencia de la condición ya existente)

**Fuente:** `docs/REGLAS_DE_NEGOCIO.md` §6.4
