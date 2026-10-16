"""HU-44: biblioteca de ejemplos de Unidad y Sesión dentro de la plataforma.

Los ejemplos son archivos JSON en data/ejemplos/ con la misma forma que
Document.content, de modo que se pueden mostrar con el visor del Editor en
modo solo lectura y actualizar sin tocar código. Esta lectura es de archivos:
no usa la IA, no escribe en la base de datos y no cuenta para la gamificación.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DIRECTORIO_EJEMPLOS = Path(__file__).resolve().parent.parent.parent / "data" / "ejemplos"
TIPOS_VALIDOS = ("unidad", "sesion")
CAMPOS_RESUMEN = ("id", "tipo", "titulo", "descripcion")


def _leer(ruta: Path) -> Optional[Dict[str, Any]]:
    """Lee y valida un ejemplo; devuelve None (y lo registra) si el archivo no sirve."""
    try:
        ejemplo = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("[Ejemplos] No se pudo leer %s: %s", ruta.name, e)
        return None
    if not isinstance(ejemplo, dict):
        logger.warning("[Ejemplos] %s: se esperaba un objeto JSON", ruta.name)
        return None

    contenido = ejemplo.get("content")
    valido = (
        isinstance(ejemplo.get("id"), str) and ejemplo["id"].strip()
        and ejemplo.get("tipo") in TIPOS_VALIDOS
        and isinstance(ejemplo.get("titulo"), str) and ejemplo["titulo"].strip()
        and isinstance(contenido, dict) and contenido
        and all(isinstance(v, str) for v in contenido.values())
    )
    if not valido:
        logger.warning("[Ejemplos] %s no cumple el formato esperado y se omite", ruta.name)
        return None
    return ejemplo


def _todos(directorio: Optional[Path] = None) -> List[Dict[str, Any]]:
    carpeta = directorio or DIRECTORIO_EJEMPLOS
    if not carpeta.is_dir():
        return []
    ejemplos, vistos = [], set()
    for ruta in sorted(carpeta.glob("*.json")):
        ejemplo = _leer(ruta)
        if ejemplo is None:
            continue
        if ejemplo["id"] in vistos:
            logger.warning("[Ejemplos] id repetido %r en %s: se omite", ejemplo["id"], ruta.name)
            continue
        vistos.add(ejemplo["id"])
        ejemplos.append(ejemplo)
    # Unidades primero y, dentro de cada tipo, por título.
    return sorted(ejemplos, key=lambda e: (e["tipo"] != "unidad", e["titulo"]))


def listar_ejemplos(directorio: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Resumen de cada ejemplo (sin el contenido completo)."""
    return [{k: e.get(k, "") for k in CAMPOS_RESUMEN} for e in _todos(directorio)]


def obtener_ejemplo(ejemplo_id: str, directorio: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Ejemplo completo por id, o None. El id se busca entre los ejemplos válidos: nunca se
    usa para armar una ruta de archivo, así que no hay riesgo de salir del directorio."""
    for ejemplo in _todos(directorio):
        if ejemplo["id"] == ejemplo_id:
            return ejemplo
    return None
