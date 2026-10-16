"""Tests HU-35 (competencias múltiples) y HU-39 (criterios/rúbrica vs sesiones)."""
from src.agents.generator_agent import GeneratorAgent
from src.validators.structure_validator import StructureValidator


def _agent():
    return GeneratorAgent.__new__(GeneratorAgent)


def test_hu35_varias_competencias_usa_bloque_plural():
    # Mismo separador que arma GenerationService ("\n".join)
    texto = "\n".join(["Competencia A", "Competencia B"])
    ctx = _agent()._construir_contexto_competencia(texto, "Matemática", 3)
    assert "COMPETENCIAS OBLIGATORIAS (USAR SOLO ESTAS)" in ctx
    assert "- Competencia A" in ctx and "- Competencia B" in ctx
    assert "EXACTAMENTE estas 2" in ctx


def test_hu35_una_competencia_sin_cambios():
    ctx = _agent()._construir_contexto_competencia("Competencia A", "Matemática", 3)
    assert "COMPETENCIA OBLIGATORIA (USAR SOLO ESTA)" in ctx


def _rubrica(filas: int) -> str:
    cab = "| Criterio | C — Inicio | B — Proceso | A — Logrado | AD — Destacado |\n|---|---|---|---|---|\n"
    cuerpo = "".join(f"| Criterio {i} | c | b | a | ad |\n" for i in range(1, filas + 1))
    return cab + cuerpo


def _advertencias(contenido, n):
    rep = StructureValidator().validar_unidad_didactica(contenido, num_sesiones=n)
    return [e for e in rep.errores if e.seccion == "RÚBRICA ANALÍTICA"]


def test_hu39_rubrica_con_filas_correctas():
    assert _advertencias(_rubrica(4), 4) == []


def test_hu39_rubrica_con_filas_de_menos():
    adv = _advertencias(_rubrica(3), 6)
    assert len(adv) == 1 and adv[0].tipo == "ADVERTENCIA"


# --- HU-37: registro de áreas/grados usados ---

def test_hu37_registra_areas_y_grados_sin_duplicados():
    from types import SimpleNamespace
    from src.api.services.generation_service import GenerationService

    stats = SimpleNamespace(areas_usadas=[], grados_usados=None)
    for area, grado in [("Matemática", 1), ("Comunicación", 1), ("Matemática", 2), ("Ciencia", 3)]:
        GenerationService._registrar_area_grado(stats, area, grado)
    assert stats.areas_usadas == ["Matemática", "Comunicación", "Ciencia"]
    assert stats.grados_usados == ["1", "2", "3"]


def test_hu37_ignora_valores_vacios():
    from types import SimpleNamespace
    from src.api.services.generation_service import GenerationService

    stats = SimpleNamespace(areas_usadas=[], grados_usados=[])
    GenerationService._registrar_area_grado(stats, "", None)
    assert stats.areas_usadas == [] and stats.grados_usados == []
