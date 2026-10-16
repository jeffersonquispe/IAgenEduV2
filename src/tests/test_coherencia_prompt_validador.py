"""El validador solo puede exigir lo que el prompt realmente pide al modelo.

Defecto que esto evita: el validador exigía una sección "INSTRUMENTOS" que el prompt de la Unidad nunca
produjo. Toda Unidad generada fallaba con un error crítico y el pipeline hacía SIEMPRE un segundo pase de
corrección (otra llamada larga a Sonnet: más lento, más caro y con peor formato). Solo se vio al generar de verdad.
"""
from pathlib import Path

import pytest

from src.core.matriz_axiologica import contar_filas_matriz, extraer_matriz
from src.validators.structure_validator import StructureValidator

RAIZ = Path(__file__).resolve().parents[2]
PROMPTS = RAIZ / "src" / "prompts"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "unidad_cruda_real.md"


def _prompt(nombre):
    return (PROMPTS / f"{nombre}.md").read_text(encoding="utf-8").upper()


@pytest.mark.parametrize("seccion", StructureValidator.SECCIONES_UNIDAD)
def test_cada_seccion_que_valida_la_unidad_esta_en_su_prompt(seccion):
    assert seccion.upper() in _prompt("unidad_didactica"), (
        f"El validador exige '{seccion}' pero unidad_didactica.md nunca se lo pide al modelo: "
        f"toda Unidad fallaría con un error crítico.")


@pytest.mark.parametrize("seccion", StructureValidator.SECCIONES_SESION)
def test_cada_seccion_que_valida_la_sesion_esta_en_su_prompt(seccion):
    assert seccion.upper() in _prompt("sesion_aprendizaje"), (
        f"El validador exige '{seccion}' pero sesion_aprendizaje.md nunca se lo pide al modelo.")


def test_el_validador_no_exige_el_plural_que_el_prompt_nunca_produjo():
    assert "INSTRUMENTOS" not in StructureValidator.SECCIONES_UNIDAD
    assert "INSTRUMENTO" in StructureValidator.SECCIONES_UNIDAD


# --- Con una salida REAL del modelo (guardada como fixture) ---

@pytest.fixture(scope="module")
def unidad_real():
    return FIXTURE.read_text(encoding="utf-8")


def test_una_unidad_real_pasa_la_validacion_estructural_sin_errores_criticos(unidad_real):
    """Si esto falla, cada generación real volvería a disparar el pase de corrección."""
    reporte = StructureValidator().validar_unidad_didactica(unidad_real, num_sesiones=4)
    assert not reporte.tiene_errores_criticos, [e.mensaje for e in reporte.errores if e.tipo == "CRITICO"]
    assert reporte.puntaje >= 90


def test_la_matriz_de_la_unidad_real_tiene_las_tres_filas_del_perfil(unidad_real):
    assert contar_filas_matriz(unidad_real) == 3
    tabla = extraer_matriz(unidad_real)
    for valor in ("Fe", "Amor", "Ciudadanía"):
        assert f"| {valor} |" in tabla
    assert "[COMPLETAR" not in tabla.upper()                    # el modelo completó enfoque e instrumento
    assert "Criterio" not in tabla.splitlines()[0]              # y la tabla no arrastra la rúbrica


def test_la_unidad_real_trae_un_criterio_por_sesion(unidad_real):
    import re
    assert len(re.findall(r"Criterio de evaluaci[oó]n\s*:", unidad_real)) >= 4
