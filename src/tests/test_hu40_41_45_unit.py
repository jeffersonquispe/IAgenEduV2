"""Tests unitarios HU-40 (materiales), HU-41 (reto) y HU-45 (límite de competencias)."""
from pathlib import Path

import pytest

from src.validators.structure_validator import StructureValidator

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

RELLENO = "| ITEM | CONTENIDO |\n|------|-----------|\n"


def _tabla(*secciones: str) -> str:
    filas = "".join(f"| **{s}** | contenido de prueba para {s} |\n" for s in secciones)
    return RELLENO + filas


def _criticos(reporte):
    return [e.seccion for e in reporte.errores if e.tipo == "CRITICO"]


# --- Prompts ---

def test_prompt_unidad_incluye_materiales_basicos():
    texto = (PROMPTS / "unidad_didactica.md").read_text(encoding="utf-8")
    assert "MATERIALES BÁSICOS" in texto
    assert "Para el docente" in texto and "Para el estudiante" in texto


def test_prompt_sesion_incluye_reto_separado():
    texto = (PROMPTS / "sesion_aprendizaje.md").read_text(encoding="utf-8")
    assert "| **RETO** |" in texto
    assert "| **SITUACIÓN SIGNIFICATIVA** |" in texto


# --- Validador ---

@pytest.mark.parametrize("faltante", StructureValidator.SECCIONES_UNIDAD)
def test_unidad_reporta_critico_por_cada_seccion_faltante(faltante):
    secciones = [s for s in StructureValidator.SECCIONES_UNIDAD if s != faltante]
    reporte = StructureValidator().validar_unidad_didactica(_tabla(*secciones))
    assert faltante in _criticos(reporte)


def test_unidad_completa_no_tiene_criticos():
    reporte = StructureValidator().validar_unidad_didactica(
        _tabla(*StructureValidator.SECCIONES_UNIDAD)
    )
    assert _criticos(reporte) == []
    assert reporte.es_valido


def test_unidad_sin_materiales_es_rechazada():
    secciones = [s for s in StructureValidator.SECCIONES_UNIDAD if s != "MATERIALES"]
    reporte = StructureValidator().validar_unidad_didactica(_tabla(*secciones))
    assert not reporte.es_valido


def test_sesion_exige_reto():
    secciones = [s for s in StructureValidator.SECCIONES_SESION if s != "RETO"]
    contenido = _tabla(*secciones) + "INICIO DESARROLLO CIERRE"
    reporte = StructureValidator().validar_sesion_aprendizaje(contenido)
    assert "RETO" in _criticos(reporte)


def test_sesion_completa_es_valida():
    contenido = _tabla(*StructureValidator.SECCIONES_SESION) + "INICIO DESARROLLO CIERRE"
    reporte = StructureValidator().validar_sesion_aprendizaje(contenido)
    assert _criticos(reporte) == []


# --- HU-45: constantes de límite ---

def test_limite_competencias_unidad_es_2():
    from src.api.services.generation_service import MAX_COMPETENCIAS_UNIDAD
    assert MAX_COMPETENCIAS_UNIDAD == 2


def test_validar_limite_competencias_acepta_hasta_2():
    from src.api.services.generation_service import GenerationService
    GenerationService.validar_limite_competencias({"competencias": ["A", "B"]})
    GenerationService.validar_limite_competencias({})


def test_validar_limite_competencias_rechaza_3():
    from src.api.services.generation_service import GenerationService
    with pytest.raises(ValueError, match="Máximo 2"):
        GenerationService.validar_limite_competencias({"competencias": ["A", "B", "C"]})
