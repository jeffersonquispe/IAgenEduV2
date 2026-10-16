"""HU-46: DATOS INFORMATIVOS de la Unidad (perfil institucional + datos del wizard)."""
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import models
from src.api.database import get_db
from src.api.routes import generation
from src.api.routes.auth import get_current_user
from src.api.services.generation_service import GenerationService
from src.core.datos_informativos import (
    construir_datos_informativos_unidad, limpiar_celda, normalizar_datos_unidad,
)

ROOT = Path(__file__).resolve().parents[2]

PERFIL = SimpleNamespace(
    dre_ugel="UGEL Cusco", nombre_institucion="I.E. San Martín",
    coordinacion_pedagogica="Prof. Juana Martínez",
)
VACIO = {"secciones": "", "fecha_inicio": None, "fecha_termino": None}


def _filas(tabla):
    """{item: contenido} de la tabla generada."""
    out = {}
    for linea in tabla.split("\n")[2:]:
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        out[celdas[0].strip("*")] = celdas[1]
    return out


# --- Validación y normalización ---

def test_sin_datos_devuelve_vacios():
    assert normalizar_datos_unidad({}) == VACIO


def test_normaliza_secciones_y_fechas():
    r = normalizar_datos_unidad({"secciones": "  3ro A\ny 3ro B ", "fecha_inicio": "2026-03-16",
                                 "fecha_termino": "2026-05-29"})
    assert r["secciones"] == "3ro A y 3ro B"
    assert r["fecha_inicio"] == date(2026, 3, 16) and r["fecha_termino"] == date(2026, 5, 29)


def test_una_sola_fecha_es_valida():
    assert normalizar_datos_unidad({"fecha_inicio": "2026-03-16"})["fecha_termino"] is None


def test_mismo_dia_de_inicio_y_termino_es_valido():
    normalizar_datos_unidad({"fecha_inicio": "2026-03-16", "fecha_termino": "2026-03-16"})


