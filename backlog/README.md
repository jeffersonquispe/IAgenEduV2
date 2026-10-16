# Backlog — IA-GEN-EDU

Historias de usuario **pendientes de implementar**, derivadas de limitaciones conocidas del proyecto (ver `docs/DETALLES_TECNICOS.md` §15 y las notas finales de `USER_STORIES.md`), de una revisión del código activo (`src/api/`, `frontend/`), de contrastar `docs/FLUJO_APLICATIVO(2).md` (documento funcional/reglas de negocio) contra lo que el código realmente hace hoy, y de `docs/REGLAS_DE_NEGOCIO.md` (reglas de negocio verificadas directamente contra el código). Continúan la numeración de `USER_STORIES.md` (que documenta lo ya implementado).

Cada historia vive en su propio archivo para poder moverse a un tablero (Jira/Trello/GitHub Projects) sin reformatear. Formato: narrativa `Como/quiero/para`, criterios de aceptación, prioridad, esfuerzo estimado y archivos relevantes.

## Índice

| # | Historia | Épica | Prioridad | Esfuerzo |
|---|---|---|---|---|
| ~~[HU-19](HU-19-recuperar-contrasena.md)~~ | ✅ Recuperar contraseña olvidada | Autenticación | Alta | M |
| ~~[HU-20](HU-20-verificacion-email.md)~~ | ✅ (código listo; requiere activar "Confirm email" en Supabase) Verificación de correo al registrarse | Autenticación | Media | M |
| ~~[HU-21](HU-21-secret-key-obligatoria.md)~~ | ✅ `SECRET_KEY` obligatoria por entorno | Seguridad | Alta | S |
| ~~[HU-22](HU-22-selector-unidad-padre.md)~~ | ✅ Selector de unidad padre al crear una Sesión | Generación | Alta | S |
| ~~[HU-23](HU-23-exportacion-docx-institucional.md)~~ | ✅ Exportación DOCX con estilos institucionales | Exportación | Media | M |
| ~~[HU-24](HU-24-busqueda-filtrado-documentos.md)~~ | ✅ Búsqueda y filtrado de documentos | Historial | Media | S |
| ~~[HU-25](HU-25-tests-automatizados.md)~~ | ✅ Suite de tests automatizados | Calidad técnica | Alta | L |
| ~~[HU-26](HU-26-actualizar-requirements.md)~~ | ✅ `requirements.txt` fiel a las dependencias reales | Calidad técnica | Alta | S |
| ~~[HU-27](HU-27-migracion-postgresql.md)~~ | ✅ Migración de SQLite a PostgreSQL | Infraestructura | Baja | L |
| [HU-28](HU-28-campo-institucion-educativa.md) | ~~Campo "Institución Educativa" en la generación~~ → ver HU-31/HU-32 | Generación | — | — |
| ~~[HU-29](HU-29-validar-temas-no-repetidos.md)~~ | ✅ (fase 1) Validar que no haya temas repetidos entre sesiones | Calidad del contenido | Media | M |
| ~~[HU-30](HU-30-gating-exportacion-por-validacion.md)~~ | ✅ Bloquear exportación si el documento no pasa validación | Calidad / Exportación | Media | M |
| ~~[HU-31](HU-31-perfil-institucional.md)~~ | ✅ Perfil institucional del docente (nombre, visión, contexto) | Generación | Media | M |
| ~~[HU-32](HU-32-contexto-institucional-en-generacion.md)~~ | ✅ Inyectar el contexto institucional en el pipeline de generación | Generación | Media | S-M |
| ~~[HU-33](HU-33-generacion-como-job-asincrono.md)~~ | ✅ (código listo; requiere aplicar supabase/migrations/20261008_generation_jobs.sql) Generación de documentos como job asíncrono | Infraestructura | Media | L |
| ~~[HU-34](HU-34-limite-concurrencia-bedrock.md)~~ | ✅ Límite de concurrencia para llamadas a Bedrock | Infraestructura | Media | S |
| ~~[HU-35](HU-35-fix-join-competencias-multiples.md)~~ | ✅ Corregir el ensamblado de competencias múltiples en el prompt | Calidad del contenido | Media | S |
| ~~[HU-36](HU-36-valores-institucionales-configurables.md)~~ | ✅ Hacer configurables los valores y enfoques transversales institucionales | Generación | Alta | S-M |
| ~~[HU-37](HU-37-fix-registro-areas-grados-usados.md)~~ | ✅ Registrar áreas y grados usados en la app activa (insignias rotas) | Gamificación | Media | S |
| ~~[HU-38](HU-38-definir-puntos-por-accion.md)~~ | ✅ (Opción A) Definir e implementar (o retirar de la documentación) los puntos por acción directa | Gamificación | Baja | S |
| ~~[HU-39](HU-39-criterios-alineados-a-sesiones.md)~~ | ✅ Alinear el número de criterios de evaluación (y filas de rúbrica) con el número de sesiones | Calidad del contenido | Alta | S-M |
| ~~[HU-40](HU-40-materiales-basicos-unidad.md)~~ | ✅ Sección "Materiales Básicos" (docente/estudiante) en la Unidad Didáctica | Generación | Media | S |
| ~~[HU-41](HU-41-reto-explicito-sesion.md)~~ | ✅ Campo "Reto" explícito en la Situación Significativa de la Sesión | Generación | Media | S |
| ~~[HU-42](HU-42-matriz-axiologica-estructurada.md)~~ | ✅ Matriz axiológica institucional estructurada (Valor/Enfoque/Comportamiento/Instrumento) | Personalización institucional | Media | M |
| ~~[HU-43](HU-43-recurso-previo-aula-invertida.md)~~ | ✅ Adjuntar recurso previo (enlace) para sesiones con Aula Invertida | Generación | Baja | S |
| ~~[HU-44](HU-44-biblioteca-ejemplos.md)~~ | ✅ Biblioteca de ejemplos y plantillas de referencia dentro de la plataforma | Onboarding | Media | M |
| ~~[HU-45](HU-45-limite-competencias-seleccionables.md)~~ | ✅ (Unidad; la Sesión hereda las de su Unidad, sin selector propio) Límite máximo de competencias seleccionables por documento | Calidad del contenido | Media | S |
| ~~[HU-46](HU-46-datos-informativos-completos.md)~~ | ✅ Completar "Datos Informativos" institucionales (DRE/UGEL, fechas, coordinación) | Personalización institucional | Baja | S-M |
| ~~[HU-47](HU-47-plantilla-oficial-control-documentario.md)~~ | ✅ (requiere aplicar supabase/migrations/20261009_institution_control_documentario.sql) Exportación fiel a la plantilla oficial (encabezado y control documentario) | Exportación | Baja | S |
| ~~[HU-48](HU-48-subir-plantilla-institucional.md)~~ | ✅ (ya existía en el código) Subir y parsear la plantilla institucional (Unidad/Sesión) en un esquema reutilizable | Plantillas institucionales | Media | L |
| ~~[HU-49](HU-49-generacion-guiada-por-plantilla.md)~~ | ✅ (ya existía en el código) Generación de contenido guiada por la plantilla institucional activa | Plantillas institucionales | Media | M |
| ~~[HU-50](HU-50-exportar-sobre-plantilla-original.md)~~ | ✅ (ya existía en el código) Exportar el documento rellenando directamente el archivo de plantilla subido | Plantillas institucionales | Media | M |

