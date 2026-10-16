"""Guardado de lo editado en el Editor: PUT /data/documents/{id} y su historial de versiones."""
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api import models
from src.api.database import get_db
from src.api.routes import data
from src.api.routes.auth import get_current_user
from src.api.routes.export import _CONTENT_FIELDS
from src.api.services.generation_service import ConflictoDeVersion, GenerationService
from src.core.campos_documento import CAMPOS_DE_CONTENIDO

ROOT = Path(__file__).resolve().parents[2]
USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTRO = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

CONTENIDO_SESION = {
    "titulo": "Sesión - T", "datos_informativos": "Colegio X", "reto": "¿Cómo?",
    "propositos_de_aprendizaje": "Competencia A",
    "secuencia_didactica": "INICIO 10 min. DESARROLLO 60 min. CIERRE 20 min.",
    "contenido_crudo": "| texto crudo del modelo |",
}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for t in (models.Document.__table__, models.DocumentVersion.__table__):
        t.create(engine, checkfirst=True)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _documento(db, user=USER, tipo="sesion", content=None, version=1):
    doc_id = str(uuid.uuid4())
    contenido = dict(content if content is not None else CONTENIDO_SESION)
    db.add(models.Document(id=doc_id, user_id=user, type=tipo, title="Doc", content=contenido,
                           current_version=version))
    db.add(models.DocumentVersion(document_id=doc_id, version_num=version, content=contenido,
                                  change_label="Generación inicial"))
    db.commit()
    return doc_id


def _usuario(user_id=USER):
    return SimpleNamespace(id=user_id)


def _guardar(db, doc_id, content, base_version=None, user=USER):
    params = {"content": content}
    if base_version is not None:
        params["base_version"] = base_version
    return GenerationService().guardar_cambios(db, _usuario(user), doc_id, params)


def _doc(db, doc_id):
    db.expire_all()
    return db.get(models.Document, doc_id)


def _versiones(db, doc_id):
    db.expire_all()
    return db.query(models.DocumentVersion).filter_by(document_id=doc_id).order_by(
        models.DocumentVersion.version_num).all()


# --- Guardar ---

def test_guarda_el_cambio_y_sube_la_version(db):
    doc_id = _documento(db)
    r = _guardar(db, doc_id, {"reto": "¿Cómo mejoramos nuestro barrio?"})
    assert r["guardado"] is True and r["version"] == 2
    doc = _doc(db, doc_id)
    assert doc.content["reto"] == "¿Cómo mejoramos nuestro barrio?" and doc.current_version == 2


def test_registra_una_version_nueva_con_el_contenido_completo(db):
    doc_id = _documento(db)
    _guardar(db, doc_id, {"reto": "Nuevo reto"})
    versiones = _versiones(db, doc_id)
    assert [v.version_num for v in versiones] == [1, 2]
    assert versiones[0].content["reto"] == "¿Cómo?"                       # la original se conserva
    assert versiones[1].content["reto"] == "Nuevo reto" and versiones[1].change_label == "Edición guardada"


def test_conserva_lo_que_no_se_edita(db):
    doc_id = _documento(db)
    _guardar(db, doc_id, {"reto": "Otro"})
    contenido = _doc(db, doc_id).content
    assert contenido["contenido_crudo"] == "| texto crudo del modelo |" and contenido["titulo"] == "Sesión - T"
    assert contenido["datos_informativos"] == "Colegio X"


def test_guardar_lo_mismo_no_crea_version(db):
    doc_id = _documento(db)
    r = _guardar(db, doc_id, {"reto": "¿Cómo?", "datos_informativos": "Colegio X"})
    assert r["guardado"] is False and r["version"] == 1
    assert len(_versiones(db, doc_id)) == 1 and _doc(db, doc_id).current_version == 1


def test_un_documento_sin_version_registrada_cuenta_como_version_1(db):
    doc_id = _documento(db)
    doc = db.get(models.Document, doc_id)
    doc.current_version = None
    db.commit()
    assert _guardar(db, doc_id, {"reto": "X"})["version"] == 2


# --- La validación la calcula el servidor ---

