"""HU-46: sección DATOS INFORMATIVOS de la Unidad Didáctica.

Se arma en código (no la genera el LLM) a partir del perfil institucional
(HU-31) y de los datos que el docente indica en el wizard, para que campos como
la UGEL, la coordinación pedagógica o las fechas nunca sean inventados por el
modelo. Los campos sin dato se omiten.
"""
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

MAX_LARGO_SECCIONES = 100
MAX_LARGO_CELDA = 200


def limpiar_celda(valor: Any, maximo: int = MAX_LARGO_CELDA) -> str:
    """Deja un valor apto para una celda de tabla Markdown: una sola línea, sin
    '|' (rompería la tabla) y con largo acotado."""
    if valor is None:
        return ""
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    texto = texto.replace("|", "/")
    return texto[:maximo].rstrip()


def _parsear_fecha(valor: Any, nombre: str) -> Optional[date]:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if not isinstance(valor, str):
        raise ValueError(f"{nombre} debe ser una fecha en formato AAAA-MM-DD.")
    try:
        return datetime.strptime(valor.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{nombre} no es una fecha válida (use el formato AAAA-MM-DD).")


def normalizar_datos_unidad(params: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y normaliza lo que el wizard envía para los datos informativos.

    Devuelve {"secciones": str, "fecha_inicio": date|None, "fecha_termino": date|None}.
    Lanza ValueError con un mensaje legible si algo es inválido.
    """
    secciones = params.get("secciones")
    if secciones is not None and not isinstance(secciones, str):
        raise ValueError("Las secciones deben ser texto (ej. '3ro A y 3ro B').")
    secciones = limpiar_celda(secciones, MAX_LARGO_SECCIONES + 1)
    if len(secciones) > MAX_LARGO_SECCIONES:
        raise ValueError(f"Las secciones son demasiado largas (máximo {MAX_LARGO_SECCIONES} caracteres).")

    inicio = _parsear_fecha(params.get("fecha_inicio"), "La fecha de inicio")
    termino = _parsear_fecha(params.get("fecha_termino"), "La fecha de término")
    if inicio and termino and termino < inicio:
        raise ValueError("La fecha de término no puede ser anterior a la fecha de inicio.")
    return {"secciones": secciones, "fecha_inicio": inicio, "fecha_termino": termino}


def _fmt(d: Optional[date]) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def construir_datos_informativos_unidad(
    perfil: Any,
    area: str,
    grado: Any,
    datos: Dict[str, Any],
    docente: Optional[str] = None,
) -> str:
    """Tabla `| ITEM | CONTENIDO |` con los datos informativos disponibles.

    `perfil` es el InstitutionProfile del docente (o None); `datos` es la salida
    de normalizar_datos_unidad().
    """
    grado_txt = limpiar_celda(grado)
    secciones = datos.get("secciones") or ""
    grado_y_secciones = f"{grado_txt} {secciones}".strip() if secciones else grado_txt

    filas: List[Tuple[str, str]] = [
        ("DRE / UGEL", limpiar_celda(getattr(perfil, "dre_ugel", None))),
        ("Institución educativa", limpiar_celda(getattr(perfil, "nombre_institucion", None))),
        ("Área curricular", limpiar_celda(area)),
        ("Grado y secciones", grado_y_secciones),
        ("Fecha de inicio", _fmt(datos.get("fecha_inicio"))),
        ("Fecha de término", _fmt(datos.get("fecha_termino"))),
        ("Coordinación pedagógica", limpiar_celda(getattr(perfil, "coordinacion_pedagogica", None))),
        ("Docente(s)", limpiar_celda(docente)),
    ]
    filas = [(k, v) for k, v in filas if v]
    if not filas:
        return ""

    lineas = ["| ITEM | CONTENIDO |", "|------|-----------|"]
    lineas += [f"| **{k}** | {v} |" for k, v in filas]
    return "\n".join(lineas)
