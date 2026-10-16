# src/agents/coordinator.py
"""
Orquestador de Agentes: coordina el pipeline Generador → Validador → Formateador.
Devuelve (contenido: str, métricas: PipelineMetrics) para cada generación.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .generator_agent import GeneratorAgent
from .validator_agent import ValidatorAgent
from .formatter_agent import FormatterAgent
from ..core.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Métricas de una ejecución del pipeline."""
    tipo: str = ""                    # 'unidad' | 'sesion'
    area_curricular: str = ""
    grado: str = ""
    metodologia: str = ""
    puntaje_validacion: int = 0       # 0–100
    errores_criticos: int = 0
    errores_advertencia: int = 0
    correcciones_aplicadas: int = 0
    tokens_aprox: int = 0
    duracion_ms: int = 0
    llm_model: str = BedrockClient.CLAUDE_SONNET
    # HU-30: detalle de lo que sigue fallando tras la corrección, para mostrarlo
    # al docente: [{"tipo", "categoria", "mensaje", "seccion"}]
    detalle_validacion: list = field(default_factory=list)

    def aplicar_reporte(self, reporte) -> None:
        """Copia el estado de un ValidationReport a las métricas. Se llama tras
        CADA validación (inicial y posteriores a una corrección) para que las
        métricas reflejen el estado final del contenido, no el previo."""
        self.puntaje_validacion = reporte.puntaje
        self.errores_criticos = sum(1 for e in reporte.errores if e.tipo == "CRITICO")
        self.errores_advertencia = sum(1 for e in reporte.errores if e.tipo == "ADVERTENCIA")
        self.detalle_validacion = [
            {"tipo": e.tipo, "categoria": e.categoria, "mensaje": e.mensaje, "seccion": e.seccion}
            for e in reporte.errores if e.tipo in ("CRITICO", "ADVERTENCIA")
        ]

    def resumen_validacion(self) -> dict:
        """Forma que viaja al cliente y se guarda en Document.content['validacion']."""
        return {
            "es_valido": self.errores_criticos == 0,
            "puntaje_validacion": self.puntaje_validacion,
            "errores_criticos": self.errores_criticos,
            "errores_advertencia": self.errores_advertencia,
            "detalle": self.detalle_validacion,
        }


