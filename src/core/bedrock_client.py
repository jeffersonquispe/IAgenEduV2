# src/core/bedrock_client.py
"""
Cliente centralizado para Amazon Bedrock con reintentos, logging y manejo de errores.
Reemplaza la creación directa de clientes boto3 en cada función.
"""
import boto3
import json
import logging
import os
import asyncio
import threading
from typing import Optional, Iterator
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)

# Cargar .env si existe
try:
    from dotenv import load_dotenv
    import pathlib
    env_path = pathlib.Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except (ImportError, Exception):
    pass


class RespuestaIncompleta(Exception):
    """La respuesta del modelo fue vacía o demasiado corta."""
    pass


# HU-34: límite de llamadas a Bedrock en vuelo a la vez. Todas las llamadas son
# síncronas y corren en hilos (el streaming en el threadpool de FastAPI,
# invocar_async con to_thread), así que el primitivo es threading, no asyncio.
# Default 4: conservador a propósito para no requerir tuning antes del primer
# despliegue — las cuotas on-demand de Claude en una cuenta AWS nueva suelen ser
# de pocas solicitudes por minuto, y cada generación completa encadena varias
# llamadas (generar + validar con LLM + posible corrección). Súbelo con
# BEDROCK_MAX_CONCURRENCY cuando conozcas la cuota real de tu cuenta/modelo.
DEFAULT_BEDROCK_MAX_CONCURRENCY = 4


def _leer_max_concurrencia() -> int:
    raw = (os.environ.get("BEDROCK_MAX_CONCURRENCY") or "").strip()
    if not raw:
        return DEFAULT_BEDROCK_MAX_CONCURRENCY
    try:
        valor = int(raw)
        if valor < 1:
            raise ValueError
        return valor
    except ValueError:
        logger.warning(
            f"[Bedrock] BEDROCK_MAX_CONCURRENCY={raw!r} no es un entero >= 1; "
            f"usando {DEFAULT_BEDROCK_MAX_CONCURRENCY}"
        )
        return DEFAULT_BEDROCK_MAX_CONCURRENCY


class LimiteConcurrencia:
    """Semáforo con cola: las llamadas que exceden el límite esperan su turno
    en vez de dispararse todas a la vez contra AWS."""

    def __init__(self, maximo: int):
        self.maximo = maximo
        self._sem = threading.BoundedSemaphore(maximo)
        self._lock = threading.Lock()
        self._en_vuelo = 0
        self._esperando = 0

    @property
    def en_vuelo(self) -> int:
        return self._en_vuelo

    @property
    def esperando(self) -> int:
        return self._esperando

    def __enter__(self):
        if not self._sem.acquire(blocking=False):
            with self._lock:
                self._esperando += 1
                esperando = self._esperando
            logger.info(
                f"[Bedrock] Límite de concurrencia ({self.maximo}) alcanzado; "
                f"en cola: {esperando}"
            )
            try:
                self._sem.acquire()
            finally:
                with self._lock:
                    self._esperando -= 1
        with self._lock:
            self._en_vuelo += 1
        return self

    def __exit__(self, *exc):
        with self._lock:
            self._en_vuelo -= 1
        self._sem.release()
        return False


_limite: Optional[LimiteConcurrencia] = None
_limite_lock = threading.Lock()


def get_limite_concurrencia() -> LimiteConcurrencia:
    """Límite compartido por todo el proceso (lazy, para leer el entorno ya cargado)."""
    global _limite
    if _limite is None:
        with _limite_lock:
            if _limite is None:
                _limite = LimiteConcurrencia(_leer_max_concurrencia())
    return _limite


