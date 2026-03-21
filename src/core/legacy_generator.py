# src/core/legacy_generator.py
"""
Generador legacy: contiene los prompts directos a Bedrock usados como fallback
cuando el pipeline de agentes (coordinator) no está disponible.

Este módulo NO debe ser importado directamente por las rutas API.
bedrock_services.py lo usa internamente como último recurso.
"""
import json
import logging
import os
from typing import Optional

from .bedrock_client import get_bedrock_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes institucionales
# ---------------------------------------------------------------------------
VALORES_PERMITIDOS = [
    "Participación", "Respeto", "Solidaridad", "Conciencia crítica",
    "Compromiso ambiental", "Apertura y acogida", "Gratitud y donación",
    "Compasión y misericordia", "Cuidado y promoción de la vida",
    "Discernimiento y compromiso", "Encuentro personal con Jesucristo",
    "Caridad", "Experiencia comunitaria de la fe",
]

ENFOQUES_TRANSVERSALES_PERMITIDOS = [
    "Búsqueda de la excelencia: Superación personal.",
    "Enfoque ambiental: justicia y solidaridad.",
    "Enfoque de derecho: conciencia de derechos.",
    "Atención a la diversidad: respeto por las diferencias.",
    "Enfoque orientación al bien común: empatía y solidaridad.",
    "Enfoque de derecho: libertad y responsabilidad.",
    "Enfoque Ambiental: respeto a toda forma de vida, solidaridad planetaria y equidad intergeneracional.",
    "Enfoque intercultural: respeto a la identidad cultural y diálogo intercultural.",
]


def _cliente():
    return get_bedrock_client()


def generar_unidad_didactica_fallback(
    area_curricular: str,
    grado,
    competencia_referencia: Optional[str] = None,
    temas: Optional[str] = None,
    num_sesiones: int = 6,
    producto_final: Optional[str] = None,
) -> str:
    """
    Genera una unidad didáctica enviando el prompt directamente a Bedrock
    (sin pipeline de agentes). Usado cuando el coordinator falla.
    """
    valores_texto = ", ".join(VALORES_PERMITIDOS)
    enfoques_texto = "; ".join(ENFOQUES_TRANSVERSALES_PERMITIDOS)

    contexto_competencia = ""
    if competencia_referencia and competencia_referencia.strip():
        competencias_lista = [c.strip() for c in competencia_referencia.split("\n") if c.strip()]
        if len(competencias_lista) > 1:
            competencias_texto = "\n".join(f"- {c}" for c in competencias_lista)
            contexto_competencia = (
                f"\nCOMPETENCIAS OBLIGATORIAS (USAR SOLO ESTAS):\n{competencias_texto}\n"
                f"NO agregues otras competencias que no estén en la lista.\n"
            )
        else:
            contexto_competencia = (
                f"\nCOMPETENCIA OBLIGATORIA (USAR SOLO ESTA):\n{competencia_referencia}\n"
                f"NO uses ni agregues otras competencias.\n"
            )

    contexto_temas = ""
    if temas and temas.strip():
        contexto_temas = f"\nTEMAS ESPECÍFICOS:\n{temas}\n"

    contexto_producto = ""
    if producto_final and producto_final.strip():
        contexto_producto = (
            f"\nPRODUCTO FINAL DE UNIDAD: {producto_final}\n"
            f"La rúbrica DEBE evaluar dimensiones de este producto.\n"
        )

    prompt = f"""Actúa como especialista en diseño curricular (MINEDU Perú).
Genera una unidad didáctica completa para {area_curricular}, {grado}° de SECUNDARIA.

{contexto_competencia}
{contexto_temas}
{contexto_producto}

EXACTAMENTE {num_sesiones} sesiones de aprendizaje.

REGLAS:
- Responde SOLO con tablas Markdown: | ITEM | CONTENIDO |
- Primera tabla: TÍTULO DE LA UNIDAD
- Segunda tabla: SITUACIÓN SIGNIFICATIVA
- Tercera tabla: PROPÓSITOS DE APRENDIZAJE (competencia, capacidades, criterios, evidencia, instrumento)
- Cuarta tabla: EVIDENCIAS, INSTRUMENTOS, VALORES Y ENFOQUES TRANSVERSALES, SECUENCIA DE SESIONES
- Quinta tabla: COMPETENCIAS TRANSVERSALES (3 columnas: Competencia | Estándar | Instrumento)
- Sexta tabla: RÚBRICA ANALÍTICA (columnas: Criterio | C-Inicio | B-Proceso | A-Logrado | AD-Destacado)
- Valores permitidos: {valores_texto}
- Enfoques permitidos: {enfoques_texto}
- NO generes texto fuera de las tablas. NO uses viñetas. NO uses HTML.
"""
    logger.info(f"[Legacy] Generando unidad didáctica fallback: {area_curricular} {grado}°")
    return _cliente().invocar(prompt, max_tokens=8000, temperature=0.7)


