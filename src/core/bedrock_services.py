# src/core/bedrock_services.py
"""
Bridge entre las rutas FastAPI y el pipeline de agentes.
Redirige las llamadas al AgentCoordinator (pipeline completo) y usa
legacy_generator como fallback si el pipeline falla.

Este módulo es intencionalmente delgado -- toda la lógica de generación
vive en src/agents/ y src/core/legacy_generator.py.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_USE_AGENT_PIPELINE = True


def generar_unidad_didactica(
    area_curricular: str,
    grado,
    competencia_referencia: Optional[str] = None,
    temas: Optional[str] = None,
    num_sesiones: int = 6,
    producto_final: Optional[str] = None,
) -> str:
    """Genera una unidad didáctica. Usa el pipeline de agentes con fallback legacy."""
    if _USE_AGENT_PIPELINE:
        try:
            from ..agents.coordinator import get_coordinator
            coordinator = get_coordinator(usar_validacion_llm=True)
            contenido, _ = coordinator.generar_unidad_didactica(  # ignora métricas aquí
                area_curricular=area_curricular,
                grado=grado,
                competencia_referencia=competencia_referencia,
                temas=temas,
                num_sesiones=num_sesiones,
                producto_final=producto_final,
            )
            if contenido and len(contenido) > 100:
                logger.info("[bedrock_services] Unidad generada con pipeline de agentes")
                return contenido
            logger.warning("[bedrock_services] Pipeline devolvió resultado corto, usando fallback")
        except Exception as e:
            logger.warning(f"[bedrock_services] Pipeline falló, usando fallback: {e}")

    from .legacy_generator import generar_unidad_didactica_fallback
    return generar_unidad_didactica_fallback(
        area_curricular=area_curricular,
        grado=grado,
        competencia_referencia=competencia_referencia,
        temas=temas,
        num_sesiones=num_sesiones,
        producto_final=producto_final,
    )


def generar_sesion_aprendizaje(
    titulo_unidad: str,
    titulo_sesion: str,
    nivel: str,
    grado: str,
    seccion: str,
    duracion: str,
    competencias_unidad: Optional[str] = None,
    tema: Optional[str] = None,
    metodologia: Optional[str] = None,
) -> str:
    """Genera una sesión de aprendizaje. Usa el pipeline de agentes con fallback legacy."""
    if _USE_AGENT_PIPELINE:
        try:
            from ..agents.coordinator import get_coordinator
            coordinator = get_coordinator(usar_validacion_llm=True)
            contenido, _ = coordinator.generar_sesion_aprendizaje(
                titulo_unidad=titulo_unidad,
                titulo_sesion=titulo_sesion,
                nivel=nivel,
                grado=str(grado),
                seccion=seccion,
                duracion=duracion,
                competencias_unidad=competencias_unidad,
                tema=tema,
                metodologia=metodologia,
            )
            if contenido and len(contenido) > 100:
                logger.info("[bedrock_services] Sesión generada con pipeline de agentes")
                return contenido
            logger.warning("[bedrock_services] Pipeline sesión devolvió resultado corto, usando fallback")
        except Exception as e:
            logger.warning(f"[bedrock_services] Pipeline sesión falló, usando fallback: {e}")

    from .legacy_generator import generar_sesion_aprendizaje_fallback
    return generar_sesion_aprendizaje_fallback(
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


def mejorar_documento_con_instruccion(
    texto_documento: str,
    instruccion_usuario: str,
    tipo_documento: str = "documento",
) -> str:
    """Mejora un documento existente según la instrucción del usuario."""
    if _USE_AGENT_PIPELINE:
        try:
            from ..agents.coordinator import get_coordinator
            coordinator = get_coordinator(usar_validacion_llm=False)
            resultado = coordinator.mejorar_documento(
                texto_documento=texto_documento,
                instruccion_usuario=instruccion_usuario,
                tipo_documento=tipo_documento,
            )
            if resultado and len(resultado) > 20:
                return resultado
        except Exception as e:
            logger.warning(f"[bedrock_services] Pipeline mejora falló, usando fallback: {e}")

    # Fallback directo
    from .bedrock_client import get_bedrock_client
    client = get_bedrock_client()
    prompt = (
        f"Eres un editor experto en documentos educativos del MINEDU Perú.\n\n"
        f"DOCUMENTO:\n\"\"\"\n{texto_documento}\n\"\"\"\n\n"
        f"INSTRUCCIÓN: {instruccion_usuario}\n\n"
        f"Aplica exactamente lo que pide el usuario. "
        f"Conserva la estructura de tablas Markdown. "
        f"Devuelve SOLO el documento modificado, sin texto antes ni después."
    )
    nuevo_texto = client.invocar(prompt, max_tokens=8000, temperature=0.4).strip()
    return nuevo_texto if nuevo_texto else texto_documento