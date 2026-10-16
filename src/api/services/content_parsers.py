# src/api/services/content_parsers.py
"""
Estrategias de parseo del texto crudo devuelto por el pipeline de agentes
hacia el dict estructurado que se guarda en Document.content.

Unidad y Sesión usaban dos formas de parseo distintas mezcladas dentro de
routes/generation.py (una vía src/app/docx_parsers.py, otra con un loop
if/elif inline). Aquí quedan detrás de la misma interfaz (Strategy) para que
agregar un tercer tipo de documento no vuelva a tocar los route handlers.
"""
import re
from typing import Any, Dict, Protocol


class DocumentContentParser(Protocol):
    """Convierte el texto crudo generado por el LLM en las secciones de Document.content."""

    def parsear(self, contenido: str, **kwargs: Any) -> Dict[str, Any]:
        ...


_NIVELES_RUBRICA = ("INICIO", "PROCESO", "LOGRADO", "DESTACADO", " AD", " A ", " B ", " C ")


def extraer_rubrica(contenido: str) -> str:
    """Extrae la tabla de rúbrica del contenido generado.

    El disparador original ("aparece 'criterio' + un nivel en la línea") daba
    falsos positivos: "Criterio de evaluación: ..." también aparece como
    prosa dentro de la fila de "Secuencia de Sesiones" (que menciona el
    criterio de cada sesión), arrastrando el resto del documento entero como
    si fuera la rúbrica. Ahora exige que la PRIMERA celda de la fila sea el
    encabezado ("Criterio") y que las demás celdas sean cortas (nombres de
    nivel como "Logrado", no párrafos narrativos), y una vez dentro, solo
    continúa mientras las filas mantengan la misma cantidad de columnas que
    el encabezado real de la rúbrica.
    """
    if not contenido:
        return ""
    lineas = contenido.split("\n")
    rubrica_lineas = []
    en_rubrica = False
    columnas_esperadas = None

    for linea in lineas:
        stripped = linea.strip()
        if not stripped.startswith("|"):
            if en_rubrica:
                break
            continue

        celdas = [c.strip() for c in stripped.strip("|").split("|")]

        if not en_rubrica:
            primera = celdas[0].upper() if celdas else ""
            demas_cortas = len(celdas) > 2 and all(len(c) < 60 for c in celdas[1:])
            if "CRITERIO" in primera and demas_cortas and any(
                nivel in linea.upper() for nivel in _NIVELES_RUBRICA
            ):
                en_rubrica = True
                columnas_esperadas = len(celdas)

        if en_rubrica:
            if columnas_esperadas is not None and len(celdas) != columnas_esperadas:
                break
            rubrica_lineas.append(linea)

    return "\n".join(rubrica_lineas).strip()


def extraer_fila_por_encabezado(contenido: str, clave: str) -> str:
    """Devuelve el contenido de la fila de tabla `| **ENCABEZADO** | contenido |`
    cuya primera celda empieza por `clave` (sin distinguir mayúsculas ni
    asteriscos). Si la celda continúa en líneas siguientes que no empiezan
    con "|" (saltos de línea dentro de la celda), también se incluyen."""
    if not contenido:
        return ""
    clave = clave.upper()
    partes: list = []
    dentro = False
    for linea in contenido.split("\n"):
        stripped = linea.strip()
        if stripped.startswith("|"):
            if dentro:
                break
            celdas = [c.strip() for c in stripped.strip("|").split("|")]
            if celdas and celdas[0].replace("*", "").strip().upper().startswith(clave):
                dentro = True
                resto = " ".join(c for c in celdas[1:] if c)
                if resto:
                    partes.append(resto)
        elif dentro:
            if not stripped:
                break
            partes.append(stripped.rstrip("|").strip())
    return "\n".join(partes).strip()


_GUIONES_FINALES = re.compile(r"\s*-{2,}\s*$")


def _sin_guiones_finales(texto: str) -> str:
    """Quita el resto del separador de tabla Markdown (`--`) que a veces queda pegado al final."""
    return _GUIONES_FINALES.sub("", texto or "").strip()


# La Unidad que sirve la API no tiene el límite de celda del DOCX del Streamlit legacy: el texto no se
# recorta (antes las actividades se cortaban a 800 caracteres, a media palabra).
_LIMITES_SECUENCIA = {"max_titulo": 500, "max_criterio": 2000, "max_actividades": 6000}


class UnidadContentParser:
    """Parsea el contenido crudo de una Unidad Didáctica reutilizando docx_parsers.py."""

    def parsear(self, contenido: str, *, area: str, num_sesiones: int = 4, **_: Any) -> Dict[str, Any]:
        from ...core.matriz_axiologica import extraer_matriz  # import local: ver generation_service
        from ...app.docx_parsers import (
            extraer_situacion_significativa_completa,
            extraer_propositos_completo,
            extraer_valores_enfoques_transversales,
            extraer_secuencia_sesiones,
        )

        situacion_extr = extraer_situacion_significativa_completa(contenido)
        propositos_extr = extraer_propositos_completo(contenido)
        valores_dict = extraer_valores_enfoques_transversales(contenido)
        sesiones_list = extraer_secuencia_sesiones(contenido, num_sesiones, **_LIMITES_SECUENCIA)
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
            "situacion_significativa": _sin_guiones_finales(situacion_extr),
            "propositos_de_aprendizaje": _sin_guiones_finales(propositos_extr),
            # HU-42: la matriz axiológica generada como tabla; si el contenido no
            # la trae (documentos antiguos o plantilla institucional), se conserva
            # el formato de texto de antes.
            "valores_y_enfoques_transversales": extraer_matriz(contenido) or (
                f"Valores: {valores_dict.get('valores')}\n\n"
                f"Enfoques: {valores_dict.get('enfoques_transversales')}"
            ),
            "secuencia_de_sesiones": secuencia_sesiones_str,
            "materiales_basicos": _sin_guiones_finales(extraer_fila_por_encabezado(contenido, "MATERIALES")),  # HU-40
            "rubrica_unidad": rubrica_unidad,
        }


