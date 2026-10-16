"""HU-44: biblioteca de ejemplos de Unidad y Sesión dentro de la plataforma."""
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.database import get_db
from src.api.routes import data
from src.api.routes.auth import get_current_user
from src.api.routes.export import _CONTENT_FIELDS
from src.core import ejemplos
from src.core.docx_export import _bloques_de_sesion, generar_docx
from src.core.markdown_table import parse_markdown_table
from src.core.matriz_axiologica import contar_filas_matriz, extraer_matriz
from src.core.pdf_generator import generar_pdf_sesion, generar_pdf_unidad

ROOT = Path(__file__).resolve().parents[2]


def _escribir(carpeta, nombre, contenido):
    (carpeta / nombre).write_text(contenido if isinstance(contenido, str) else json.dumps(contenido),
                                  encoding="utf-8")


def _valido(**extra):
    return {"id": "ej-1", "tipo": "unidad", "titulo": "Un ejemplo", "descripcion": "d",
            "content": {"situacion_significativa": "texto"}, **extra}


# --- El cargador ---

def test_lista_unidad_y_sesion_con_solo_el_resumen():
    lista = ejemplos.listar_ejemplos()
    assert [e["tipo"] for e in lista] == ["unidad", "sesion"]           # unidades primero
    assert all(set(e) == {"id", "tipo", "titulo", "descripcion"} for e in lista)
    assert all("content" not in e for e in lista)


def test_obtiene_el_ejemplo_completo_por_id():
    e = ejemplos.obtener_ejemplo("unidad-ept-programacion")
    assert e["tipo"] == "unidad" and e["content"]["situacion_significativa"]
    assert ejemplos.obtener_ejemplo("sesion-ept-programacion")["tipo"] == "sesion"


@pytest.mark.parametrize("peligroso", [
    "no-existe", "", "../../.env", "..\\..\\.env", "unidad-ept-programacion/../../x",
    "unidad_ept_programacion", "UNIDAD-EPT-PROGRAMACION",
])
def test_un_id_desconocido_o_con_rutas_no_devuelve_nada(peligroso):
    assert ejemplos.obtener_ejemplo(peligroso) is None


def test_un_ejemplo_nuevo_aparece_sin_tocar_codigo(tmp_path):
    assert ejemplos.listar_ejemplos(tmp_path) == []
    _escribir(tmp_path, "nuevo.json", _valido())
    assert [e["id"] for e in ejemplos.listar_ejemplos(tmp_path)] == ["ej-1"]
    assert ejemplos.obtener_ejemplo("ej-1", tmp_path)["content"] == {"situacion_significativa": "texto"}


def test_un_directorio_inexistente_da_lista_vacia(tmp_path):
    assert ejemplos.listar_ejemplos(tmp_path / "no-existe") == []


@pytest.mark.parametrize("malo", [
    "esto no es json",
    "[1, 2, 3]",
    {**_valido(), "tipo": "examen"},
    {**_valido(), "id": ""},
    {**_valido(), "titulo": "   "},
    {**_valido(), "content": {}},
    {**_valido(), "content": "texto"},
    {**_valido(), "content": {"situacion_significativa": ["no", "es", "texto"]}},
    {k: v for k, v in _valido().items() if k != "id"},
])
def test_los_archivos_invalidos_se_omiten_sin_romper_los_demas(tmp_path, malo):
    _escribir(tmp_path, "a_malo.json", malo)
    _escribir(tmp_path, "b_bueno.json", {**_valido(), "id": "ej-bueno"})
    assert [e["id"] for e in ejemplos.listar_ejemplos(tmp_path)] == ["ej-bueno"]


def test_un_id_repetido_se_omite(tmp_path):
    _escribir(tmp_path, "a.json", _valido())
    _escribir(tmp_path, "b.json", {**_valido(), "titulo": "Otro con el mismo id"})
    lista = ejemplos.listar_ejemplos(tmp_path)
    assert len(lista) == 1 and lista[0]["titulo"] == "Un ejemplo"


