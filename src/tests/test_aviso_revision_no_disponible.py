"""Cuando la revisión pedagógica con IA no se puede ejecutar, el documento lo dice.

Antes, un fallo de la IA (p. ej. el modelo retirado por AWS) devolvía en silencio "APROBADO, 70" y
el documento parecía revisado. Ahora el resultado neutro se marca con `revision_disponible=False` y el
agente validador lo convierte en una ADVERTENCIA visible en el aviso del Editor.
"""
from unittest.mock import MagicMock

import pytest

from src.agents.coordinator import PipelineMetrics
from src.agents.validator_agent import (
    MENSAJE_REVISION_NO_DISPONIBLE, SECCION_REVISION_AUTOMATICA, ValidatorAgent,
)
from src.validators.content_validator import ContentValidator
from src.validators.revalidacion import revalidar_contenido
from src.validators.structure_validator import StructureValidator

JSON_OK = '{"calificacion_general": "APROBADO", "puntaje": 88, "errores": [], "sugerencias": ["Todo bien"]}'


def _unidad_valida():
    filas = "".join(f"| **{s}** | contenido de prueba para {s} |\n" for s in StructureValidator.SECCIONES_UNIDAD)
    return "| ITEM | CONTENIDO |\n|---|---|\n" + filas


def _sesion_valida():
    filas = "".join(f"| **{s}** | contenido de prueba para {s} |\n" for s in StructureValidator.SECCIONES_SESION)
    return "| ITEM | CONTENIDO |\n|---|---|\n" + filas + "INICIO DESARROLLO CIERRE"


def _agente(resultado=None, falla=None, usar_llm=True):
    agente = ValidatorAgent(usar_validacion_llm=usar_llm)
    if usar_llm:
        agente.content_validator = MagicMock()
        if falla:
            agente.content_validator.validar.side_effect = falla
        else:
            agente.content_validator.validar.return_value = resultado
    return agente


def _avisos(reporte):
    return [e for e in reporte.errores if e.seccion == SECCION_REVISION_AUTOMATICA]


NO_DISPONIBLE = {"calificacion_general": "APROBADO", "puntaje": 70, "errores": [], "sugerencias": ["x"],
                 "revision_disponible": False}
DISPONIBLE = {"calificacion_general": "APROBADO", "puntaje": 90, "errores": [], "sugerencias": [],
              "revision_disponible": True}


# --- ContentValidator marca cuándo no pudo evaluar ---

def _validador(bedrock):
    v = ContentValidator.__new__(ContentValidator)
    v.prompt_manager = MagicMock()
    v.prompt_manager.cargar.return_value = "PROMPT"
    v.bedrock = bedrock
    return v


def test_una_evaluacion_real_se_marca_como_disponible():
    bedrock = MagicMock()
    bedrock.invocar_validacion.return_value = JSON_OK
    r = _validador(bedrock).validar("texto")
    assert r["revision_disponible"] is True and r["puntaje"] == 88


def test_si_la_ia_falla_el_resultado_neutro_se_marca_como_no_disponible():
    bedrock = MagicMock()
    bedrock.invocar_validacion.side_effect = RuntimeError("This model version has reached the end of its life")
    r = _validador(bedrock).validar("texto")
    assert r["revision_disponible"] is False and r["calificacion_general"] == "APROBADO" and r["puntaje"] == 70
    assert "end of its life" in r["sugerencias"][0]


def test_una_respuesta_ilegible_tambien_se_marca_como_no_disponible():
    bedrock = MagicMock()
    bedrock.invocar_validacion.return_value = "```json\n{\"calificacion_general\": \"RECHAZADO\", \"pun"
    assert _validador(bedrock).validar("texto")["revision_disponible"] is False


# --- El agente lo convierte en una advertencia ---

@pytest.mark.parametrize("tipo,validar,contenido", [
    ("unidad", "validar_unidad", _unidad_valida), ("sesion", "validar_sesion", _sesion_valida)])
def test_la_revision_no_disponible_agrega_una_advertencia_visible(tipo, validar, contenido):
    reporte = getattr(_agente(NO_DISPONIBLE), validar)(contenido())
    avisos = _avisos(reporte)
    assert len(avisos) == 1 and avisos[0].tipo == "ADVERTENCIA" and avisos[0].mensaje == MENSAJE_REVISION_NO_DISPONIBLE
    assert not reporte.tiene_errores_criticos                       # avisa, pero no bloquea nada