class AgentCoordinator:
    """
    Orquesta los tres agentes especialistas:
    1. GeneratorAgent: genera el contenido educativo con RAG
    2. ValidatorAgent: valida estructura y calidad pedagógica
    3. FormatterAgent: limpia y normaliza el formato final

    Devuelve siempre (contenido: str, métricas: PipelineMetrics).
    """

    def __init__(self, usar_validacion_llm: bool = True):
        self.generator = GeneratorAgent()
        self.validator = ValidatorAgent(usar_validacion_llm=usar_validacion_llm)
        self.formatter = FormatterAgent()
        self.max_correcciones = 1

    def validar_y_formatear_unidad(
        self, contenido: str, area_curricular: str, grado, num_sesiones: Optional[int] = None,
        plantilla_esquema: Optional[dict] = None,
    ) -> Tuple[str, PipelineMetrics]:
        """
        Valida, corrige si es necesario, y formatea una unidad didáctica.
        Extrae los Pasos 2-4 del pipeline (usado por streaming y por generar_unidad_didactica).

        `num_sesiones` habilita la verificación HU-39 (criterios de evaluación
        alineados 1:1 con la cantidad de sesiones solicitada).
        """
        metricas = PipelineMetrics(tipo="unidad", area_curricular=area_curricular, grado=str(grado))

        # Paso 2: Validar
        reporte = self.validator.validar_unidad(
            contenido=contenido,
            area_curricular=area_curricular,
            grado=str(grado),
            num_sesiones=num_sesiones,
            plantilla_esquema=plantilla_esquema,
        )
        metricas.aplicar_reporte(reporte)

        # Paso 3: Corregir si hay errores críticos
        if reporte.tiene_errores_criticos:
            logger.warning("[Coordinator] Errores críticos detectados, corrigiendo...")
            for intento in range(self.max_correcciones):
                errores_para_corregir = [
                    {"tipo": e.tipo, "mensaje": e.mensaje}
                    for e in reporte.errores if e.tipo == "CRITICO"
                ]
                contenido = self.generator.corregir(contenido, errores_para_corregir)
                metricas.correcciones_aplicadas += 1

                reporte = self.validator.validar_unidad(
                    contenido=contenido, area_curricular=area_curricular, grado=str(grado),
                    num_sesiones=num_sesiones, plantilla_esquema=plantilla_esquema,
                )
                metricas.aplicar_reporte(reporte)

                if not reporte.tiene_errores_criticos:
                    logger.info(f"[Coordinator] Corrección exitosa en intento {intento + 1}")
                    break

        # Paso 4: Formatear
        contenido_final = self.formatter.formatear(contenido)
        metricas.tokens_aprox = len(contenido_final) // 4

        return contenido_final, metricas

    def generar_unidad_didactica(
        self,
        area_curricular: str,
        grado,
        competencia_referencia: str = None,
        temas: str = None,
        num_sesiones: int = 6,
        producto_final: str = None,
    ) -> Tuple[str, PipelineMetrics]:
        """
        Genera una unidad didáctica con el pipeline completo.
        Returns: (contenido_final, métricas)
        """
        t0 = time.monotonic()

        logger.info(
            f"[Coordinator] Iniciando pipeline: unidad didáctica "
            f"{area_curricular} {grado}° ({num_sesiones} sesiones)"
        )

        # Paso 1: Generar
        contenido = self.generator.generar_unidad_didactica(
            area_curricular=area_curricular,
            grado=grado,
            competencia_referencia=competencia_referencia,
            temas=temas,
            num_sesiones=num_sesiones,
            producto_final=producto_final,
        )

        # Pasos 2-4: Validar, corregir, formatear
        contenido_final, metricas = self.validar_y_formatear_unidad(
            contenido=contenido,
            area_curricular=area_curricular,
            grado=grado,
            num_sesiones=num_sesiones,
        )

        metricas.duracion_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            f"[Coordinator] Pipeline completo. "
            f"Validación: {metricas.puntaje_validacion}/100, "
            f"Duración: {metricas.duracion_ms}ms"
        )
        return contenido_final, metricas

    def validar_y_formatear_sesion(
        self, contenido: str, grado: str, metodologia: str = None,
        plantilla_esquema: Optional[dict] = None,
    ) -> Tuple[str, PipelineMetrics]:
        """
        Valida, corrige si es necesario, y formatea una sesión de aprendizaje.
        Extrae los Pasos 2-4 del pipeline (usado por streaming y por generar_sesion_aprendizaje).
        """
        metricas = PipelineMetrics(tipo="sesion", grado=grado, metodologia=metodologia or "")

        reporte = self.validator.validar_sesion(contenido, plantilla_esquema=plantilla_esquema)
        metricas.aplicar_reporte(reporte)

        if reporte.tiene_errores_criticos:
            logger.warning("[Coordinator] Sesión: corrigiendo errores críticos...")
            errores = [{"tipo": e.tipo, "mensaje": e.mensaje}
                       for e in reporte.errores if e.tipo == "CRITICO"]
            contenido = self.generator.corregir(contenido, errores)
            metricas.correcciones_aplicadas += 1

            # HU-30: re-validar tras corregir, igual que la Unidad; si no, las
            # métricas conservarían los errores previos a la corrección y se
            # bloquearía la exportación de un documento ya arreglado.
            reporte = self.validator.validar_sesion(contenido, plantilla_esquema=plantilla_esquema)
            metricas.aplicar_reporte(reporte)

        contenido_final = self.formatter.formatear(contenido)
        metricas.tokens_aprox = len(contenido_final) // 4

        return contenido_final, metricas

    def generar_sesion_aprendizaje(
        self,
        titulo_unidad: str,
        titulo_sesion: str,
        nivel: str,
        grado: str,
        seccion: str,
        duracion: str,
        competencias_unidad: str = None,
        tema: str = None,
        metodologia: str = None,
    ) -> Tuple[str, PipelineMetrics]:
        """
        Genera una sesión de aprendizaje con el pipeline completo.
        Returns: (contenido_final, métricas)
        """
        t0 = time.monotonic()

        logger.info(f"[Coordinator] Iniciando pipeline: sesión '{titulo_sesion}'")

        contenido = self.generator.generar_sesion_aprendizaje(
            titulo_unidad=titulo_unidad,
            titulo_sesion=titulo_sesion,
            nivel=nivel,
            grado=grado,
            seccion=seccion,
            duracion=duracion,
            competencias_unidad=competencias_unidad,
            tema=tema,
            metodologia=metodologia,
        )

        # Pasos 2-4: Validar, corregir, formatear
        contenido_final, metricas = self.validar_y_formatear_sesion(
            contenido=contenido,
            grado=grado,
            metodologia=metodologia,
        )

        metricas.duracion_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            f"[Coordinator] Sesión completa. "
            f"Validación: {metricas.puntaje_validacion}/100, "
            f"Duración: {metricas.duracion_ms}ms"
        )
        return contenido_final, metricas

    def mejorar_documento(
        self,
        texto_documento: str,
        instruccion_usuario: str,
        tipo_documento: str = "documento",
    ) -> str:
        """Mejora un documento existente. Devuelve solo el string (sin métricas)."""
        logger.info(f"[Coordinator] Mejorando {tipo_documento}")
        contenido = self.generator.mejorar_documento(
            texto_documento=texto_documento,
            instruccion_usuario=instruccion_usuario,
            tipo_documento=tipo_documento,
        )
        return self.formatter.formatear(contenido)


# Singleton
_default_coordinator: Optional[AgentCoordinator] = None


def get_coordinator(usar_validacion_llm: bool = True) -> AgentCoordinator:
    """Obtiene la instancia singleton del AgentCoordinator."""
    global _default_coordinator
    if _default_coordinator is None:
        _default_coordinator = AgentCoordinator(usar_validacion_llm=usar_validacion_llm)
    return _default_coordinator
