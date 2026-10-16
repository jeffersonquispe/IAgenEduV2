"""HU-30: revalidación de un documento ya editado o refinado, sin IA.

La validación de la generación se hace sobre el texto crudo que produce el modelo.
Después, el docente edita o refina secciones sueltas en el Editor, y el documento
vive como un diccionario de secciones (los campos de Document.content), no como
ese texto. Esta revalidación recalcula, sobre las secciones actuales, los
controles que sí se pueden evaluar a ese nivel:

  * que cada sección obligatoria tenga contenido,
  * un criterio de evaluación por sesión y una fila de rúbrica por sesión,
  * que no haya temas repetidos entre sesiones,
  * que la matriz axiológica tenga filas y no conserve campos [COMPLETAR],
  * que no queden etiquetas HTML sueltas,
  * en la Sesión, que la secuencia tenga Inicio, Desarrollo y Cierre.

Los errores de la validación anterior sobre algo que NO se puede reevaluar desde
las secciones (p. ej. la falta de "EVIDENCIAS" en el texto original, o lo que
juzgó el LLM) se conservan: borrar una sección de este diccionario no es la
forma de arreglarlos, y no deben desaparecer en silencio.
"""
import re
from typing import Any, Dict, Iterable, List, Optional

from .structure_validator import StructureValidator, ValidationError, ValidationReport
from ..utils.table_utils import extraer_sesiones_numeradas

# campo de Document.content -> nombre de la sección en los errores de StructureValidator
CAMPOS_REQUERIDOS: Dict[str, Dict[str, str]] = {
    "unidad": {
        "situacion_significativa": "SITUACIÓN SIGNIFICATIVA",
        "propositos_de_aprendizaje": "PROPÓSITOS",
        "valores_y_enfoques_transversales": "VALORES",
        "secuencia_de_sesiones": "SECUENCIA",
        "materiales_basicos": "MATERIALES",
    },
    "sesion": {
        "datos_informativos": "DATOS INFORMATIVOS",
        "reto": "RETO",
        "propositos_de_aprendizaje": "PROPÓSITOS",
        "secuencia_didactica": "SECUENCIA DIDÁCTICA",
    },
}

# Secciones de los errores que también se calculan aquí (además de los campos requeridos).
SECCIONES_ADICIONALES: Dict[str, set] = {
    "unidad": {"SECUENCIA DE SESIONES", "RÚBRICA ANALÍTICA", "MATRIZ AXIOLÓGICA"},
    "sesion": {"MATRIZ AXIOLÓGICA"},
}

MAX_ERRORES_PREVIOS = 100
MAX_LARGO_MENSAJE = 300
_TIPOS_ERROR = ("CRITICO", "ADVERTENCIA")


def tipos_soportados() -> Iterable[str]:
    return CAMPOS_REQUERIDOS.keys()


def _errores_previos(detalle: Optional[List[Any]]) -> List[ValidationError]:
    """Convierte el detalle que manda el cliente en errores, descartando lo que no tenga la forma esperada."""
    errores: List[ValidationError] = []
    for d in (detalle or [])[:MAX_ERRORES_PREVIOS]:
        if not isinstance(d, dict) or d.get("tipo") not in _TIPOS_ERROR:
            continue
        mensaje = str(d.get("mensaje") or "").strip()[:MAX_LARGO_MENSAJE]
        if not mensaje:
            continue
        errores.append(ValidationError(
            tipo=d["tipo"],
            categoria=str(d.get("categoria") or "CONTENIDO")[:30],
            mensaje=mensaje,
            seccion=str(d.get("seccion") or "")[:80],
        ))
    return errores


def revalidar_contenido(
    contenido: Dict[str, Any],
    tipo: str,
    detalle_previo: Optional[List[Any]] = None,
) -> ValidationReport:
    """Devuelve el ValidationReport del documento actual.

    `contenido`: secciones actuales (campos de Document.content).
    `detalle_previo`: el `detalle` de la validación anterior; de ahí se conservan
    los errores que esta revalidación no puede recalcular.
    """
    if tipo not in CAMPOS_REQUERIDOS:
        raise ValueError(f"tipo de documento no soportado: {tipo!r}")

    validador = StructureValidator()
    textos = {k: v for k, v in (contenido or {}).items() if isinstance(v, str)}
    reporte = ValidationReport()

    # 1) Secciones obligatorias con contenido.
    for campo, nombre in CAMPOS_REQUERIDOS[tipo].items():
        if not textos.get(campo, "").strip():
            reporte.errores.append(ValidationError(
                tipo="CRITICO", categoria="ESTRUCTURA",
                mensaje=f"Falta la sección requerida: {nombre}", seccion=nombre,
            ))

    # 2) Matriz axiológica (HU-42).
    validador._validar_matriz_axiologica(textos.get("valores_y_enfoques_transversales", ""), reporte)

    # 3) Controles propios de cada tipo.
    if tipo == "unidad":
        secuencia = textos.get("secuencia_de_sesiones", "")
        if secuencia.strip():
            sesiones = extraer_sesiones_numeradas(secuencia)
            criterios = len(re.findall(r"^\s*Criterio\s*:", secuencia, flags=re.IGNORECASE | re.MULTILINE))
            if sesiones and criterios != len(sesiones):
                reporte.errores.append(ValidationError(
                    tipo="ADVERTENCIA", categoria="CONTENIDO",
                    mensaje=(f"Se esperaban {len(sesiones)} criterios de evaluación (uno por sesión), "
                             f"pero se detectaron {criterios} en el contenido."),
                    seccion="SECUENCIA DE SESIONES",
                ))
            validador._validar_temas_no_repetidos(secuencia, reporte)                      # HU-29
            rubrica = textos.get("rubrica_unidad", "")
            if rubrica.strip() and sesiones:
                validador._validar_filas_rubrica_vs_sesiones(rubrica, len(sesiones), reporte)   # HU-39
    else:
        secuencia = textos.get("secuencia_didactica", "")
        if secuencia.strip():
            validador._validar_secuencia_didactica(secuencia, reporte)

    # 4) HTML residual en cualquier sección.
    validador._validar_html_residual("\n".join(textos.values()), reporte)

    # 5) Se conserva lo que no se puede recalcular desde las secciones.
    recalculadas = set(CAMPOS_REQUERIDOS[tipo].values()) | SECCIONES_ADICIONALES[tipo]
    vistos = {(e.tipo, e.mensaje, e.seccion) for e in reporte.errores}
    for previo in _errores_previos(detalle_previo):
        if previo.seccion in recalculadas or "etiquetas HTML residuales" in previo.mensaje:
            continue
        clave = (previo.tipo, previo.mensaje, previo.seccion)
        if clave not in vistos:
            vistos.add(clave)
            reporte.errores.append(previo)
    return reporte
