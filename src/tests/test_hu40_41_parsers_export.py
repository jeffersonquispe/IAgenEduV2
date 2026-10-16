"""HU-40 / HU-41: 'Materiales Básicos' (Unidad) y 'Reto' (Sesión) deben sobrevivir
parser -> exportación PDF/DOCX, y el Editor debe conocerlos."""
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.api.services.content_parsers import (
    SesionContentParser, UnidadContentParser, extraer_fila_por_encabezado,
)

ROOT = Path(__file__).resolve().parents[2]

UNIDAD_MD = """| ITEM | CONTENIDO |
|------|-----------|
| **II. SITUACIÓN SIGNIFICATIVA** | Los estudiantes enfrentan un reto real. |
| **III. PROPÓSITOS DE APRENDIZAJE** | Competencias: A. Criterios de evaluación: x. |
| **MATERIALES BÁSICOS** | Para el docente: proyector, guías.
Para el estudiante: cuaderno, computadora. |
| **EVIDENCIAS DE APRENDIZAJE** | Un producto final. |
"""

SESION_MD = """| ITEM | CONTENIDO |
|------|-----------|
| **DATOS INFORMATIVOS** | Colegio X, 2° A |
| **SITUACIÓN SIGNIFICATIVA** | Situación de prueba. |
| **RETO** | ¿Cómo podemos resolver el problema de la comunidad? |
| **PROPÓSITOS DE APRENDIZAJE** | Competencia A |
| **SECUENCIA DIDÁCTICA** | INICIO 10 min. DESARROLLO 60 min. CIERRE 20 min. |
| **MATERIALES Y RECURSOS** | Pizarra |
"""


# --- extraer_fila_por_encabezado ---

def test_fila_simple():
    assert extraer_fila_por_encabezado(SESION_MD, "RETO").startswith("¿Cómo podemos")


def test_fila_multilinea_incluye_continuacion():
    texto = extraer_fila_por_encabezado(UNIDAD_MD, "MATERIALES")
    assert "Para el docente: proyector" in texto
    assert "Para el estudiante: cuaderno" in texto
    assert "EVIDENCIAS" not in texto


def test_fila_inexistente_o_vacia():
    assert extraer_fila_por_encabezado(SESION_MD, "NO EXISTE") == ""
    assert extraer_fila_por_encabezado("", "RETO") == ""


# --- Parsers ---

def test_unidad_parser_extrae_materiales_basicos():
    doc = UnidadContentParser().parsear(UNIDAD_MD, area="Matemática")
    assert "Para el docente" in doc["materiales_basicos"]
    assert "Para el estudiante" in doc["materiales_basicos"]


def test_unidad_parser_sin_materiales_devuelve_cadena_vacia():
    doc = UnidadContentParser().parsear(UNIDAD_MD.replace("MATERIALES BÁSICOS", "OTRA"), area="X")
    assert doc["materiales_basicos"] == ""


def test_sesion_parser_extrae_reto_separado_de_la_situacion():
    doc = SesionContentParser().parsear(SESION_MD, tema_sesion="Tema")
    assert doc["reto"] == "¿Cómo podemos resolver el problema de la comunidad?"
    assert "¿Cómo podemos" not in doc["datos_informativos"]
    assert "Situación de prueba" in doc["datos_informativos"]


def test_sesion_parser_no_confunde_palabras_que_contienen_reto():
    """'COMPLETO' contiene 'RETO'; no debe abrir la sección de reto."""
    md = SESION_MD.replace(
        "| **RETO** | ¿Cómo podemos resolver el problema de la comunidad? |\n", ""
    )
    md += "\nEl trabajo completo se entrega al final.\n"
    doc = SesionContentParser().parsear(md, tema_sesion="Tema")
    assert doc["reto"] == ""


def test_sesion_parser_reto_en_texto_plano():
    md = "DATOS INFORMATIVOS\nColegio X\nRETO\n¿Cómo lo resolvemos?\nPROPÓSITOS\nA\n"
    doc = SesionContentParser().parsear(md, tema_sesion="T")
    assert doc["reto"] == "¿Cómo lo resolvemos?"


# --- Exportación (integración parser -> filtro -> PDF / DOCX) ---

def test_filtro_de_exportacion_conserva_reto_y_materiales():
    from src.api.routes.export import _filtrar_contenido_exportable
    out = _filtrar_contenido_exportable(
        {"titulo": "T", "reto": "¿Cómo?", "materiales_basicos": "Docente: x", "done": True, "id": "1"}
    )
    assert out["reto"] == "¿Cómo?" and out["materiales_basicos"] == "Docente: x"
    assert "done" not in out and "id" not in out


def _texto_pdf(ruta) -> str:
    from pypdf import PdfReader
    return " ".join(pg.extract_text() or "" for pg in PdfReader(str(ruta)).pages)


def test_pdf_unidad_incluye_materiales_basicos(tmp_path):
    from src.core.pdf_generator import generar_pdf_unidad
    doc = UnidadContentParser().parsear(UNIDAD_MD, area="Matemática")
    salida = tmp_path / "u.pdf"
    generar_pdf_unidad({"titulo": "U", "materiales_basicos": doc["materiales_basicos"]}, str(salida))
    texto = _texto_pdf(salida)
    assert "MATERIALES BASICOS" in texto.upper().replace("Á", "A")
    assert "proyector" in texto and "cuaderno" in texto


def test_pdf_sesion_incluye_reto(tmp_path):
    from src.core.pdf_generator import generar_pdf_sesion
    doc = SesionContentParser().parsear(SESION_MD, tema_sesion="Tema")
    salida = tmp_path / "s.pdf"
    generar_pdf_sesion({"titulo": "S", "reto": doc["reto"]}, str(salida))
    texto = _texto_pdf(salida)
    assert "RETO" in texto
    assert "problema de la comunidad" in texto


@pytest.mark.asyncio
async def test_endpoint_docx_exporta_reto_y_materiales():
    """Integración de la ruta /export/docx sin plantilla institucional."""
    from docx import Document
    from src.api.routes.export import export_docx

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None  # sin plantilla
    user = SimpleNamespace(id="u1", stats=SimpleNamespace(exportaciones_docx=0))
    payload = {"titulo": "Sesion Test", "reto": "¿Cómo lo resolvemos?",
               "datos_informativos": "Colegio X", "done": True}

    resp = await export_docx(data=payload, db=db, current_user=user)
    textos = [p.text for p in Document(resp.path).paragraphs]
    assert "II. RETO" in textos                  # encabezado numerado de la sección (HU-23)
    assert "¿Cómo lo resolvemos?" in textos      # contenido
    assert user.stats.exportaciones_docx == 1


# --- Editor (React): verificación estática del archivo ---

def test_editor_conoce_los_campos_nuevos():
    src = (ROOT / "frontend/src/lib/documento.js").read_text(encoding="utf-8")
    bloque = src[src.index("const CONTENT_FIELDS"):src.index("]", src.index("const CONTENT_FIELDS"))]
    for campo in ("reto", "materiales_basicos"):
        assert f"'{campo}'" in bloque
    assert re.search(r"reto:\s*\"RETO\"", src)
    assert re.search(r"materiales_basicos:\s*\"MATERIALES BÁSICOS\"", src)
