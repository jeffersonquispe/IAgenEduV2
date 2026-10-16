"""HU-42: matriz axiológica estructurada (Valor | Enfoques | Comportamientos | Instrumento).

La matriz oficial de las instituciones tiene una fila por valor, con su enfoque
transversal, el comportamiento observable y el instrumento. Este módulo:

  * decide QUÉ filas debe llevar el documento (las del perfil institucional, o
    un emparejamiento genérico valores/enfoques si el perfil no trae matriz),
  * redacta las instrucciones que se inyectan al prompt para que el modelo
    complete la tabla respetando esas filas, y
  * extrae la tabla ya generada del texto para guardarla como sección propia.

Lo que el perfil ya define se conserva tal cual; el modelo solo completa lo que
falta (enfoque, comportamiento, instrumento).
"""
import re
from typing import Any, Dict, List, Optional

from .contexto_institucional import limitar
from .valores_institucionales import resolver_enfoques_transversales, resolver_valores_institucionales

# Una matriz de más filas deja de ser legible en el documento.
MAX_FILAS_MATRIZ = 5

LIMITE_VALOR = 80
LIMITE_ENFOQUE = 150
LIMITE_COMPORTAMIENTO = 700
LIMITE_INSTRUMENTO = 120

ENCABEZADO = "| Valor | Enfoques transversales | Comportamientos observables | Instrumento |"


def _celda(valor: Any, maximo: int) -> str:
    """Texto apto para una celda de tabla Markdown (sin '|' ni saltos de línea)."""
    return limitar(valor, maximo).replace("|", "/")


def construir_filas_matriz(perfil: Optional[Any], max_filas: int = MAX_FILAS_MATRIZ) -> List[Dict[str, str]]:
    """Filas que debe llevar la matriz: [{valor, enfoque, comportamiento, instrumento}].

    Los campos vacíos significan "el modelo debe completarlos".
    """
    filas: List[Dict[str, str]] = []
    for fila in (getattr(perfil, "matriz_axiologica", None) or []):
        if not isinstance(fila, dict):
            continue
        valor = _celda(fila.get("valor"), LIMITE_VALOR)
        if not valor:
            continue
        filas.append({
            "valor": valor,
            "enfoque": _celda(fila.get("enfoque"), LIMITE_ENFOQUE),
            "comportamiento": _celda(fila.get("comportamiento_observable"), LIMITE_COMPORTAMIENTO),
            "instrumento": _celda(fila.get("instrumento"), LIMITE_INSTRUMENTO),
        })
    if filas:
        return filas[:max_filas]

    # Sin matriz propia: emparejamiento genérico valor <-> enfoque.
    valores = resolver_valores_institucionales(perfil)
    enfoques = resolver_enfoques_transversales(perfil)
    return [
        {
            "valor": _celda(v, LIMITE_VALOR),
            "enfoque": _celda(enfoques[i % len(enfoques)], LIMITE_ENFOQUE) if enfoques else "",
            "comportamiento": "",
            "instrumento": "",
        }
        for i, v in enumerate(valores[:max_filas])
    ]


def instrucciones_matriz(filas: List[Dict[str, str]], enfoques: List[str], por_sesion: bool = False) -> str:
    """Bloque de texto para el placeholder {contexto_matriz} del prompt."""
    if not filas:
        return ""
    lineas = [
        "FILAS DE LA MATRIZ AXIOLÓGICA (úsalas exactamente como se indican; completa solo lo que dice [COMPLETAR]):"
    ]
    for i, f in enumerate(filas, 1):
        lineas.append(
            f"{i}. Valor: {f['valor']} | "
            f"Enfoque: {f['enfoque'] or '[COMPLETAR: elige UNO del listado de enfoques]'} | "
            f"Comportamiento observable: {f['comportamiento'] or '[COMPLETAR: conducta concreta y observable en clase]'} | "
            f"Instrumento: {f['instrumento'] or '[COMPLETAR: lista de cotejo, escala de valoración o rúbrica de actitudes]'}"
        )
    if enfoques:
        lineas.append("Listado de enfoques disponibles: " + "; ".join(enfoques))
    if por_sesion:
        lineas.append(
            "Para ESTA sesión incluye solo las 1 o 2 filas cuyo valor se relacione mejor con el tema de la sesión."
        )
    else:
        lineas.append("Genera EXACTAMENTE estas filas, en este orden, sin agregar ni quitar ninguna.")
    return "\n".join(lineas) + "\n"


# --- Extracción desde el texto generado -----------------------------------

def _es_encabezado_matriz(linea: str) -> bool:
    s = linea.strip()
    if not s.startswith("|"):
        return False
    primera = s.strip("|").split("|")[0].replace("*", "").strip().upper()
    return primera.startswith("VALOR") and "COMPORTAMIENTO" in s.upper()


def _celdas(linea: str) -> List[str]:
    """Celdas de una fila Markdown, sin las celdas vacías del final (el formateador añade una de más)."""
    partes = [c.strip() for c in linea.strip().strip("|").split("|")]
    while partes and not partes[-1]:
        partes.pop()
    return partes


_CELDA_SEPARADORA = re.compile(r":?-{2,}:?")
_CELDA_VACIA_O_GUIONES = re.compile(r"(:?-+:?)?")


def _es_separador(linea: str) -> bool:
    """Fila separadora de tabla: todas sus celdas son guiones (`|---|---|`)."""
    celdas = _celdas(linea)
    return bool(celdas) and all(_CELDA_SEPARADORA.fullmatch(c) for c in celdas)


def _es_residuo_de_separador(linea: str) -> bool:
    """Fila sin contenido (solo celdas vacías o guiones) que no es un separador válido, p. ej. `|  | --`."""
    partes = [c.strip() for c in linea.strip().strip("|").split("|")]
    return all(_CELDA_VACIA_O_GUIONES.fullmatch(c) for c in partes) and not _es_separador(linea)


def extraer_matriz(contenido: str) -> str:
    """Tabla Markdown de la matriz axiológica, o "" si no está en el contenido.

    El modelo escribe las tablas una tras otra, a veces sin línea en blanco entre ellas. La tabla
    termina cuando: la línea no es de tabla; una fila tiene más columnas que el encabezado; aparece
    un segundo separador (la línea anterior era el encabezado de la tabla siguiente); o aparece una
    fila sin contenido. Sin esto, la matriz se llevaba consigo las tablas que venían detrás
    (instrumentos, rúbrica) y se guardaba mezclada con ellas.
    """
    if not contenido:
        return ""
    salida: List[str] = []
    ancho = 0
    separadores = 0
    dentro = False
    for linea in contenido.split("\n"):
        s = linea.strip()
        if not dentro:
            if _es_encabezado_matriz(s):
                dentro, ancho = True, len(_celdas(s))
                salida.append(s)
            continue
        if not s.startswith("|"):
            break
        if _es_separador(s):
            separadores += 1
            if separadores > 1:               # empieza otra tabla: la línea anterior era su encabezado
                salida.pop()
                break
        elif _es_residuo_de_separador(s) or len(_celdas(s)) > ancho:
            break
        salida.append(s)
    return "\n".join(salida)


def contar_filas_matriz(contenido: str) -> int:
    """Filas de datos de la matriz (sin encabezado ni separador)."""
    tabla = extraer_matriz(contenido)
    if not tabla:
        return 0
    return sum(1 for l in tabla.split("\n")[1:] if not _es_separador(l))


def tiene_matriz(contenido: str) -> bool:
    return bool(extraer_matriz(contenido))