def test_recalcula_la_validacion_si_el_documento_ya_tenia(db):
    base = {**CONTENIDO_SESION, "validacion": {
        "es_valido": False, "puntaje_validacion": 75, "errores_criticos": 1, "errores_advertencia": 0,
        "detalle": [{"tipo": "CRITICO", "categoria": "ESTRUCTURA",
                     "mensaje": "Falta la sección requerida: RETO", "seccion": "RETO"}]}}
    base["reto"] = ""
    doc_id = _documento(db, content=base)
    r = _guardar(db, doc_id, {"reto": "¿Cómo transformamos el barrio?"})
    assert r["validacion"]["es_valido"] is True and r["validacion"]["errores_criticos"] == 0
    assert _doc(db, doc_id).content["validacion"]["es_valido"] is True       # y queda guardada


def test_si_el_documento_no_tenia_validacion_no_se_inventa_una(db):
    doc_id = _documento(db)
    assert _guardar(db, doc_id, {"reto": "Otro"})["validacion"] is None
    assert "validacion" not in _doc(db, doc_id).content


def test_el_cliente_no_puede_falsificar_la_validacion_ni_otros_metadatos(db):
    doc_id = _documento(db)
    _guardar(db, doc_id, {"reto": "Otro", "validacion": {"es_valido": True}, "contenido_crudo": "hackeado",
                          "id": "otro", "done": True, "type": "unidad"})
    contenido = _doc(db, doc_id).content
    assert "validacion" not in contenido and contenido["contenido_crudo"] == "| texto crudo del modelo |"
    assert "done" not in contenido and _doc(db, doc_id).type == "sesion"


# --- Conflictos y propiedad ---

def test_con_la_version_correcta_guarda(db):
    doc_id = _documento(db)
    assert _guardar(db, doc_id, {"reto": "A"}, base_version=1)["version"] == 2
    assert _guardar(db, doc_id, {"reto": "B"}, base_version=2)["version"] == 3


def test_con_una_version_vieja_hay_conflicto_y_no_se_pisa_el_cambio_ajeno(db):
    doc_id = _documento(db)
    _guardar(db, doc_id, {"reto": "Cambio desde la pestaña A"}, base_version=1)
    with pytest.raises(ConflictoDeVersion) as e:
        _guardar(db, doc_id, {"reto": "Cambio desde la pestaña B"}, base_version=1)
    assert e.value.version_actual == 2
    assert _doc(db, doc_id).content["reto"] == "Cambio desde la pestaña A"
    assert len(_versiones(db, doc_id)) == 2


def test_sin_base_version_no_se_comprueba_el_conflicto(db):
    doc_id = _documento(db)
    _guardar(db, doc_id, {"reto": "A"})
    assert _guardar(db, doc_id, {"reto": "B"})["version"] == 3


def test_un_documento_ajeno_o_inexistente_no_se_puede_guardar(db):
    doc_id = _documento(db, user=USER)
    with pytest.raises(LookupError):
        _guardar(db, doc_id, {"reto": "intruso"}, user=OTRO)
    with pytest.raises(LookupError):
        _guardar(db, "no-existe", {"reto": "x"})
    assert _doc(db, doc_id).content["reto"] == "¿Cómo?"


# --- Entradas inválidas ---

@pytest.mark.parametrize("params", [
    {}, {"content": "texto"}, {"content": ["a"]},
    {"content": {"reto": 5}}, {"content": {"reto": None}}, {"content": {"reto": ["x"]}},
    {"content": {"reto": "x" * 300_001}},
    {"content": {"reto": "x"}, "base_version": "2"}, {"content": {"reto": "x"}, "base_version": True},
    {"content": {"reto": "x"}, "base_version": 1.5},
])
def test_rechaza_entradas_invalidas_sin_modificar_nada(db, params):
    doc_id = _documento(db)
    with pytest.raises(ValueError):
        GenerationService().guardar_cambios(db, _usuario(), doc_id, params)
    assert _doc(db, doc_id).current_version == 1 and len(_versiones(db, doc_id)) == 1


def test_los_campos_desconocidos_se_ignoran(db):
    doc_id = _documento(db)
    r = _guardar(db, doc_id, {"campo_inventado": "x", "titulo": "Otro título"})
    assert r["guardado"] is False                         # no había nada válido que cambiar
    assert "campo_inventado" not in _doc(db, doc_id).content and _doc(db, doc_id).content["titulo"] == "Sesión - T"


# --- Historial acotado ---

