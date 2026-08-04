# HU-34: Límite de concurrencia para llamadas a Bedrock

**Épica:** Infraestructura / Escalabilidad | **Prioridad:** Media | **Esfuerzo:** S

**Como** administrador del sistema, **quiero** limitar cuántas llamadas a Bedrock se ejecutan al mismo tiempo, **para** que una ráfaga de docentes generando simultáneamente no dispare *throttling* en cascada y arruine la experiencia de todos.

## Contexto

`BedrockClient.invocar()` (`src/core/bedrock_client.py`) ya maneja `ThrottlingException` con backoff exponencial por request individual, pero no existe ningún límite compartido entre requests concurrentes — si 10 docentes generan a la vez, se disparan 10+ llamadas simultáneas a Bedrock (cada una con su propio pipeline de Generator → Validator LLM → posible corrección), sin ningún control central. Bajo AWS, esto puede agotar la cuota de *transactions per second* del modelo y hacer que **todos** empiecen a recibir `ThrottlingException` a la vez.

## Criterios de aceptación

- Un semáforo compartido (`asyncio.Semaphore` o equivalente) limita el número de llamadas a Bedrock en vuelo al mismo tiempo, con un valor configurable (variable de entorno, p. ej. `BEDROCK_MAX_CONCURRENCY`).
- Las llamadas que exceden el límite esperan en cola en vez de dispararse todas a la vez contra AWS.
- El límite aplica tanto al camino estándar (`GenerationService.crear_unidad`/`crear_sesion`) como al de streaming (`generar_unidad_stream_events`) y a las llamadas del `ValidatorAgent` (LLM-as-judge) — cualquier punto que invoque `BedrockClient`.
- El valor por defecto es conservador (documentar el razonamiento: cuota real de la cuenta AWS / modelo usado) para no requerir tuning manual antes del primer despliegue.

## Notas de implementación

- Esta historia es independiente de **HU-33**: se puede implementar sola, sin esperar a que la generación pase a ser un job asíncrono. Si ambas se implementan, el semáforo debe vivir en el proceso que ejecuta el trabajo en background, no en el route handler.
- El singleton `get_bedrock_client()` (`src/core/bedrock_client.py`) es un buen lugar natural para colgar el semáforo, ya que todas las llamadas pasan por ahí.

**Archivos relevantes:** `src/core/bedrock_client.py`

**Relaciona con:** **HU-33**