class BedrockClient:
    """
    Cliente unificado para invocar modelos en Amazon Bedrock.

    Centraliza:
    - Creación y reutilización del cliente boto3
    - Reintentos con backoff exponencial
    - Validación de respuestas
    - Logging estructurado
    """

    # Modelos disponibles
    CLAUDE_SONNET = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    # Modelo económico para la validación de contenido (LLM-as-judge). Configurable porque AWS
    # retira versiones: el anterior (claude-3-haiku-20240307) ya no existe y la validación fallaba
    # en silencio. Si cambias de modelo, comprueba que tu cuenta tenga acceso a él en Bedrock.
    CLAUDE_HAIKU = os.environ.get("BEDROCK_VALIDATION_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

    def __init__(self, max_reintentos: int = 3):
        self.max_reintentos = max_reintentos
        self._client = None
        self._region = (os.environ.get('AWS_REGION') or 'us-east-1').strip()

    @property
    def client(self):
        """Acceso lazy al cliente boto3 (se crea una sola vez)."""
        if self._client is None:
            self._client = self._crear_cliente()
        return self._client

    def invocar(
        self,
        prompt: str,
        modelo: str = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        min_longitud_respuesta: int = 50,
    ) -> str:
        """
        Invoca un modelo con reintentos y validación.

        Args:
            prompt: Texto del prompt
            modelo: ID del modelo (default: Claude Sonnet)
            max_tokens: Máximo de tokens en la respuesta
            temperature: Temperatura de generación
            min_longitud_respuesta: Longitud mínima aceptable (en chars)

        Returns:
            Texto de la respuesta del modelo

        Raises:
            RespuestaIncompleta: Si la respuesta no supera min_longitud_respuesta
            Exception: Si todos los reintentos fallan
        """
        if modelo is None:
            modelo = self.CLAUDE_SONNET

        ultimo_error = None

        for intento in range(1, self.max_reintentos + 1):
            try:
                # No enviar top_p junto con temperature: algunos modelos Claude en
                # Bedrock (incl. el configurado en BEDROCK_MODEL_ID) rechazan la
                # petición con ValidationException si se especifican ambos.
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                })

                # HU-34: el slot se ocupa solo durante la llamada (no durante el
                # backoff entre reintentos, para no retener cupo mientras se espera).
                with get_limite_concurrencia():
                    response = self.client.invoke_model(
                        body=body,
                        modelId=modelo,
                        accept='application/json',
                        contentType='application/json',
                    )
                    response_body = json.loads(response['body'].read())
                texto = response_body.get('content', [{}])[0].get('text', '')

                # Validar que la respuesta no esté vacía o truncada
                if not texto or len(texto) < min_longitud_respuesta:
                    raise RespuestaIncompleta(
                        f"Respuesta demasiado corta ({len(texto)} chars, "
                        f"mínimo {min_longitud_respuesta})"
                    )

                logger.info(
                    f"[Bedrock] Modelo={modelo}, tokens_respuesta≈{len(texto)//4}, "
                    f"intento={intento}/{self.max_reintentos}"
                )
                return texto

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                ultimo_error = e

                if error_code == 'ThrottlingException':
                    if intento < self.max_reintentos:
                        import time
                        delay = 2 ** intento
                        logger.warning(f"[Bedrock] Throttling, reintentando en {delay}s...")
                        time.sleep(delay)
                        continue
                elif error_code == 'ModelTimeoutException':
                    if intento < self.max_reintentos:
                        import time
                        logger.warning("[Bedrock] Timeout del modelo, reintentando...")
                        time.sleep(2)
                        continue
                raise

            except RespuestaIncompleta as e:
                ultimo_error = e
                if intento < self.max_reintentos:
                    logger.warning(f"[Bedrock] {e}, reintentando...")
                    continue
                raise

            except NoCredentialsError:
                raise Exception(self._mensaje_error_credenciales())

            except Exception as e:
                ultimo_error = e
                if intento < self.max_reintentos:
                    import time
                    logger.warning(f"[Bedrock] Error: {e}, reintentando en {2**intento}s...")
                    time.sleep(2 ** intento)
                    continue
                raise

        raise Exception(
            f"Todos los reintentos agotados. Último error: {ultimo_error}"
        )

    def invocar_validacion(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Invocación para validación con un modelo más rápido y barato (Haiku).
        Usa temperature baja para respuestas más determinísticas.
        """
        return self.invocar(
            prompt=prompt,
            modelo=self.CLAUDE_HAIKU,
            max_tokens=max_tokens,
            temperature=0.2,
            min_longitud_respuesta=10,
        )

    async def invocar_async(
        self,
        prompt: str,
        modelo: str = None,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """
        Versión async de invocar(). Envuelve la llamada bloqueante
        en asyncio.to_thread para no bloquear el event loop de FastAPI.
        """
        return await asyncio.to_thread(
            self.invocar,
            prompt=prompt,
            modelo=modelo or self.CLAUDE_SONNET,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def invocar_stream(self, prompt: str, modelo: str = None, max_tokens: int = 8000,
                       temperature: float = 0.7) -> Iterator[str]:
        """
        Streaming via invoke_model_with_response_stream de Bedrock.
        Hace yield de fragmentos de texto a medida que llegan del modelo.
        """
        if modelo is None:
            modelo = self.CLAUDE_SONNET

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        })

        try:
            # HU-34: el slot se mantiene mientras dura el stream (la solicitud
            # sigue en vuelo en AWS) y se libera en el `with` aunque el cliente
            # cierre el generador a mitad (GeneratorExit).
            with get_limite_concurrencia():
                response = self.client.invoke_model_with_response_stream(
                    body=body,
                    modelId=modelo,
                    accept="application/json",
                    contentType="application/json",
                )
                for event in response["body"]:
                    chunk = event.get("chunk")
                    if chunk:
                        data = json.loads(chunk["bytes"])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
        except Exception as e:
            logger.error(f"[Bedrock] Error en streaming: {e}")
            raise

    def _crear_cliente(self):
        """Crea el cliente boto3 para bedrock-runtime."""
        aws_access_key = (os.environ.get('AWS_ACCESS_KEY_ID') or '').strip()
        aws_secret_key = (os.environ.get('AWS_SECRET_ACCESS_KEY') or '').strip()
        aws_session_token = (os.environ.get('AWS_SESSION_TOKEN') or '').strip() or None
        aws_profile = (os.environ.get('AWS_PROFILE') or '').strip() or None

        config = Config(
            read_timeout=180,
            connect_timeout=10,
            retries={'max_attempts': 2}
        )

        try:
            if aws_access_key and aws_secret_key:
                kwargs = {
                    'service_name': 'bedrock-runtime',
                    'region_name': self._region,
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key,
                    'config': config,
                }
                if aws_session_token:
                    kwargs['aws_session_token'] = aws_session_token
                return boto3.client(**kwargs)

            if aws_profile:
                session = boto3.Session(profile_name=aws_profile)
            else:
                session = boto3.Session()

            creds = session.get_credentials()
            if not creds:
                raise Exception("No se encontraron credenciales de AWS")

            return session.client('bedrock-runtime', region_name=self._region, config=config)

        except NoCredentialsError:
            raise Exception(self._mensaje_error_credenciales())
        except Exception as e:
            raise Exception(
                f"Error creando cliente Bedrock: {e}\n\n"
                + self._mensaje_error_credenciales()
            )

    @staticmethod
    def _mensaje_error_credenciales() -> str:
        """Mensaje de error útil cuando faltan credenciales."""
        return (
            "❌ No se encontraron credenciales de AWS.\n\n"
            "Configura tus credenciales:\n"
            "1. Archivo .env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION\n"
            "2. Variables de entorno del sistema\n"
            "3. Perfil AWS: aws configure\n"
            "4. Docker: env_file en docker-compose.yml\n"
        )


# Singleton para reutilizar en toda la aplicación
_default_client: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """Obtiene la instancia singleton del BedrockClient."""
    global _default_client
    if _default_client is None:
        _default_client = BedrockClient()
    return _default_client
