# src/api/services/content_parsers.py
"""
Estrategias de parseo del texto crudo devuelto por el pipeline de agentes
hacia el dict estructurado que se guarda en Document.content.

Unidad y Sesión usaban dos formas de parseo distintas mezcladas dentro de
routes/generation.py (una vía src/app/docx_parsers.py, otra con un loop
if/elif inline). Aquí quedan detrás de la misma interfaz (Strategy) para que
agregar un tercer tipo de documento no vuelva a tocar los route handlers.
"""
from typing import Any, Dict, Protocol


class DocumentContentParser(Protocol):
    """Convierte el texto crudo generado por el LLM en las secciones de Document.content."""

    def parsear(self, contenido: str, **kwargs: Any) -> Dict[str, Any]:
        ...


def extraer_rubrica(contenido: str) -> str:
    """Extrae la tabla de rúbrica del contenido generado."""
    if not contenido:
        return ""
    lineas = contenido.split("\n")
    rubrica_lineas = []
    en_rubrica = False
    for linea in lineas:
        l_upper = linea.upper()
        if (("| CRITERIO" in l_upper or "CRITERIO DE EVALUACI" in l_upper)
                and ("INICIO" in l_upper or " AD " in l_upper or "DESTACADO" in l_upper
                     or "LOGRADO" in l_upper or "PROCESO" in l_upper)):
            en_rubrica = True
        if en_rubrica:
            if linea.strip().startswith("|"):
                rubrica_lineas.append(linea)
            elif rubrica_lineas and not linea.strip():
                rubrica_lineas.append(linea)
            elif rubrica_lineas and not linea.strip().startswith("|"):
                break
    return "\n".join(rubrica_lineas).strip()


class UnidadContentParser:
    """Parsea el contenido crudo de una Unidad Didáctica reutilizando docx_parsers.py."""

    def parsear(self, contenido: str, *, area: str, **_: Any) -> Dict[str, Any]:
        from ...app.docx_parsers import (
            extraer_situacion_significativa_completa,
            extraer_propositos_completo,
            extraer_valores_enfoques_transversales,
            extraer_secuencia_sesiones,
        )

        situacion_extr = extraer_situacion_significativa_completa(contenido)
        propositos_extr = extraer_propositos_completo(contenido)
        valores_dict = extraer_valores_enfoques_transversales(contenido)
        sesiones_list = extraer_secuencia_sesiones(contenido)
        rubrica_unidad = extraer_rubrica(contenido)

        secuencia_sesiones_str = ""
        for i, ses in enumerate(sesiones_list):
            if ses.get("titulo"):
                secuencia_sesiones_str += (
                    f"Sesión {i+1}: {ses.get('titulo')}\n"
                    f"Criterio: {ses.get('criterio')}\n"
                    f"Actividades: {ses.get('actividades')}\n\n"
                )

        return {
            "titulo": f"Unidad Didáctica - {area}",
            "situacion_significativa": situacion_extr,
            "propositos_de_aprendizaje": propositos_extr,
            "valores_y_enfoques_transversales": (
                f"Valores: {valores_dict.get('valores')}\n\n"
                f"Enfoques: {valores_dict.get('enfoques_transversales')}"
            ),
            "secuencia_de_sesiones": secuencia_sesiones_str,
            "rubrica_unidad": rubrica_unidad,
        }


class SesionContentParser:
    """Parsea el contenido crudo de una Sesión de Aprendizaje (secciones por encabezado)."""

    def parsear(self, contenido: str, *, tema_sesion: str, **_: Any) -> Dict[str, Any]:
        datos_informativos = propositos_ap = secuencia_didactica = reflexion = ""
        current_section = None

        for line in contenido.split("\n"):
            lu = line.upper().strip()

            # Detectar cambios de sección (más flexible)
            if any(x in lu for x in ["DATOS INFORMATIVOS", "DATOS INFORMATBOS"]):
                current_section = "datos"
                continue
            elif any(x in lu for x in ["PROPÓSITOS", "PROPOSITOS", "PROPÓSITO DE APRENDIZAJE"]):
                current_section = "propositos"
                continue
            elif any(x in lu for x in ["SECUENCIA DIDÁCTICA", "SECUENCIA DIDACTICA", "SECUENCIA DE ACTIVIDADES"]):
                current_section = "secuencia"
                continue
            elif any(x in lu for x in ["REFLEXIÓN", "REFLEXION SOBRE LA ACTIVIDAD", "METACOGNICIÓN"]):
                current_section = "reflexion"
                continue
            elif any(x in lu for x in ["RÚBRICA", "RUBRICA"]):
                # Cambio a rúbrica
                continue

            # Acumular contenido en la sección actual
            if current_section and line.strip():  # Solo si no es línea vacía
                if current_section == "datos":
                    datos_informativos += line + "\n"
                elif current_section == "propositos":
                    propositos_ap += line + "\n"
                elif current_section == "secuencia":
                    secuencia_didactica += line + "\n"
                elif current_section == "reflexion":
                    reflexion += line + "\n"

        rubrica_sesion = extraer_rubrica(contenido)

        return {
            "titulo": f"Sesión - {tema_sesion}",
            "datos_informativos": datos_informativos.strip(),
            "propositos_de_aprendizaje": propositos_ap.strip(),
            "secuencia_didactica": secuencia_didactica.strip(),
            "reflexion_sobre_la_actividad": reflexion.strip(),
            "rubrica_sesion": rubrica_sesion,
            "contenido_crudo": contenido,
        }
