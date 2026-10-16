# src/validators/content_validator.py
"""
Valida la calidad pedagógica del contenido generado usando un LLM ligero.
Complementa al StructureValidator con validación semántica.
"""
import json
import logging
from typing import Optional

from ..core.prompt_manager import get_prompt_manager
from ..core.bedrock_client import get_bedrock_client

logger = logging.getLogger(__name__)

# Cuánto del documento se le muestra al modelo y cuánto se le deja responder.
MAX_CARACTERES_VALIDACION = 40000
MAX_TOKENS_RESPUESTA = 2000


def _resultado_no_disponible(motivo: str) -> dict:
    """Resultado neutro cuando la revisión con IA no se pudo realizar. `revision_disponible=False`
    permite que quien lo use lo muestre al docente en vez de tomarlo por una aprobación real."""
    return {
        "calificacion_general": "APROBADO",
        "puntaje": 70,
        "errores": [],
        "sugerencias": [motivo],
        "revision_disponible": False,
    }


class ContentValidator:
    """
    Usa un modelo LLM (Haiku, rápido y barato) para evaluar la calidad
    pedagógica del contenido generado.
    """

    def __init__(self):
        self.bedrock = get_bedrock_client()
        self.prompt_manager = get_prompt_manager()

    def validar(
        self,
        contenido: str,
        tipo_documento: str = "unidad didáctica",
        area_curricular: str = "",
        grado: str = "",
        secciones_requeridas: str = "",
    ) -> dict:
        """
        Valida el contenido usando el LLM validador.

        Returns:
            dict con claves: calificacion_general, puntaje, errores, sugerencias
        """
        try:
            prompt = self.prompt_manager.cargar(
                "validacion",
                tipo_documento=tipo_documento,
                # Un límite bajo hacía que el modelo viera el documento "cortado" y lo reportara como
                # incompleto. Una Unidad ocupa ~8-30 mil caracteres: con este tope se ve entera.
                contenido=contenido[:MAX_CARACTERES_VALIDACION],
                area_curricular=area_curricular,
                grado=grado,
                secciones_requeridas=secciones_requeridas or "Ver documento",
            )

            # Con 800 tokens la respuesta de Haiku 4.5 se cortaba a mitad del JSON y no se podía leer.
            respuesta = self.bedrock.invocar_validacion(prompt, max_tokens=MAX_TOKENS_RESPUESTA)

            # Intentar parsear JSON de la respuesta
            return self._parsear_respuesta(respuesta)

        except Exception as e:
            logger.warning(f"[ContentValidator] Error en validación LLM: {e}")
            # Si falla la validación LLM, devolver un reporte neutro
            return _resultado_no_disponible(f"No se pudo realizar validación LLM: {e}")

    def _parsear_respuesta(self, respuesta: str) -> dict:
        """Intenta extraer el JSON del reporte de validación."""
        # Buscar bloque JSON en la respuesta
        json_match = None
        # Intentar extraer JSON entre ```json ... ```
        import re
        # El cierre ``` es opcional: si el modelo no lo escribe, se toma hasta el final.
        match = re.search(r'```json\s*(.*?)\s*(?:```|\Z)', respuesta, re.DOTALL)
        if match:
            json_match = match.group(1)
        else:
            # Intentar parsear toda la respuesta como JSON
            json_match = respuesta.strip()

        try:
            resultado = json.loads(json_match)
            # Validar estructura esperada
            return {
                "calificacion_general": resultado.get("calificacion_general", "APROBADO"),
                "puntaje": resultado.get("puntaje", 70),
                "errores": resultado.get("errores", []),
                "sugerencias": resultado.get("sugerencias", []),
                "revision_disponible": True,
            }
        except json.JSONDecodeError:
            logger.warning("[ContentValidator] No se pudo parsear JSON de validación")
            return _resultado_no_disponible("La respuesta del validador no fue JSON válido")
