"""Defectos que solo aparecieron al generar de verdad con Bedrock (no con textos de prueba).

1. `extraer_matriz` se llevaba las tablas que el modelo escribe pegadas detrás de la matriz (la tabla
   de "INSTRUMENTOS" y la rúbrica completa): la matriz de una Unidad salía con 10 filas en vez de 3.
2. "Se detectaron N líneas de contenido fuera de las tablas": contaba como "fuera" las líneas de
   continuación de las celdas multilínea, que el propio prompt pide usar. Falsa alarma en cada generación.
"""
from src.core.matriz_axiologica import contar_filas_matriz, extraer_matriz
from src.validators.structure_validator import StructureValidator, ValidationReport

ENCABEZADO = "| Valor | Enfoques transversales | Comportamientos observables | Instrumento |"
SEPARADOR = "| -- | -- | -- | -- | |"
FILAS = [
    "| Fe | Enfoque de derecho | Practica la oración. | Escala de valoración | |",
    "| Amor | Enfoque intercultural | Llama por su nombre a los compañeros. | Lista de cotejo | |",
    "| Ciudadanía | Enfoque ambiental | Integra equipos de trabajo. | Rúbrica de actitudes | |",
]
RUBRICA = [
    "| Criterio | C — Inicio | B — Proceso | A — Logrado | AD — Destacado |",
    "| -- | -- | -- | -- | -- |",
    "| Identifica la estructura | a | b | c | d |",
    "| Infiere el posicionamiento | a | b | c | d |",
]
BASE = [ENCABEZADO, SEPARADOR, *FILAS]


def _texto(*bloques):
    return "\n".join(l for b in bloques for l in b)


def _valores(texto):
    return [l.split("|")[1].strip() for l in extraer_matriz(texto).splitlines()[2:]]


# --- 1. La matriz no arrastra las tablas siguientes ---

def test_la_matriz_sola_se_lee_completa():
    assert _valores(_texto(BASE)) == ["Fe", "Amor", "Ciudadanía"]


def test_no_se_lleva_la_tabla_de_la_rubrica_pegada_detras():
    assert contar_filas_matriz(_texto(BASE, RUBRICA)) == 3
    assert "Identifica la estructura" not in extraer_matriz(_texto(BASE, RUBRICA))


def test_no_se_lleva_una_tabla_item_contenido_pegada_detras():
    """Caso real: tras la matriz el modelo escribió `| ITEM | CONTENIDO` (sin cierre) y una fila INSTRUMENTOS."""
    siguiente = ["| ITEM | CONTENIDO", "| ----- | ---------- |", "| *INSTRUMENTOS** | Los siguientes instrumentos... | |"]
    texto = _texto(BASE, siguiente, RUBRICA)
    assert _valores(texto) == ["Fe", "Amor", "Ciudadanía"]
    assert "INSTRUMENTOS" not in extraer_matriz(texto) and "ITEM" not in extraer_matriz(texto)


def test_una_fila_residual_sin_contenido_termina_la_tabla_sin_comerse_la_ultima_fila():
    """Caso real de la Sesión: tras la matriz apareció `|  | --` justo antes de otra tabla."""
    texto = _texto([ENCABEZADO, SEPARADOR, FILAS[1], FILAS[2]],
                   ["|  | --", "| Criterio de evaluación | Logrado | En proceso |", "| -- | -- | -- |", "| c1 | a | b |"])
    assert _valores(texto) == ["Amor", "Ciudadanía"]


def test_una_fila_sin_la_celda_final_sigue_siendo_de_la_matriz():
    sin_instrumento = "| Fe | Enfoque | Comportamiento |"            # el instrumento vacío se perdió
    assert _valores(_texto([ENCABEZADO, SEPARADOR, sin_instrumento, FILAS[1]])) == ["Fe", "Amor"]


def test_la_matriz_seguida_de_texto_termina_ahi():
    assert contar_filas_matriz(_texto(BASE) + "\n\nTexto que ya no es de la tabla\n| Otro | x |") == 3


def test_el_conteo_ignora_el_separador():
    assert contar_filas_matriz(_texto(BASE)) == 3


# --- 2. Las celdas multilínea no son "contenido fuera de las tablas" ---

def _avisos_fuera_de_tabla(texto):
    reporte = ValidationReport()
    StructureValidator()._validar_contenido_fuera_tabla(texto, reporte)
    return [e.mensaje for e in reporte.errores]


CELDAS_MULTILINEA = (
    "| ITEM | CONTENIDO |\n|---|---|\n"
    "| **SECUENCIA DE SESIONES** | Sesión 1: Tema\nCriterio: c1\nActividades: a1\n"
    "Sesión 2: Tema\nCriterio: c2\nActividades: a2\nSesión 3: Tema\nCriterio: c3\nActividades: a3 |\n"
    "| **MATERIALES** | Para el docente: proyector\nPara el estudiante: cuaderno\nOtro\nMás |\n"
)


def test_las_celdas_multilinea_no_generan_falsa_alarma():
    assert _avisos_fuera_de_tabla(CELDAS_MULTILINEA) == []


def test_la_prosa_real_fuera_de_las_tablas_sigue_detectandose():
    texto = ("| ITEM | CONTENIDO |\n|---|---|\n| **A** | texto |\n\n"
             "Esto es prosa suelta.\nOtra línea.\nUna tercera.\nUna cuarta pasa el umbral.\n")
    assert _avisos_fuera_de_tabla(texto) == ["Se detectaron 4 líneas de contenido fuera de las tablas"]


def test_prosa_despues_de_una_celda_multilinea_se_cuenta_solo_la_que_esta_fuera():
    texto = CELDAS_MULTILINEA + "\nProsa 1\nProsa 2\nProsa 3\nProsa 4\n"
    assert _avisos_fuera_de_tabla(texto) == ["Se detectaron 4 líneas de contenido fuera de las tablas"]


def test_una_fila_nueva_cierra_la_celda_abierta():
    """Si una fila quedó sin '|' final, la siguiente fila (que empieza con '|') no se toma por continuación."""
    texto = "| ITEM | CONTENIDO\n| a | b |\nProsa 1\nProsa 2\nProsa 3\nProsa 4\n"
    assert _avisos_fuera_de_tabla(texto) == ["Se detectaron 4 líneas de contenido fuera de las tablas"]


def test_el_texto_sin_tablas_no_avisa():
    assert _avisos_fuera_de_tabla("Solo prosa\nsin ninguna tabla\nen absoluto\nni una\nmás") == []