# --- Calidad de los ejemplos incluidos ---

def _editor_campos():
    src = (ROOT / "frontend/src/lib/documento.js").read_text(encoding="utf-8")
    bloque = src[src.index("export const CONTENT_FIELDS"):src.index("]", src.index("export const CONTENT_FIELDS"))]
    return set(re.findall(r"'([a-z_]+)'", bloque))


@pytest.fixture(scope="module")
def unidad():
    return ejemplos.obtener_ejemplo("unidad-ept-programacion")


@pytest.fixture(scope="module")
def sesion():
    return ejemplos.obtener_ejemplo("sesion-ept-programacion")


def test_todas_las_secciones_son_campos_que_el_editor_y_el_exportador_conocen(unidad, sesion):
    editor = _editor_campos()
    for ej in (unidad, sesion):
        claves = set(ej["content"]) - {"titulo"}
        assert claves <= editor, claves - editor
        assert claves <= _CONTENT_FIELDS, claves - _CONTENT_FIELDS


def test_los_ejemplos_traen_las_secciones_nuevas_del_formato(unidad, sesion):
    assert {"datos_informativos", "valores_y_enfoques_transversales", "materiales_basicos"} <= set(unidad["content"])
    assert {"reto", "valores_y_enfoques_transversales", "secuencia_didactica"} <= set(sesion["content"])


def test_la_unidad_tiene_un_criterio_por_sesion(unidad):
    sesiones = _bloques_de_sesion(unidad["content"]["secuencia_de_sesiones"])
    assert len(sesiones) == 4
    assert all(s["criterio"] and s["actividades"] for s in sesiones)
    assert len({s["criterio"] for s in sesiones}) == 4            # sin criterios repetidos (HU-39)


@pytest.mark.parametrize("ejemplo_id", ["unidad-ept-programacion", "sesion-ept-programacion"])
def test_la_matriz_axiologica_es_una_tabla_valida(ejemplo_id):
    contenido = ejemplos.obtener_ejemplo(ejemplo_id)["content"]["valores_y_enfoques_transversales"]
    assert extraer_matriz(contenido) and contar_filas_matriz(contenido) >= 1
    filas = parse_markdown_table(contenido)
    assert len(filas[0]) == 4 and all(all(c.strip() for c in fila) for fila in filas)   # sin celdas vacías


def test_los_datos_informativos_son_una_ficha_item_contenido(unidad):
    filas = parse_markdown_table(unidad["content"]["datos_informativos"])
    assert filas[0] == ["ITEM", "CONTENIDO"]
    items = {f[0].strip("*") for f in filas[1:]}
    assert {"DRE / UGEL", "Institución educativa", "Área curricular", "Grado y secciones",
            "Fecha de inicio", "Fecha de término", "Coordinación pedagógica", "Docente(s)"} <= items


def test_el_ejemplo_de_sesion_muestra_el_recurso_previo_de_aula_invertida(sesion):
    assert "https://www.youtube.com/watch?v=" in sesion["content"]["secuencia_didactica"]
    for momento in ("INICIO", "DESARROLLO", "CIERRE"):
        assert momento in sesion["content"]["secuencia_didactica"]


@pytest.mark.parametrize("ejemplo_id", ["unidad-ept-programacion", "sesion-ept-programacion"])
def test_los_ejemplos_no_exponen_nombres_de_personas_reales(ejemplo_id):
    """Los ven todos los docentes: los nombres de los documentos fuente se reemplazaron."""
    texto = json.dumps(ejemplos.obtener_ejemplo(ejemplo_id), ensure_ascii=False)
    for nombre in ("Jesús", "Alejandro", "Velásquez", "Veláquez", "Aguilar", "Juana", "Martínez"):
        assert nombre not in texto, nombre
    assert "[Nombre del docente]" in texto


