"""HU-47: encabezado de control documentario de los formatos oficiales.

Los formatos de Unidad y Sesión llevan una tabla con: nombre del documento,
institución o red, versión, aprobado por (y fecha), revisado por (y fecha) y
número de páginas. Los valores son propios de cada institución, así que se
configuran en el perfil institucional (HU-31) y nunca van fijos en el código.

Sin configuración, el encabezado se omite y la exportación queda como antes.
"""
import re
from typing import Any, Dict, Optional

MAX_LARGO_VALOR = 80
MAX_LARGO_VERSION = 20
MAX_LARGO_FECHA = 40

# campo -> largo máximo
CAMPOS: Dict[str, int] = {
    "red": MAX_LARGO_VALOR,                # "Red Salesiana de Escuelas"; si falta se usa el nombre de la institución
    "version": MAX_LARGO_VERSION,
    "aprobado_por": MAX_LARGO_VALOR,
    "fecha_aprobacion": MAX_LARGO_FECHA,
    "revisado_por": MAX_LARGO_VALOR,
    "fecha_revision": MAX_LARGO_FECHA,
}

NOMBRE_FORMATO = {
    "unidad": "Formato de Unidad Didáctica",
    "sesion": "Formato de Sesión de Aprendizaje",
}


def _limpio(valor: Any, maximo: int) -> str:
    """Una sola línea, sin '|' (rompería tablas Markdown) y acotado."""
    if valor is None:
        return ""
    texto = re.sub(r"\s+", " ", str(valor)).strip().replace("|", "/")
    return texto[:maximo].rstrip()


def normalizar_control(crudo: Any) -> Dict[str, str]:
    """Deja solo los campos conocidos y no vacíos. {} si no hay nada configurado."""
    if not isinstance(crudo, dict):
        return {}
    limpio = {k: _limpio(crudo.get(k), maximo) for k, maximo in CAMPOS.items()}
    return {k: v for k, v in limpio.items() if v}


def construir_control(perfil: Optional[Any], tipo: str) -> Optional[Dict[str, str]]:
    """Datos del encabezado, o None si el perfil no tiene control documentario.

    Hay "configuración" cuando existe al menos un campo del control. En ese caso
    el encabezado se muestra completo y los campos sin dato quedan en blanco,
    como un formato por llenar.
    """
    if perfil is None or tipo not in NOMBRE_FORMATO:
        return None
    try:
        crudo = getattr(perfil, "control_documentario", None)
    except Exception:
        # La columna es diferida: si todavía no se aplicó la migración, leerla falla.
        # Una exportación nunca debe romperse por esto; simplemente no hay encabezado.
        return None
    control = normalizar_control(crudo)
    if not control:
        return None

    nombre = _limpio(getattr(perfil, "nombre_institucion", None), MAX_LARGO_VALOR)
    return {
        "documento": NOMBRE_FORMATO[tipo],
        "institucion": control.get("red") or nombre,
        "version": control.get("version", ""),
        "aprobado_por": control.get("aprobado_por", ""),
        "fecha_aprobacion": control.get("fecha_aprobacion", ""),
        "revisado_por": control.get("revisado_por", ""),
        "fecha_revision": control.get("fecha_revision", ""),
    }
