"""HU-30: el resultado de validación viaja con el documento y el Editor lo usa
para pedir confirmación antes de exportar con errores críticos."""
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.agents.coordinator import AgentCoordinator, PipelineMetrics
from src.api.services.generation_service import GenerationService
from src.validators.structure_validator import ValidationError, ValidationReport

ROOT = Path(__file__).resolve().parents[2]


def _reporte(*errores):
    return ValidationReport(errores=[ValidationError(t, "ESTRUCTURA", m, s) for t, m, s in errores])


CRITICO = ("CRITICO", "Falta la sección requerida: RETO", "RETO")
ADVERT = ("ADVERTENCIA", "Las sesiones 1 y 2 tratan el mismo tema", "SECUENCIA DE SESIONES")


# --- PipelineMetrics ---

def test_aplicar_reporte_copia_conteos_y_detalle():
    m = PipelineMetrics()
    m.aplicar_reporte(_reporte(CRITICO, ADVERT))
    assert (m.errores_criticos, m.errores_advertencia) == (1, 1)
    assert m.puntaje_validacion == 65
    assert [d["tipo"] for d in m.detalle_validacion] == ["CRITICO", "ADVERTENCIA"]
    assert m.detalle_validacion[0]["seccion"] == "RETO"


def test_aplicar_reporte_reemplaza_el_estado_previo():
    m = PipelineMetrics()
    m.aplicar_reporte(_reporte(CRITICO))
    m.aplicar_reporte(_reporte())
    assert m.errores_criticos == 0 and m.detalle_validacion == []


def test_resumen_validacion_es_serializable_y_refleja_validez():
    m = PipelineMetrics()
    m.aplicar_reporte(_reporte(CRITICO))
    r = m.resumen_validacion()
    json.dumps(r)
    assert r["es_valido"] is False and r["errores_criticos"] == 1
    m.aplicar_reporte(_reporte(ADVERT))
    assert m.resumen_validacion()["es_valido"] is True      # las advertencias no invalidan


# --- Coordinador ---

def _coordinador(validaciones, corregido="contenido corregido"):
    c = AgentCoordinator.__new__(AgentCoordinator)
    c.max_correcciones = 1
    c.validator = MagicMock()
    c.validator.validar_sesion.side_effect = validaciones
    c.validator.validar_unidad.side_effect = validaciones
    c.generator = MagicMock()
    c.generator.corregir.return_value = corregido
    c.formatter = MagicMock()
    c.formatter.formatear.side_effect = lambda x: x
    return c


def test_sesion_revalida_tras_corregir_y_limpia_los_criticos():
    c = _coordinador([_reporte(CRITICO), _reporte()])
    _, m = c.validar_y_formatear_sesion("texto", grado="1")
    assert c.validator.validar_sesion.call_count == 2
    assert m.errores_criticos == 0 and m.detalle_validacion == []
    assert m.correcciones_aplicadas == 1


def test_sesion_conserva_el_error_si_la_correccion_no_lo_arregla():
    c = _coordinador([_reporte(CRITICO), _reporte(CRITICO)])
    _, m = c.validar_y_formatear_sesion("texto", grado="1")
    assert m.errores_criticos == 1 and m.resumen_validacion()["es_valido"] is False


def test_sesion_sin_errores_no_corrige_ni_revalida():
    c = _coordinador([_reporte(ADVERT)])
    _, m = c.validar_y_formatear_sesion("texto", grado="1")
    c.generator.corregir.assert_not_called()
    assert c.validator.validar_sesion.call_count == 1
    assert m.errores_advertencia == 1


def test_unidad_actualiza_advertencias_tras_corregir():
    c = _coordinador([_reporte(CRITICO, ADVERT), _reporte()])
    _, m = c.validar_y_formatear_unidad("texto", "Matemática", 1, num_sesiones=3)
    assert m.errores_criticos == 0 and m.errores_advertencia == 0


# --- Servicio: la validación viaja en el evento final y se guarda ---

SESION_MD = (
    "| ITEM | CONTENIDO |\n|------|-----------|\n"
    "| **DATOS INFORMATIVOS** | Colegio X |\n| **RETO** | ¿Cómo? |\n"
    "| **SECUENCIA DIDÁCTICA** | INICIO DESARROLLO CIERRE |\n"
)


def _ejecutar_sesion(metricas):
    gen = MagicMock()
    gen.construir_prompt_sesion.return_value = "P"
    gen.bedrock.invocar_stream.return_value = iter([SESION_MD])
    coord = MagicMock()
    coord.validar_y_formatear_sesion.return_value = (SESION_MD, metricas)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    user = SimpleNamespace(id="u", stats=None)
    svc = GenerationService()
    svc._save_version = MagicMock()
    svc._save_pipeline_run = MagicMock()
    with patch("src.agents.generator_agent.GeneratorAgent", return_value=gen), \
         patch("src.agents.coordinator.get_coordinator", return_value=coord):
        eventos = [json.loads(l[6:]) for l in svc.generar_sesion_stream_events(
            {"area": "Comunicación", "grado": "1°", "tema": "T"}, user, db) if l.startswith("data: ")]
    return eventos[-1], db


def test_evento_final_incluye_validacion_y_se_guarda_con_el_documento():
    m = PipelineMetrics()
    m.aplicar_reporte(_reporte(CRITICO))
    final, db = _ejecutar_sesion(m)
    assert final["validacion"]["es_valido"] is False
    assert final["validacion"]["detalle"][0]["seccion"] == "RETO"
    guardado = db.add.call_args.args[0]
    assert guardado.content["validacion"]["errores_criticos"] == 1


def test_sin_metricas_no_se_agrega_validacion():
    final, db = _ejecutar_sesion(None)          # p. ej. modo "solo_generador"
    assert "validacion" not in final


def test_validacion_no_se_exporta():
    from src.api.routes.export import _filtrar_contenido_exportable
    out = _filtrar_contenido_exportable({"titulo": "T", "reto": "x", "validacion": {"es_valido": False}})
    assert "validacion" not in out


# --- Editor (verificación estática) ---

def test_editor_pide_confirmacion_y_no_exporta_la_validacion():
    editor = (ROOT / "frontend/src/pages/Editor.jsx").read_text(encoding="utf-8")
    src = (ROOT / "frontend/src/lib/documento.js").read_text(encoding="utf-8")
    # Con errores críticos se pide confirmación explícita (diálogo propio; sin Toaster cae a window.confirm).
    assert "criticos.length > 0" in src and "await confirmar(" in src and "Exportar de todas formas" in src
    assert "exportarDocumento(document, format, criticos)" in editor      # el Editor entrega los críticos
    assert "window.confirm" in (ROOT / "frontend/src/lib/notify.js").read_text(encoding="utf-8")
    bloque = src[src.index("const CONTENT_FIELDS"):src.index("]", src.index("const CONTENT_FIELDS"))]
    assert "'validacion'" not in bloque       # no se renderiza como sección ni se exporta
    assert re.search(r"role=\"alert\"", editor)