Prioridad y esfuerzo son una primera estimación para ordenar el trabajo; ajústalos según el alcance real de la tesis.

## Historias derivadas de la reunión de planificación docente, `Lineamientos.docx`, `Unidad ejemplo.docx` y `Sesión de Aprendizaje ejm.docx` (HU-39 a HU-47)

Contrastar los formatos oficiales reales (RSE) contra lo que el pipeline de generación produce hoy reveló varias brechas concretas, no solo declaraciones de alcance futuro:

- **HU-39** es la más crítica: el prompt de Unidad pide un número **fijo** de 3 criterios de evaluación/filas de rúbrica sin importar `num_sesiones` (cuyo default en el wizard es 6) — rompe la relación 1:1 criterio↔sesión que el lineamiento exige explícitamente.
- **HU-40** y **HU-41** son secciones que existen en la plantilla oficial pero no en el prompt/validador actual (materiales básicos de Unidad, reto explícito de Sesión) — confirmado contra `StructureValidator.SECCIONES_UNIDAD`/`SECCIONES_SESION`.
- **HU-42** extiende **HU-31/HU-36** (contexto y valores institucionales) al **formato** de salida: la matriz axiológica real tiene una fila por valor-enfoque con instrumento propio, no el párrafo único que genera el prompt hoy.
- **HU-43**, **HU-44**, **HU-45** son mejoras de UX/wizard con evidencia directa en los archivos fuente (enlace real de recurso previo en Aula Invertida, pedido explícito de ejemplos de apoyo, límite de competencias declarado en `Lineamientos.docx`).
- **HU-46** y **HU-47** completan el perfil institucional (HU-31) y la exportación (HU-23) con los campos y el encabezado de control documentario que la plantilla oficial RSE realmente usa.