def test_el_historial_se_poda_conservando_la_primera_y_las_mas_recientes(db):
    doc_id = _documento(db)
    tope = GenerationService.MAX_VERSIONES_POR_DOCUMENTO
    for i in range(tope + 15):
        _guardar(db, doc_id, {"reto": f"Reto {i}"})
    numeros = [v.version_num for v in _versiones(db, doc_id)]
    ultimo = _doc(db, doc_id).current_version
    assert len(numeros) == tope
    assert numeros[0] == 1 and numeros[-1] == ultimo                       # la original y la última
    assert numeros[1:] == list(range(ultimo - tope + 2, ultimo + 1))      # y las más recientes, contiguas


# --- Endpoint ---

@pytest.fixture
def cliente(db):
    app = FastAPI()
    app.include_router(data.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: _usuario()
    return TestClient(app)


def test_el_endpoint_guarda(cliente, db):
    doc_id = _documento(db)
    r = cliente.put(f"/data/documents/{doc_id}", json={"content": {"reto": "Nuevo"}, "base_version": 1})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["guardado"] is True


def test_el_endpoint_responde_409_con_el_codigo_y_la_version_actual(cliente, db):
    doc_id = _documento(db, version=3)
    r = cliente.put(f"/data/documents/{doc_id}", json={"content": {"reto": "x"}, "base_version": 1})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "version_conflict" and r.json()["detail"]["version_actual"] == 3


def test_el_endpoint_responde_404_y_422(cliente, db):
    doc_id = _documento(db)
    assert cliente.put("/data/documents/no-existe", json={"content": {"reto": "x"}}).status_code == 404
    assert cliente.put(f"/data/documents/{doc_id}", json={"content": {"reto": 5}}).status_code == 422
    assert cliente.put(f"/data/documents/{doc_id}", json={}).status_code == 422


def test_el_endpoint_no_deja_guardar_el_documento_de_otro(db):
    ajeno = _documento(db, user=OTRO)
    app = FastAPI()
    app.include_router(data.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: _usuario(USER)
    assert TestClient(app).put(f"/data/documents/{ajeno}", json={"content": {"reto": "x"}}).status_code == 404


def test_el_endpoint_requiere_sesion():
    app = FastAPI()
    app.include_router(data.router)
    assert TestClient(app).put("/data/documents/x", json={"content": {}}).status_code in (401, 403)


def test_la_lista_de_documentos_incluye_la_version(cliente, db):
    _documento(db, version=4)
    assert cliente.get("/data/documents").json()[0]["current_version"] == 4


# --- La versión viaja con el documento recién generado ---

def test_el_documento_generado_llega_al_editor_con_su_id_y_version():
    from src.api.services.job_service import serializar
    doc = SimpleNamespace(id="d1", content={"reto": "x"}, current_version=1)
    job = SimpleNamespace(id="j", tipo="sesion", status="done", error=None, result_document_id="d1",
                          created_at=None, updated_at=None)

    class Sesion:
        def query(self, _):
            return SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: doc))

    resultado = serializar(job, Sesion(), incluir_resultado=True)["resultado"]
    assert resultado["id"] == "d1" and resultado["version"] == 1 and resultado["reto"] == "x"


# --- Contrato con el Editor ---

def test_los_campos_de_contenido_del_backend_y_del_editor_coinciden():
    src = (ROOT / "frontend/src/lib/documento.js").read_text(encoding="utf-8")
    bloque = src[src.index("export const CONTENT_FIELDS"):src.index("]", src.index("export const CONTENT_FIELDS"))]
    assert set(re.findall(r"'([a-z_]+)'", bloque)) == set(CAMPOS_DE_CONTENIDO)
    assert _CONTENT_FIELDS is CAMPOS_DE_CONTENIDO                           # el exportador usa la misma fuente


def test_el_editor_guarda_con_control_de_version_atajo_y_aviso_de_salida():
    src = (ROOT / "frontend/src/pages/Editor.jsx").read_text(encoding="utf-8")
    assert "api.put(`/data/documents/${docId}`" in src and "base_version: versionActual" in src
    assert "key.toLowerCase() === 's'" in src and "e.ctrlKey || e.metaKey" in src       # Ctrl+S
    assert "'beforeunload'" in src and "volverAlDashboard" in src and "cambios sin guardar" in src.lower()
    assert "status === 409" in src                                                      # conflicto de versión
    assert "setFirmaGuardada(firmaEnviada)" in src                                      # si siguió escribiendo, sigue 'sin guardar'


def test_el_dashboard_abre_el_documento_con_su_id_y_version():
    src = (ROOT / "frontend/src/pages/Dashboard.jsx").read_text(encoding="utf-8")
    assert "id: doc.id, version: doc.current_version" in src
