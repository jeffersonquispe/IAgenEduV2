"""HU-24: búsqueda, filtrado y paginación de GET /data/documents.

Unit/integración contra SQLite en memoria con las tablas reales del modelo.
"""
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from src.api import models
from src.api.database import get_db
from src.api.routes import data
from src.api.routes.auth import get_current_user

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"  # con letras: SQLite daría afinidad numérica a un id solo de dígitos
OTRO = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for t in (models.Document.__table__, models.DocumentVersion.__table__):  # sin FK a profiles/auth.users
        t.create(engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    s = Session()
    base = datetime(2026, 1, 1)

    def doc(i, user, tipo, titulo, area=None, grado=None):
        did = str(uuid.uuid4())
        s.add(models.Document(id=did, user_id=user, type=tipo, title=titulo,
                              content={}, created_at=base + timedelta(days=i),
                              area_curricular=area, grado=grado))
        return did

    doc(1, USER, "unidad", "Unidad de Fracciones", "Matemática", "1")
    doc(2, USER, "sesion", "Sesión: sumar fracciones", "Matemática", "1")
    doc(3, USER, "unidad", "Unidad de la Noticia", "Comunicación", "2")
    # Generado en modo "solo_generador": no tiene PipelineRun, pero sí área y grado en el documento.
    doc(4, USER, "sesion", "Sesión solo generador", "Comunicación", "2")
    doc(5, USER, "unidad", "Descuento 100% real_idad", "Matemática", "3")
    doc(6, OTRO, "unidad", "Unidad de Fracciones ajena", "Matemática", "1")
    s.commit()
    yield s
    s.close()


def _titulos(consulta):
    return [d.title for d in consulta.order_by(models.Document.created_at)]


def test_sin_filtros_solo_devuelve_documentos_del_usuario(db):
    c = data.construir_consulta_documentos(db, USER)
    assert c.count() == 5
    assert all("ajena" not in t for t in _titulos(c))


def test_filtro_por_tipo(db):
    assert _titulos(data.construir_consulta_documentos(db, USER, type="sesion")) == [
        "Sesión: sumar fracciones", "Sesión solo generador"]


def test_filtro_por_area(db):
    t = _titulos(data.construir_consulta_documentos(db, USER, area_curricular="Comunicación"))
    assert t == ["Unidad de la Noticia", "Sesión solo generador"]


def test_filtro_por_grado(db):
    t = _titulos(data.construir_consulta_documentos(db, USER, grado="1"))
    assert t == ["Unidad de Fracciones", "Sesión: sumar fracciones"]


def test_filtros_combinados(db):
    c = data.construir_consulta_documentos(db, USER, type="unidad", area_curricular="Matemática")
    assert _titulos(c) == ["Unidad de Fracciones", "Descuento 100% real_idad"]


def test_documento_sin_pipeline_run_si_coincide_con_filtro_de_area_y_grado(db):
    """Con área/grado en el propio documento, el filtro alcanza también a los generados en modo solo_generador."""
    por_area = data.construir_consulta_documentos(db, USER, area_curricular="Comunicación")
    por_grado = data.construir_consulta_documentos(db, USER, grado="2")
    assert "Sesión solo generador" in _titulos(por_area)
    assert "Sesión solo generador" in _titulos(por_grado)


def test_el_filtro_ya_no_une_la_tabla_de_pipeline_runs(db):
    sql = str(data.construir_consulta_documentos(db, USER, area_curricular="Matemática", grado="1"))
    assert "pipeline_runs" not in sql


def test_busqueda_por_titulo_ignora_mayusculas(db):
    assert data.construir_consulta_documentos(db, USER, q="fracciones").count() == 2
    assert data.construir_consulta_documentos(db, USER, q="NOTICIA").count() == 1


@pytest.mark.parametrize("q,esperado", [("100%", 1), ("real_idad", 1), ("%", 1), ("_", 1)])
def test_busqueda_trata_comodines_como_texto_literal(db, q, esperado):
    assert data.construir_consulta_documentos(db, USER, q=q).count() == esperado


def test_busqueda_vacia_o_espacios_no_filtra(db):
    assert data.construir_consulta_documentos(db, USER, q="   ").count() == 5


# --- Integración HTTP: validación de parámetros, paginación y header ---

@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(data.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=USER)
    return TestClient(app)


def test_endpoint_por_defecto_devuelve_lista_ordenada_mas_reciente_primero(client):
    r = client.get("/data/documents")
    assert r.status_code == 200
    assert r.headers["X-Total-Count"] == "5"
    assert r.json()[0]["title"] == "Descuento 100% real_idad"


def test_endpoint_paginacion_con_limit_y_offset(client):
    r1 = client.get("/data/documents", params={"limit": 2, "offset": 0})
    r2 = client.get("/data/documents", params={"limit": 2, "offset": 2})
    ids = [d["id"] for d in r1.json()] + [d["id"] for d in r2.json()]
    assert len(r1.json()) == 2 and len(r2.json()) == 2 and len(set(ids)) == 4
    assert r1.headers["X-Total-Count"] == r2.headers["X-Total-Count"] == "5"


def test_endpoint_total_refleja_filtros_no_la_pagina(client):
    r = client.get("/data/documents", params={"type": "unidad", "limit": 1})
    assert len(r.json()) == 1 and r.headers["X-Total-Count"] == "3"


def test_endpoint_filtra_y_busca(client):
    r = client.get("/data/documents", params={"area_curricular": "Matemática", "q": "sumar"})
    assert [d["title"] for d in r.json()] == ["Sesión: sumar fracciones"]


@pytest.mark.parametrize("params", [
    {"type": "otro"}, {"limit": 0}, {"limit": 101}, {"offset": -1}, {"q": "x" * 101},
])
def test_endpoint_rechaza_parametros_invalidos(client, params):
    assert client.get("/data/documents", params=params).status_code == 422


def test_endpoint_devuelve_area_y_grado_para_el_listado(client):
    # El Dashboard muestra área y grado en cada fila sin abrir el contenido del documento.
    r = client.get("/data/documents", params={"q": "sumar"})
    assert [(d["area_curricular"], d["grado"]) for d in r.json()] == [("Matemática", "1")]