@pytest.mark.parametrize("params,mensaje", [
    ({"fecha_inicio": "16/03/2026"}, "inicio"),
    ({"fecha_termino": "mañana"}, "término"),
    ({"fecha_inicio": "2026-02-30"}, "inicio"),
    ({"fecha_inicio": 20260316}, "inicio"),
    ({"fecha_inicio": "2026-05-29", "fecha_termino": "2026-03-16"}, "anterior"),
    ({"secciones": "x" * 101}, "largas"),
    ({"secciones": ["3ro A"]}, "texto"),
])
def test_entradas_invalidas(params, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        normalizar_datos_unidad(params)


def test_limpiar_celda_neutraliza_lo_que_rompe_la_tabla():
    assert limpiar_celda("a | b\nc\t d") == "a / b c d"
    assert limpiar_celda(None) == "" and limpiar_celda("   ") == ""
    assert len(limpiar_celda("x" * 500)) == 200


# --- Construcción de la tabla ---

def test_tabla_completa_con_todos_los_campos():
    datos = normalizar_datos_unidad({"secciones": "A y B", "fecha_inicio": "2026-03-16",
                                     "fecha_termino": "2026-05-29"})
    tabla = construir_datos_informativos_unidad(PERFIL, "Matemática", "3°", datos, docente="Ana Pérez")
    assert tabla.startswith("| ITEM | CONTENIDO |\n|------|-----------|")
    assert _filas(tabla) == {
        "DRE / UGEL": "UGEL Cusco",
        "Institución educativa": "I.E. San Martín",
        "Área curricular": "Matemática",
        "Grado y secciones": "3° A y B",
        "Fecha de inicio": "16/03/2026",
        "Fecha de término": "29/05/2026",
        "Coordinación pedagógica": "Prof. Juana Martínez",
        "Docente(s)": "Ana Pérez",
    }


def test_sin_perfil_ni_fechas_solo_incluye_lo_conocido():
    tabla = construir_datos_informativos_unidad(None, "Matemática", "3°", VACIO)
    assert _filas(tabla) == {"Área curricular": "Matemática", "Grado y secciones": "3°"}


def test_perfil_parcial_omite_los_campos_vacios():
    perfil = SimpleNamespace(dre_ugel="UGEL Cusco", nombre_institucion=None, coordinacion_pedagogica="")
    filas = _filas(construir_datos_informativos_unidad(perfil, "Arte", "1°", VACIO))
    assert "DRE / UGEL" in filas
    assert "Institución educativa" not in filas and "Coordinación pedagógica" not in filas


def test_tabla_vacia_si_no_hay_ningun_dato():
    assert construir_datos_informativos_unidad(None, "", "", VACIO) == ""


def test_un_valor_malicioso_del_perfil_no_rompe_la_tabla():
    perfil = SimpleNamespace(dre_ugel="UGEL | Cusco\n| FALSA | fila |", nombre_institucion=None,
                             coordinacion_pedagogica=None)
    tabla = construir_datos_informativos_unidad(perfil, "Arte", "1°", VACIO)
    for linea in tabla.split("\n")[2:]:
        assert linea.count("|") == 3          # exactamente 2 celdas por fila


# --- Flujo del servicio ---

UNIDAD_MD = (
    "| ITEM | CONTENIDO |\n|------|-----------|\n"
    "| **II. SITUACIÓN SIGNIFICATIVA** | Una situación significativa de prueba suficientemente larga. |\n"
    "| **III. PROPÓSITOS DE APRENDIZAJE** | Competencias: A. Criterios de evaluación: x. |\n"
)


def _db(perfil=None, plantilla=None):
    db = MagicMock()

    def consulta(modelo):
        q = MagicMock()
        q.filter.return_value.first.return_value = (
            perfil if modelo is models.InstitutionProfile
            else plantilla if modelo is models.DocumentTemplate else None)
        return q
    db.query.side_effect = consulta
    return db


def _generar(params, perfil=None, plantilla=None, full_name="Ana Pérez"):
    gen = MagicMock()
    gen.construir_prompt_unidad.return_value = "P"
    gen.bedrock.invocar_stream.return_value = iter([UNIDAD_MD])
    coord = MagicMock()
    coord.validar_y_formatear_unidad.return_value = (UNIDAD_MD, None)
    db = _db(perfil, plantilla)
    svc = GenerationService()
    svc._save_version = MagicMock()
    svc._save_pipeline_run = MagicMock()
    svc._plantilla_activa = MagicMock(return_value=plantilla)
    user = SimpleNamespace(id="u", full_name=full_name, stats=None)
    with patch("src.agents.generator_agent.GeneratorAgent", return_value=gen), \
         patch("src.agents.coordinator.get_coordinator", return_value=coord):
        eventos = [json.loads(l[6:]) for l in svc.generar_unidad_stream_events(params, user, db)
                   if l.startswith("data: ")]
    return eventos, db


def test_la_unidad_incluye_datos_informativos_como_primera_seccion():
    params = {"area": "Matemática", "grado": "3°", "competencias": ["A"], "secciones": "3ro A y 3ro B",
              "fecha_inicio": "2026-03-16", "fecha_termino": "2026-05-29"}
    eventos, db = _generar(params, perfil=PERFIL)
    final = eventos[-1]
    assert "error" not in final
    assert list(final)[:4] == ["done", "id", "version", "datos_informativos"]    # primera sección del documento
    filas = _filas(final["datos_informativos"])
    assert filas["DRE / UGEL"] == "UGEL Cusco" and filas["Docente(s)"] == "Ana Pérez"
    assert filas["Grado y secciones"] == "3° 3ro A y 3ro B" and filas["Fecha de inicio"] == "16/03/2026"
    guardado = db.add.call_args.args[0]
    assert next(iter(guardado.content)) == "datos_informativos"


def test_sin_perfil_la_unidad_igual_trae_area_y_grado():
    eventos, _ = _generar({"area": "Arte", "grado": "1°", "competencias": ["A"]}, perfil=None, full_name=None)
    assert _filas(eventos[-1]["datos_informativos"]) == {"Área curricular": "Arte", "Grado y secciones": "1°"}


def test_con_plantilla_institucional_no_se_agrega_la_seccion():
    plantilla = {"tablas": []}
    eventos, db = _generar({"area": "Arte", "grado": "1°", "competencias": ["A"]},
                           perfil=PERFIL, plantilla=plantilla)
    assert "datos_informativos" not in eventos[-1]


def test_el_servicio_corta_con_error_si_las_fechas_son_invalidas():
    eventos, db = _generar({"area": "Arte", "grado": "1°", "competencias": ["A"],
                            "fecha_inicio": "2026-05-29", "fecha_termino": "2026-03-16"})
    assert len(eventos) == 1 and "anterior" in eventos[0]["error"]
    db.add.assert_not_called()


# --- Endpoints: 422 antes de empezar ---

@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(generation.router)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u", stats=None)
    return TestClient(app)


@pytest.mark.parametrize("ruta", ["/generate/unidad/stream", "/generate/unidad/jobs"])
def test_endpoints_de_unidad_responden_422_con_datos_invalidos(cliente, ruta):
    r = cliente.post(ruta, json={"competencias": ["A"], "fecha_inicio": "2026-05-29",
                                 "fecha_termino": "2026-03-16"})
    assert r.status_code == 422 and "anterior" in r.json()["detail"]


# --- Exportación: la sección llega al PDF y al DOCX ---

def test_pdf_y_docx_incluyen_los_datos_informativos(tmp_path):
    from pypdf import PdfReader
    from docx import Document
    from src.core.pdf_generator import generar_pdf_unidad

    tabla = construir_datos_informativos_unidad(PERFIL, "Matemática", "3°", VACIO, docente="Ana Pérez")
    contenido = {"titulo": "U", "datos_informativos": tabla, "situacion_significativa": "Situación de prueba."}

    salida = tmp_path / "u.pdf"
    generar_pdf_unidad(contenido, str(salida))
    texto = " ".join(p.extract_text() or "" for p in PdfReader(str(salida)).pages)
    assert "DATOS INFORMATIVOS" in texto and "UGEL Cusco" in texto and "Juana" in texto

    from src.api.routes.export import _filtrar_contenido_exportable
    assert "datos_informativos" in _filtrar_contenido_exportable(contenido)


# --- Frontend (verificación estática) ---

def test_wizard_ofrece_los_campos_opcionales_y_solo_envia_los_completados():
    src = (ROOT / "frontend/src/components/GenerationWizard.jsx").read_text(encoding="utf-8")
    for nombre in ("secciones", "fecha_inicio", "fecha_termino"):
        assert f'name="{nombre}"' in src
        assert f"payload.{nombre} =" in src
    assert 'type="date"' in src
    assert "errorFechas(" in src


def test_el_editor_ya_muestra_datos_informativos_para_la_unidad():
    src = (ROOT / "frontend/src/lib/documento.js").read_text(encoding="utf-8")
    bloque = src[src.index("const CONTENT_FIELDS"):src.index("]", src.index("const CONTENT_FIELDS"))]
    assert "'datos_informativos'" in bloque
