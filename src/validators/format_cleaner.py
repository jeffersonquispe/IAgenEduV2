# src/validators/format_cleaner.py
"""
Limpieza final de formato para contenido generado.
Consolida la lógica que estaba dispersa en bedrock_services.py y app.py.
"""
import logging
from ..utils.table_utils import pipeline_limpieza

logger = logging.getLogger(__name__)


class FormatCleaner:
    """
    Ejecuta el pipeline de limpieza de formato sobre contenido generado.
    Actúa como la última capa antes de presentar al usuario o exportar.
    """

    def limpiar(self, contenido: str) -> str:
        """
        Ejecuta el pipeline completo de limpieza.

        Pasos:
        1. Limpiar HTML residual
        2. Asegurar tablas existan
        3. Validar orden de columnas
        4. Forzar contenido suelto dentro de tablas
        """
        if not contenido:
            return contenido

        try:
            resultado = pipeline_limpieza(contenido)
            logger.info(
                f"[FormatCleaner] Limpieza completada. "
                f"Longitud antes: {len(contenido)}, después: {len(resultado)}"
            )
            return resultado
        except Exception as e:
            logger.error(f"[FormatCleaner] Error en limpieza: {e}")
            # Si falla la limpieza, devolver el contenido original
            return contenido
