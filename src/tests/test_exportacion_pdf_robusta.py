"""Exportación a PDF y parseo de la Unidad: orden, tildes, negritas, tablas degeneradas y texto sin recortar.

Reproduce un PDF real que salió con páginas en blanco, la sección "Datos informativos" al final,
títulos sin tildes, `**` literales, textos cortados a media palabra y un `--` colgando.
"""
import pytest
from pypdf import PdfReader

from src.api.routes.export import _filtrar_contenido_exportable
from src.api.services.content_parsers import UnidadContentParser
from src.core.markdown_table import aplanar_tabla_degenerada, parse_markdown_table
from src.core.pdf_generator import generar_pdf_unidad

TEXTO_LARGO = ("Competencias: COMPETENCIA 12. Investiga usando métodos científicos para construir conocimientos. " * 40).strip()


def _paginas(ruta):
    return [(p.extract_text() or "") for p in PdfReader(str(ruta)).pages]


@pytest.fixture
def unidad():
    # Orden "malo" a propósito: así lo enviaba el frontend (datos informativos casi al final).
    return {
        "titulo": "Unidad de prueba",
        "situacion_significativa": "Una situación.",
        "propositos_de_aprendizaje": "| ITEM | CONTENIDO |\n|---|---|\n| **" + TEXTO_LARGO + "** | |",
        "rubrica_unidad": "| Criterio | Inicio |\n|---|---|\n| **Identifica** | Menciona |",
        "datos_informativos": "| ITEM | CONTENIDO |\n|---|---|\n| **Institución educativa** | Colegio X |",
        "materiales_basicos": "Para el docente: proyector.",
    }


# --- Orden y títulos ---

def test_el_exportador_pone_los_datos_informativos_primero(unidad):
    claves = [k for k in _filtrar_contenido_exportable(unidad) if k != "titulo"]
    assert claves[0] == "datos_informativos"
    assert claves.index("situacion_significativa") < claves.index("propositos_de_aprendizaje") < claves.index("materiales_basicos")


def test_los_titulos_del_pdf_llevan_tilde_y_van_en_orden(unidad, tmp_path):
    ruta = tmp_path / "u.pdf"
    generar_pdf_unidad(_filtrar_contenido_exportable(unidad), str(ruta))
    texto = "\n".join(_paginas(ruta))
    assert "DATOS INFORMATIVOS" in texto and "SITUACIÓN SIGNIFICATIVA" in texto and "PROPÓSITOS DE APRENDIZAJE" in texto
    assert "SITUACION" not in texto and "PROPOSITOS" not in texto
    assert texto.index("DATOS INFORMATIVOS") < texto.index("SITUACIÓN SIGNIFICATIVA") < texto.index("PROPÓSITOS DE APRENDIZAJE")


def test_el_pdf_no_muestra_marcadores_de_negrita(unidad, tmp_path):
    ruta = tmp_path / "u.pdf"
    generar_pdf_unidad(_filtrar_contenido_exportable(unidad), str(ruta))
    texto = "\n".join(_paginas(ruta))
    assert "**" not in texto
    assert "Institución educativa" in texto and "Identifica" in texto


# --- Tabla con toda la información en una celda (resultado de refinar con IA) ---

def test_tabla_de_una_sola_celda_no_se_considera_tabla():
    md = "| ITEM | CONTENIDO |\n|---|---|\n| **Competencias COMPETENCIA 12 ... Instrumento: Rúbrica.** | |"
    assert parse_markdown_table(md) is None
    assert aplanar_tabla_degenerada(md) == "**Competencias COMPETENCIA 12 ... Instrumento: Rúbrica.**"


def test_una_tabla_real_sigue_siendo_tabla():
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    assert parse_markdown_table(md) == [["A", "B"], ["1", "2"], ["3", "4"]]
    assert aplanar_tabla_degenerada(md) is None


def test_la_celda_gigante_no_deja_paginas_en_blanco(unidad, tmp_path):
    ruta = tmp_path / "u.pdf"
    generar_pdf_unidad(_filtrar_contenido_exportable(unidad), str(ruta))
    paginas = _paginas(ruta)
    encabezado = "PLANIFICACIÓN EDUCATIVA AI - MINEDU"
    for i, p in enumerate(paginas, 1):
        contenido = p.replace(encabezado, "").replace("ITEM CONTENIDO", "")
        contenido = "\n".join(l for l in contenido.splitlines() if not l.strip().startswith("Página "))
        assert contenido.strip(), f"la página {i} quedó en blanco: {p!r}"
    assert len(paginas) <= 3
    assert "PROPÓSITOS DE APRENDIZAJE" in "\n".join(paginas)


def test_una_tabla_legitima_demasiado_alta_cae_a_texto_sin_paginas_en_blanco(tmp_path):
    filas = "\n".join(f"| fila {i} | {'texto muy largo ' * 400} |" for i in range(2))
    datos = {"titulo": "T", "rubrica_unidad": "| Criterio | Detalle |\n|---|---|\n" + filas}
    ruta = tmp_path / "u.pdf"
    generar_pdf_unidad(datos, str(ruta))
    paginas = _paginas(ruta)
    assert all(len(p.replace("PLANIFICACIÓN EDUCATIVA AI - MINEDU", "").strip()) > 40 for p in paginas)


# --- Parser de la Unidad ---

def _crudo(n_sesiones=6, actividades=2500):
    sesiones = "".join(
        f"| **SECUENCIA DE SESIONES** | Sesión {i}: Título: Tema {i} Criterio de evaluación: Criterio {i} "
        f"Principales actividades: {'actividad larga ' * (actividades // 16)}FIN{i} |\n"
        for i in range(1, n_sesiones + 1)
    )
    return (
        "| **SITUACIÓN SIGNIFICATIVA** | Texto de la situación. -- |\n"
        "| **PROPÓSITOS DE APRENDIZAJE** | Competencias: A. Instrumento: Rúbrica. -- |\n"
        + sesiones
    )


def test_las_actividades_largas_no_se_recortan_a_media_palabra():
    out = UnidadContentParser().parsear(_crudo(n_sesiones=2), area="Ciencia", num_sesiones=2)
    assert "FIN1" in out["secuencia_de_sesiones"] and "FIN2" in out["secuencia_de_sesiones"]


def test_se_extraen_tantas_sesiones_como_se_pidieron():
    out = UnidadContentParser().parsear(_crudo(n_sesiones=6, actividades=200), area="Ciencia", num_sesiones=6)
    for i in range(1, 7):
        assert f"Sesión {i}:" in out["secuencia_de_sesiones"], i


def test_el_parser_quita_los_guiones_finales_del_separador():
    out = UnidadContentParser().parsear(_crudo(n_sesiones=1, actividades=100), area="Ciencia", num_sesiones=1)
    assert not out["situacion_significativa"].endswith("--")
    assert not out["propositos_de_aprendizaje"].endswith("--")