def test_los_ejemplos_se_pueden_exportar_a_docx_y_pdf(unidad, sesion, tmp_path):
    for ej, pdf in ((unidad, generar_pdf_unidad), (sesion, generar_pdf_sesion)):
        assert generar_docx(ej["content"], ej["tipo"], None)[:2] == b"PK"        # un .docx es un zip
        salida = tmp_path / f"{ej['tipo']}.pdf"
        pdf(ej["content"], str(salida))
        assert salida.read_bytes().startswith(b"%PDF")


def test_cada_ejemplo_declara_su_fuente(unidad, sesion):
    for ej in (unidad, sesion):
        assert "reemplazaron" in ej["fuente"] and ".docx" in ej["fuente"]


# --- Endpoints ---

@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(data.router)

    def sin_base_de_datos():
        raise AssertionError("los ejemplos no deben abrir la base de datos")

    usuario = SimpleNamespace(id="u", stats=SimpleNamespace(docs_generados=0, puntos=0, mejoras_realizadas=0))
    app.dependency_overrides[get_db] = sin_base_de_datos
    app.dependency_overrides[get_current_user] = lambda: usuario
    return TestClient(app), usuario


def test_la_lista_de_ejemplos(cliente):
    c, _ = cliente
    r = c.get("/data/ejemplos")
    assert r.status_code == 200
    assert [e["tipo"] for e in r.json()] == ["unidad", "sesion"]
    assert "content" not in r.json()[0]


def test_el_detalle_de_un_ejemplo_trae_el_contenido(cliente):
    c, _ = cliente
    r = c.get("/data/ejemplos/sesion-ept-programacion")
    assert r.status_code == 200 and r.json()["content"]["reto"].startswith("¿Cómo podemos")


def test_un_ejemplo_inexistente_da_404(cliente):
    c, _ = cliente
    assert c.get("/data/ejemplos/no-existe").status_code == 404
    assert c.get("/data/ejemplos/..%2F..%2F.env").status_code in (404, 422)


def test_verlos_no_cuenta_como_generacion_ni_suma_puntos(cliente):
    c, usuario = cliente
    for ruta in ("/data/ejemplos", "/data/ejemplos/unidad-ept-programacion", "/data/ejemplos/sesion-ept-programacion"):
        assert c.get(ruta).status_code == 200
    assert vars(usuario.stats) == {"docs_generados": 0, "puntos": 0, "mejoras_realizadas": 0}


def test_requiere_iniciar_sesion():
    app = FastAPI()
    app.include_router(data.router)
    c = TestClient(app)
    assert c.get("/data/ejemplos").status_code in (401, 403)
    assert c.get("/data/ejemplos/unidad-ept-programacion").status_code in (401, 403)


# --- Frontend (verificación estática) ---

def _leer(ruta):
    return (ROOT / ruta).read_text(encoding="utf-8")


def test_la_pagina_usa_el_visor_del_editor_en_solo_lectura():
    src = _leer("frontend/src/pages/Ejemplos.jsx")
    assert "from './Editor'" in src and "<EditableSection" in src
    assert re.search(r"\n\s+disabled\n", src)                       # modo solo lectura
    assert "/generate/" not in src and "refine" not in src.replace("onRefine", "")   # sin IA ni refinamiento


def test_el_editor_exporta_lo_que_reutiliza_la_biblioteca():
    # Campos y etiquetas viven en lib/documento.js y el Editor los reexporta (Ejemplos importa de './Editor').
    doc = _leer("frontend/src/lib/documento.js")
    assert "export const CONTENT_FIELDS" in doc and "export const SECTION_LABELS" in doc
    editor = _leer("frontend/src/pages/Editor.jsx")
    assert "export { CONTENT_FIELDS, SECTION_LABELS }" in editor and "export function EditableSection" in editor


def test_la_biblioteca_esta_en_el_menu_y_en_las_rutas():
    assert "label=\"Ejemplos\"" in _leer("frontend/src/components/Sidebar.jsx")
    app = _leer("frontend/src/App.jsx")
    assert 'path="/ejemplos"' in app and "user ? <Ejemplos />" in app          # ruta protegida