@pytest.mark.parametrize("validar,contenido", [("validar_unidad", _unidad_valida), ("validar_sesion", _sesion_valida)])
def test_una_excepcion_del_validador_tambien_genera_el_aviso(validar, contenido):
    reporte = getattr(_agente(falla=RuntimeError("fallo inesperado")), validar)(contenido())
    assert len(_avisos(reporte)) == 1


@pytest.mark.parametrize("validar,contenido", [("validar_unidad", _unidad_valida), ("validar_sesion", _sesion_valida)])
def test_con_una_revision_real_no_hay_aviso(validar, contenido):
    assert _avisos(getattr(_agente(DISPONIBLE), validar)(contenido())) == []


def test_si_la_validacion_con_ia_esta_desactivada_a_proposito_no_se_avisa():
    reporte = _agente(usar_llm=False).validar_unidad(_unidad_valida())
    assert _avisos(reporte) == []


def test_si_la_estructura_falla_ni_se_llama_a_la_ia_ni_se_avisa():
    agente = _agente(NO_DISPONIBLE)
    reporte = agente.validar_unidad("| ITEM | CONTENIDO |\n|---|---|\n| **TÍTULO** | Unidad de prueba con texto suficiente para pasar el mínimo de largo |")
    assert reporte.tiene_errores_criticos
    agente.content_validator.validar.assert_not_called()
    assert _avisos(reporte) == []


def test_los_errores_que_reporta_la_ia_llegan_al_reporte():
    """Regresión: un import absoluto dentro del agente fallaba fuera de producción y descartaba estos errores."""
    resultado = {**DISPONIBLE, "errores": [
        {"criterio": "COHERENCIA", "tipo": "ADVERTENCIA", "descripcion": "Los criterios no se alinean con las sesiones"}]}
    reporte = _agente(resultado).validar_unidad(_unidad_valida())
    assert any(e.mensaje == "Los criterios no se alinean con las sesiones" and e.tipo == "ADVERTENCIA"
               for e in reporte.errores)


# --- Efecto en las métricas, el aviso del Editor y la revalidación ---

def test_la_advertencia_aparece_en_el_detalle_sin_invalidar_el_documento():
    reporte = _agente(NO_DISPONIBLE).validar_unidad(_unidad_valida())
    m = PipelineMetrics()
    m.aplicar_reporte(reporte)
    resumen = m.resumen_validacion()
    assert resumen["es_valido"] is True and resumen["errores_advertencia"] == 1 and resumen["errores_criticos"] == 0
    assert resumen["detalle"][0]["seccion"] == SECCION_REVISION_AUTOMATICA
    assert resumen["detalle"][0]["mensaje"] == MENSAJE_REVISION_NO_DISPONIBLE
    assert resumen["puntaje_validacion"] == 90                       # una advertencia resta 10


def test_la_revalidacion_al_editar_conserva_el_aviso_porque_no_se_puede_recalcular_sin_la_ia():
    previo = [{"tipo": "ADVERTENCIA", "categoria": "CONTENIDO", "mensaje": MENSAJE_REVISION_NO_DISPONIBLE,
               "seccion": SECCION_REVISION_AUTOMATICA}]
    contenido = {"situacion_significativa": "x", "propositos_de_aprendizaje": "x", "valores_y_enfoques_transversales": "x",
                 "secuencia_de_sesiones": "x", "materiales_basicos": "x"}
    reporte = revalidar_contenido(contenido, "unidad", previo)
    assert [e.mensaje for e in reporte.errores] == [MENSAJE_REVISION_NO_DISPONIBLE]


def test_el_mensaje_es_comprensible_para_un_docente():
    assert "revisión pedagógica automática" in MENSAJE_REVISION_NO_DISPONIBLE
    assert "estructura" in MENSAJE_REVISION_NO_DISPONIBLE and "Revísalo" in MENSAJE_REVISION_NO_DISPONIBLE
    assert "Traceback" not in MENSAJE_REVISION_NO_DISPONIBLE and "Exception" not in MENSAJE_REVISION_NO_DISPONIBLE