class SesionContentParser:
    """Parsea el contenido crudo de una Sesión de Aprendizaje.

    El FormatterAgent normaliza el documento como una tabla Markdown de una
    sola fila por sección (`| **ENCABEZADO** | contenido... |`), no como texto
    plano con encabezados en su propia línea. Por eso cada fila se procesa de
    forma independiente: la sección se identifica por la primera celda y el
    contenido es el resto de esa MISMA fila — nunca se descarta contenido por
    aparecer junto a su encabezado (el bug anterior perdía la sección
    completa de "SECUENCIA DIDÁCTICA" por esto, y una mención incidental de
    "reflexión" dentro de "MATERIALES Y RECURSOS" activaba la sección
    equivocada).

    El LLM produce más subsecciones (situación significativa, enfoque
    transversal, materiales y recursos) que los campos que expone el editor;
    se agrupan en el campo relacionado más cercano.
    """

    _SECTION_KEYWORDS = [
        (("DATOS INFORMATIVOS", "SITUACIÓN SIGNIFICATIVA", "SITUACION SIGNIFICATIVA"), "datos"),
        (("PROPÓSITOS", "PROPOSITOS", "ENFOQUE TRANSVERSAL"), "propositos"),
        (("SECUENCIA DIDÁCTICA", "SECUENCIA DIDACTICA", "SECUENCIA DE ACTIVIDADES", "MATERIALES Y RECURSOS"), "secuencia"),
        (("REFLEXIÓN DOCENTE", "REFLEXION DOCENTE", "METACOGNICIÓN", "METACOGNICION"), "reflexion"),
    ]

    def parsear(self, contenido: str, *, tema_sesion: str, **_: Any) -> Dict[str, Any]:
        secciones: Dict[str, list] = {"datos": [], "reto": [], "propositos": [], "secuencia": [], "reflexion": []}
        current_section = None

        for line in contenido.split("\n"):
            stripped = line.strip()

            if stripped.startswith("|"):
                # Fila de tabla: [encabezado, contenido, ...] — clasificar por la
                # primera celda, nunca por texto que aparezca dentro del resto.
                celdas = [c.strip() for c in stripped.strip("|").split("|")]
                if not celdas or not celdas[0]:
                    continue
                encabezado = celdas[0].upper()
                resto = " ".join(c for c in celdas[1:] if c)

                # HU-41: "RETO" se compara contra el INICIO del encabezado; un
                # `in` lo activaría con cualquier palabra que lo contenga.
                if encabezado.replace("*", "").strip().startswith("RETO"):
                    current_section = "reto"
                    if resto:
                        secciones["reto"].append(resto)
                    continue

                bucket = next(
                    (target for keywords, target in self._SECTION_KEYWORDS
                     if any(kw in encabezado for kw in keywords)),
                    None,
                )
                if bucket:
                    current_section = bucket
                    if resto:
                        secciones[bucket].append(resto)
                # Filas de tabla sin encabezado reconocido (ej. la rúbrica final)
                # no se acumulan en ninguna sección — extraer_rubrica() las maneja aparte.
                continue

            # Texto plano (formato sin tabla): encabezado en su propia línea.
            lu = stripped.upper()
            if lu.replace("*", "").strip().rstrip(":") == "RETO":
                current_section = "reto"
                continue
            bucket = next(
                (target for keywords, target in self._SECTION_KEYWORDS
                 if any(kw in lu for kw in keywords)),
                None,
            )
            if bucket:
                current_section = bucket
                continue

            if current_section and stripped:
                secciones[current_section].append(stripped)

        rubrica_sesion = extraer_rubrica(contenido)
        from ...core.matriz_axiologica import extraer_matriz  # HU-42 (import local: ver generation_service)
        matriz = extraer_matriz(contenido)

        return {
            "titulo": f"Sesión - {tema_sesion}",
            "datos_informativos": "\n\n".join(secciones["datos"]).strip(),
            "reto": "\n\n".join(secciones["reto"]).strip(),
            "propositos_de_aprendizaje": "\n\n".join(secciones["propositos"]).strip(),
            **({"valores_y_enfoques_transversales": matriz} if matriz else {}),
            "secuencia_didactica": "\n\n".join(secciones["secuencia"]).strip(),
            "reflexion_sobre_la_actividad": "\n\n".join(secciones["reflexion"]).strip(),
            "rubrica_sesion": rubrica_sesion,
            "contenido_crudo": contenido,
        }
