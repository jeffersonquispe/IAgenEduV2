# src/agents/formatter_agent.py
"""
Agente Formateador: asegura que el contenido final tenga el formato correcto.
Es la última etapa del pipeline antes de devolver al usuario.
"""
import logging

from ..validators.format_cleaner import FormatCleaner

logger = logging.getLogger(__name__)


class FormatterAgent:
    """
    Aplica limpieza y normalización de formato al contenido generado.
    Consolida toda la lógica de limpieza HTML, validación de tablas,
    y corrección de columnas que antes estaba dispersa.
    """

    def __init__(self):
        self.cleaner = FormatCleaner()

    def formatear(self, contenido: str) -> str:
        """
        Formatea el contenido generado para presentación final.

        Pipeline:
        1. Limpiar HTML residual
        2. Asegurar estructura de tablas
        3. Validar y corregir orden de columnas
        4. Forzar contenido suelto dentro de tablas

        Returns:
            Contenido limpio y formateado
        """
        if not contenido:
            return contenido

        resultado = self.cleaner.limpiar(contenido)

        logger.info(
            f"[Formatter] Contenido formateado. "
            f"Entrada: {len(contenido)} chars → Salida: {len(resultado)} chars"
        )
        return resultado
