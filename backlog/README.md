# Backlog — IA-GEN-EDU

Historias de usuario **pendientes de implementar**, derivadas de limitaciones conocidas del proyecto (ver `docs/DETALLES_TECNICOS.md` §15 y las notas finales de `USER_STORIES.md`), de una revisión del código activo (`src/api/`, `frontend/`), de contrastar `docs/FLUJO_APLICATIVO(2).md` (documento funcional/reglas de negocio) contra lo que el código realmente hace hoy, y de `docs/REGLAS_DE_NEGOCIO.md` (reglas de negocio verificadas directamente contra el código). Continúan la numeración de `USER_STORIES.md` (que documenta lo ya implementado).

Cada historia vive en su propio archivo para poder moverse a un tablero (Jira/Trello/GitHub Projects) sin reformatear. Formato: narrativa `Como/quiero/para`, criterios de aceptación, prioridad, esfuerzo estimado y archivos relevantes.

## Índice

| # | Historia | Épica | Prioridad | Esfuerzo |
|---|---|---|---|---|
| [HU-19](HU-19-recuperar-contrasena.md) | Recuperar contraseña olvidada | Autenticación | Alta | M |
| [HU-20](HU-20-verificacion-email.md) | Verificación de correo al registrarse | Autenticación | Media | M |
| [HU-21](HU-21-secret-key-obligatoria.md) | `SECRET_KEY` obligatoria por entorno | Seguridad | Alta | S |
| [HU-22](HU-22-selector-unidad-padre.md) | Selector de unidad padre al crear una Sesión | Generación | Alta | S |
| [HU-23](HU-23-exportacion-docx-institucional.md) | Exportación DOCX con estilos institucionales | Exportación | Media | M |
| [HU-24](HU-24-busqueda-filtrado-documentos.md) | Búsqueda y filtrado de documentos | Historial | Media | S |
| [HU-25](HU-25-tests-automatizados.md) | Suite de tests automatizados | Calidad técnica | Alta | L |
| [HU-26](HU-26-actualizar-requirements.md) | `requirements.txt` fiel a las dependencias reales | Calidad técnica | Alta | S |
| [HU-27](HU-27-migracion-postgresql.md) | Migración de SQLite a PostgreSQL | Infraestructura | Baja | L |
| [HU-28](HU-28-campo-institucion-educativa.md) | ~~Campo "Institución Educativa" en la generación~~ → ver HU-31/HU-32 | Generación | — | — |
| [HU-29](HU-29-validar-temas-no-repetidos.md) | Validar que no haya temas repetidos entre sesiones | Calidad del contenido | Media | M |
| [HU-30](HU-30-gating-exportacion-por-validacion.md) | Bloquear exportación si el documento no pasa validación | Calidad / Exportación | Media | M |
| [HU-31](HU-31-perfil-institucional.md) | Perfil institucional del docente (nombre, visión, contexto) | Generación | Media | M |
| [HU-32](HU-32-contexto-institucional-en-generacion.md) | Inyectar el contexto institucional en el pipeline de generación | Generación | Media | S-M |
| [HU-33](HU-33-generacion-como-job-asincrono.md) | Generación de documentos como job asíncrono | Infraestructura | Media | L |
| [HU-34](HU-34-limite-concurrencia-bedrock.md) | Límite de concurrencia para llamadas a Bedrock | Infraestructura | Media | S |
| [HU-35](HU-35-fix-join-competencias-multiples.md) | Corregir el ensamblado de competencias múltiples en el prompt | Calidad del contenido | Media | S |
| [HU-36](HU-36-valores-institucionales-configurables.md) | Hacer configurables los valores y enfoques transversales institucionales | Generación | Alta | S-M |
| [HU-37](HU-37-fix-registro-areas-grados-usados.md) | Registrar áreas y grados usados en la app activa (insignias rotas) | Gamificación | Media | S |
| [HU-38](HU-38-definir-puntos-por-accion.md) | Definir e implementar (o retirar de la documentación) los puntos por acción directa | Gamificación | Baja | S |

Prioridad y esfuerzo son una primera estimación para ordenar el trabajo; ajústalos según el alcance real de la tesis.

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
