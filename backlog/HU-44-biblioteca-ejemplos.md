# HU-44: Biblioteca de ejemplos y plantillas de referencia dentro de la plataforma

**Épica:** Soporte al docente / Onboarding | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** consultar dentro de la plataforma ejemplos reales de una Unidad Didáctica y una Sesión de Aprendizaje ya completas, **para** entender qué se espera de cada sección antes de generar la mía o mientras edito una ya generada.

## Contexto

La reunión de planificación identifica como entregable concreto: *"Material de apoyo: entrega de archivos y ejemplos prácticos de sesiones y unidades para que los docentes puedan guiarse en el proceso."* Hoy esos ejemplos existen solo como archivos sueltos (`Unidad ejemplo.docx`, `Sesión de Aprendizaje ejm.docx`) fuera de la aplicación — no hay ninguna pantalla ni endpoint que los exponga a un docente usando el sistema activo.

## Criterios de aceptación

- Nueva sección accesible desde el Dashboard/Sidebar ("Ejemplos" o "Guía") que muestra al menos un ejemplo completo de Unidad y uno de Sesión, en el mismo formato visual que usa el Editor.
- El docente puede ver el ejemplo sin que cuente como una generación (no consume el pipeline de IA ni gasta puntos/cuota de gamificación).
- Los ejemplos se pueden actualizar sin desplegar código (archivo de datos versionado, no hardcodeado en el JSX).

## Notas de implementación

- Los ejemplos ya extraídos de `Unidad ejemplo.docx` y `Sesión de Aprendizaje ejm.docx` pueden servir de contenido semilla; conviene guardarlos como fixtures JSON con la misma forma que `Document.content` (ver `docs/DETALLES_TECNICOS.md` §4.2) para reutilizar el Editor/visor existente en modo solo-lectura.

**Archivos relevantes:** `frontend/src/pages/` (nueva página), `frontend/src/components/Sidebar.jsx`, nueva ruta de datos estáticos o endpoint `GET /data/ejemplos`

**Fuente:** notas de reunión ("Material de apoyo... ejemplos prácticos de sesiones y unidades")
