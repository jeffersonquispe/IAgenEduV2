# src/agents/validator_agent.py
"""
Agente Validador: verifica la calidad estructural y pedagógica del contenido.
Combina validación programática (rápida) con validación LLM (profunda).
"""
import logging
from typing import Optional

from ..validators.structure_validator import StructureValidator, ValidationReport
from ..validators.content_validator import ContentValidator

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """
    Orquesta las validaciones estructurales y de contenido.
    Decide si el contenido necesita corrección.
    """

    def __init__(self, usar_validacion_llm: bool = True):
        self.structure_validator = StructureValidator()
        self.content_validator = ContentValidator() if usar_validacion_llm else None
        self.usar_validacion_llm = usar_validacion_llm

    def validar_unidad(
        self,
        contenido: str,
        area_curricular: str = "",
        grado: str = "",
    ) -> ValidationReport:
        """
        Valida una unidad didáctica generada.

        Paso 1: Validación estructural (rápida, programática)
        Paso 2: Si pasa estructura, validación de contenido (LLM, más lenta)

        Returns:
            ValidationReport con todos los errores encontrados
        """
        # Paso 1: Validación estructural
        reporte = self.structure_validator.validar_unidad_didactica(contenido)

        # Si hay errores críticos de estructura, no gastar en validación LLM
        if reporte.tiene_errores_criticos:
            logger.warning(
                f"[Validator] Unidad falló validación estructural: "
                f"{len(reporte.errores)} errores"
            )
            return reporte

        # Paso 2: Validación de contenido con LLM (opcional)
        if self.usar_validacion_llm and self.content_validator:
            try:
                resultado_llm = self.content_validator.validar(
                    contenido=contenido,
                    tipo_documento="unidad didáctica",
                    area_curricular=area_curricular,
                    grado=str(grado),
                    secciones_requeridas=", ".join(
                        StructureValidator.SECCIONES_UNIDAD
                    ),
                )

                # Convertir errores LLM al formato ValidationReport
                for error in resultado_llm.get("errores", []):
                    from validators.structure_validator import ValidationError
                    reporte.errores.append(ValidationError(
                        tipo=error.get("tipo", "ADVERTENCIA"),
                        categoria=error.get("criterio", "CONTENIDO"),
                        mensaje=error.get("descripcion", str(error)),
                    ))

                logger.info(
                    f"[Validator] Validación LLM: puntaje={resultado_llm.get('puntaje', '?')}"
                )

            except Exception as e:
                logger.warning(f"[Validator] Error en validación LLM: {e}")

        logger.info(f"[Validator] Resultado final: {reporte.resumen()}")
        return reporte

    def validar_sesion(
        self,
        contenido: str,
        area_curricular: str = "",
        grado: str = "",
    ) -> ValidationReport:
        """Valida una sesión de aprendizaje generada."""
        reporte = self.structure_validator.validar_sesion_aprendizaje(contenido)

        if reporte.tiene_errores_criticos:
            logger.warning(
                f"[Validator] Sesión falló validación estructural: "
                f"{len(reporte.errores)} errores"
            )
            return reporte

        if self.usar_validacion_llm and self.content_validator:
            try:
                resultado_llm = self.content_validator.validar(
                    contenido=contenido,
                    tipo_documento="sesión de aprendizaje",
                    area_curricular=area_curricular,
                    grado=str(grado),
                    secciones_requeridas=", ".join(
                        StructureValidator.SECCIONES_SESION
                    ),
                )

                for error in resultado_llm.get("errores", []):
                    from validators.structure_validator import ValidationError
                    reporte.errores.append(ValidationError(
                        tipo=error.get("tipo", "ADVERTENCIA"),
                        categoria=error.get("criterio", "CONTENIDO"),
                        mensaje=error.get("descripcion", str(error)),
                    ))

            except Exception as e:
                logger.warning(f"[Validator] Error en validación LLM sesión: {e}")

        logger.info(f"[Validator] Sesión resultado: {reporte.resumen()}")
        return reporte
