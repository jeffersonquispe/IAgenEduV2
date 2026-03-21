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
from typing import Optional, Iterator
from botocore.exceptions import NoCredentialsError, ClientError

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
    CLAUDE_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"

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
        top_p: float = 0.9,
        min_longitud_respuesta: int = 50,
    ) -> str:
        """
        Invoca un modelo con reintentos y validación.

        Args:
            prompt: Texto del prompt
            modelo: ID del modelo (default: Claude Sonnet)
            max_tokens: Máximo de tokens en la respuesta
            temperature: Temperatura de generación
            top_p: Top-p sampling
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
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "top_p": top_p,
                })

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
            top_p=0.9,
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

        try:
            if aws_access_key and aws_secret_key:
                kwargs = {
                    'service_name': 'bedrock-runtime',
                    'region_name': self._region,
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key,
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

            return session.client('bedrock-runtime', region_name=self._region)

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