## Plantillas institucionales personalizables (HU-48 a HU-50)

`Unidad didáctica(3).docx` y `Sesión de Aprendizaje(1).docx` son la versión **en blanco (silueta)** del mismo formato RSE que ya usan `Unidad ejemplo.docx`/`Sesión de Aprendizaje ejm.docx` llenos — confirmando que la estructura hoy hardcodeada en `src/prompts/*.md` y `StructureValidator` es, en realidad, la plantilla de una institución particular, no un estándar universal del sistema. HU-48/49/50 convierten esa estructura fija en algo que el propio docente puede subir y reemplazar cuando quiera, sin tocar código:

- **HU-48** sube el `.docx` en blanco y lo convierte en un esquema estructurado (tablas, columnas, celdas de instrucción vs. celdas de dato).
- **HU-49** usa ese esquema para que la IA genere contenido con la estructura exacta de la plantilla activa, en vez de la estructura fija actual.
- **HU-50** va un paso más allá: exporta rellenando el `.docx` original subido (no un documento reconstruido desde cero), preservando diseño, logos y encabezado de control documentario tal como los subió el docente — resolviendo de paso HU-47 para cualquier institución que suba su propia plantilla.

Se implementan en ese orden (HU-48 → HU-49 → HU-50) porque cada una depende del esquema que produce la anterior.

## Hallazgos de `docs/REGLAS_DE_NEGOCIO.md` (HU-35 a HU-38)

Al documentar las reglas de negocio verificándolas contra el código (no contra otra documentación), aparecieron 3 discrepancias reales no detectadas antes:

- **HU-35:** el backend une competencias múltiples con `", "` pero el generador espera separarlas por `"\n"` — con 2+ competencias, el prompt no aplica la instrucción reforzada que debería.
- **HU-36:** los "valores institucionales" del generador están hardcodeados a un colegio católico específico (incluye "Encuentro personal con Jesucristo", "Caridad"), no son los valores genéricos del CNEB — el sistema no es neutral institucionalmente hoy. Se relaciona directamente con HU-31/HU-32.
- **HU-37 y HU-38:** dos huecos en gamificación — dos insignias inalcanzables en la app activa (HU-37, bug real) y una regla de puntos documentada pero nunca implementada (HU-38, más una decisión de producto que un bug).

## Contexto institucional (HU-31, HU-32) y escalabilidad (HU-33, HU-34)

Dos planteamientos que surgieron al revisar el sistema en uso real:

- **Contexto institucional:** hoy la generación solo usa datos curriculares (área, grado, competencias, temas) — nada de la realidad del colegio del docente. HU-31 agrega un perfil institucional persistente (nombre, visión, contexto); HU-32 lo inyecta en el prompt para que la Situación Significativa y los ejemplos generados sean pertinentes al colegio real, no genéricos. HU-32 depende de HU-31.
- **Escalabilidad:** se verificó en vivo que una generación real tarda 149 segundos con la conexión HTTP bloqueada todo ese tiempo (`asyncio.to_thread`). HU-33 lo convierte en un job asíncrono (202 + polling) para que no se pierda el trabajo si se corta la conexión y para no agotar el threadpool con varios docentes generando a la vez. HU-34 es independiente: un límite de concurrencia sobre las llamadas a Bedrock para evitar throttling en cascada. Ambas se relacionan con HU-27 (PostgreSQL), necesaria si se llega a escalar a múltiples workers.

## Historias derivadas de `docs/FLUJO_APLICATIVO(2).md`

Al contrastar `docs/FLUJO_APLICATIVO(2).md` contra el código, se confirmaron varias reglas de negocio ya implementadas (filtro de competencias por área, producto final gobernando la rúbrica, metodología cambiando la secuencia, contenido suelto encapsulado automáticamente en tablas). Las siguientes describen reglas que el documento declara pero que **hoy no existen en el código** — quedaron como HU-22 (ya existía), HU-28, HU-29 y HU-30 de esta lista. La afirmación de esa misma sección 6 sobre "insignias"/extensibilidad general (§8) no generó historias por ser declaraciones de diseño no verificables como comportamiento específico.