def generar_sesion_aprendizaje_fallback(
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
    """
    Genera una sesión de aprendizaje enviando el prompt directamente a Bedrock.
    Usado cuando el coordinator falla.
    """
    instruccion_metodologia = ""
    if metodologia:
        m = metodologia.upper()
        if "ABP" in m:
            instruccion_metodologia = (
                "METODOLOGÍA ABP: Inicio = plantear problema real (sin explicar teoría). "
                "Desarrollo = análisis grupal → investigación → diseño de solución → validación. "
                "Cierre = socialización de resultados y metacognición."
            )
        elif "INVERTIDA" in m or "FLIPPED" in m:
            instruccion_metodologia = (
                "METODOLOGÍA AULA INVERTIDA: Inicio = verificar tarea previa (NO explicar contenido nuevo). "
                "Desarrollo = debate, análisis profundo, resolución colaborativa. "
                "Cierre = síntesis y metacognición."
            )
        else:  # ERCA por defecto
            instruccion_metodologia = (
                "METODOLOGÍA ERCA: Inicio = experiencia vivencial concreta. "
                "Desarrollo = reflexión sobre la experiencia → conceptualización → aplicación práctica. "
                "Cierre = metacognición y transferencia."
            )

    competencias_contexto = ""
    if competencias_unidad:
        competencias_contexto = f"\nCOMPETENCIAS DE LA UNIDAD (usar estas):\n{competencias_unidad}\n"

    prompt = f"""Actúa como especialista en diseño de sesiones de aprendizaje (MINEDU Perú).

DATOS DE LA SESIÓN:
- Unidad: {titulo_unidad}
- Sesión: {titulo_sesion}
- Nivel: {nivel} | Grado: {grado} | Sección: {seccion}
- Duración: {duracion}
{f'- Tema: {tema}' if tema else ''}
{instruccion_metodologia}
{competencias_contexto}

REGLAS:
- Responde SOLO con tablas Markdown | ITEM | CONTENIDO |
- Tabla 1: DATOS INFORMATIVOS, PROPÓSITOS DE APRENDIZAJE, MATERIALES, REFLEXIÓN
- Tabla 2: SECUENCIA DIDÁCTICA con sub-secciones INICIO / DESARROLLO / CIERRE
  - INICIO: {round(int(''.join(filter(str.isdigit, duracion)) or '90') * 0.15)} min aprox
  - DESARROLLO: {round(int(''.join(filter(str.isdigit, duracion)) or '90') * 0.65)} min aprox
  - CIERRE: {round(int(''.join(filter(str.isdigit, duracion)) or '90') * 0.20)} min aprox
- Tabla 3: RÚBRICA DE SESIÓN (columnas: Criterio | Logrado | En Proceso)
- Incluir METACOGNICIÓN explícita en el CIERRE
- NO uses viñetas ni HTML
"""
    logger.info(f"[Legacy] Generando sesión fallback: {titulo_sesion}")
    return _cliente().invocar(prompt, max_tokens=8000, temperature=0.65)
