# src/utils/retry.py
"""
Utilidad de reintentos con backoff exponencial para llamadas a AWS Bedrock.
"""
import time
import logging
import random
from functools import wraps

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Error cuando se agotan todos los reintentos."""
    def __init__(self, mensaje: str, ultimo_error: Exception = None):
        self.ultimo_error = ultimo_error
        super().__init__(mensaje)


def con_reintentos(
    max_intentos: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    excepciones_reintentables: tuple = None,
):
    """
    Decorador que reintenta una función con backoff exponencial + jitter.

    Args:
        max_intentos: Número máximo de intentos (default 3)
        base_delay: Delay base en segundos (default 1.0)
        max_delay: Delay máximo en segundos (default 30.0)
        excepciones_reintentables: Tuple de excepciones que disparan reintento.
            Si es None, reintenta en cualquier excepción.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ultimo_error = None
            for intento in range(1, max_intentos + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    ultimo_error = e
                    # Verificar si la excepción es reintentable
                    if excepciones_reintentables and not isinstance(e, excepciones_reintentables):
                        raise

                    if intento == max_intentos:
                        logger.error(
                            f"[Retry] {func.__name__} falló después de {max_intentos} intentos. "
                            f"Último error: {e}"
                        )
                        raise RetryError(
                            f"Falló después de {max_intentos} intentos: {e}",
                            ultimo_error=e,
                        ) from e

                    # Backoff exponencial con jitter
                    delay = min(base_delay * (2 ** (intento - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.5)
                    total_delay = delay + jitter

                    logger.warning(
                        f"[Retry] {func.__name__} intento {intento}/{max_intentos} falló: {e}. "
                        f"Reintentando en {total_delay:.1f}s..."
                    )
                    time.sleep(total_delay)

        return wrapper
    return decorator


def reintentar_llamada(
    func,
    args=(),
    kwargs=None,
    max_intentos: int = 3,
    base_delay: float = 1.0,
    validar_resultado=None,
):
    """
    Reintenta una llamada con validación de resultado.

    Args:
        func: Función a llamar
        args: Argumentos posicionales
        kwargs: Argumentos con nombre
        max_intentos: Número máximo de intentos
        base_delay: Delay base en segundos
        validar_resultado: Función que recibe el resultado y devuelve True si es válido.
            Si devuelve False, se reintenta.

    Returns:
        El resultado de la función si pasa validación.
    """
    if kwargs is None:
        kwargs = {}

    ultimo_resultado = None
    ultimo_error = None

    for intento in range(1, max_intentos + 1):
        try:
            resultado = func(*args, **kwargs)

            # Si hay validación, verificar el resultado
            if validar_resultado:
                if validar_resultado(resultado):
                    return resultado
                else:
                    logger.warning(
                        f"[Retry] Intento {intento}/{max_intentos}: resultado no pasó validación"
                    )
                    ultimo_resultado = resultado
                    if intento < max_intentos:
                        delay = base_delay * (2 ** (intento - 1))
                        time.sleep(delay)
                    continue

            return resultado

        except Exception as e:
            ultimo_error = e
            if intento == max_intentos:
                raise
            delay = base_delay * (2 ** (intento - 1))
            logger.warning(
                f"[Retry] Intento {intento}/{max_intentos} falló: {e}. "
                f"Reintentando en {delay:.1f}s..."
            )
            time.sleep(delay)

    # Si llegamos aquí, devolver el último resultado (no pasó validación pero se agotaron intentos)
    if ultimo_resultado is not None:
        logger.warning("[Retry] Agotados reintentos; devolviendo último resultado sin validar.")
        return ultimo_resultado
    raise RetryError("Agotados reintentos sin resultado válido", ultimo_error)
