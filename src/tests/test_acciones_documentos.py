"""Acciones sobre documentos del listado: duplicar, eliminar y orden por última actividad.

Integración contra SQLite en memoria con las tablas reales del modelo.
"""
import uuid
from datetime import datetime, timedelta
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

USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTRO = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
BASE = datetime(2026, 1, 1)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for t in (models.Document.__table__, models.DocumentVersion.__table__,
              models.PipelineRun.__table__, models.GenerationJob.__table__):
        t.create(engine, checkfirst=True)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(data.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=USER)
    return TestClient(app)


def _doc(db, titulo, *, user=USER, dias=0, tipo="unidad", content=None, parent=None):
    doc_id = str(uuid.uuid4())
    contenido = content if content is not None else {"titulo": titulo, "situacion_significativa": "Texto"}
    db.add(models.Document(id=doc_id, user_id=user, type=tipo, title=titulo, content=contenido,
                           created_at=BASE + timedelta(days=dias), current_version=1,
                           area_curricular="Matemática", grado="1", parent_document_id=parent))
    db.add(models.DocumentVersion(document_id=doc_id, version_num=1, content=contenido,
                                  change_label="Generación inicial", created_at=BASE + timedelta(days=dias)))
    db.commit()
    return doc_id


# --- Orden por última actividad ---

def test_listado_ordena_por_ultima_edicion_no_por_creacion(client, db):
    viejo = _doc(db, "Creado antes", dias=1)
    _doc(db, "Creado después", dias=10)
    # El documento viejo se edita hoy: debe pasar al frente.
    db.add(models.DocumentVersion(document_id=viejo, version_num=2, content={}, change_label="Edición guardada",
                                  created_at=BASE + timedelta(days=30)))
    db.commit()
    r = client.get("/data/documents")
    assert [d["title"] for d in r.json()] == ["Creado antes", "Creado después"]


def test_listado_expone_updated_at(client, db):
    _doc(db, "Doc", dias=2)
    d = client.get("/data/documents").json()[0]
    assert d["updated_at"].startswith("2026-01-03")
    assert d["created_at"].startswith("2026-01-03")


def test_updated_at_refleja_la_version_mas_reciente(client, db):
    doc_id = _doc(db, "Doc", dias=2)
    db.add(models.DocumentVersion(document_id=doc_id, version_num=2, content={}, change_label="x",
                                  created_at=BASE + timedelta(days=20)))
    db.commit()
    d = client.get("/data/documents").json()[0]
    assert d["updated_at"].startswith("2026-01-21") and d["created_at"].startswith("2026-01-03")


# --- Duplicar ---

def test_duplicar_crea_una_copia_independiente(client, db):
    original = _doc(db, "Unidad de Fracciones")
    r = client.post(f"/data/documents/{original}/duplicate")
    assert r.status_code == 201
    copia = r.json()
    assert copia["id"] != original
    assert copia["title"] == "Copia de Unidad de Fracciones"
    assert copia["content"]["titulo"] == "Copia de Unidad de Fracciones"
    assert copia["content"]["situacion_significativa"] == "Texto"
    assert copia["current_version"] == 1
    assert (copia["area_curricular"], copia["grado"], copia["type"]) == ("Matemática", "1", "unidad")

    en_bd = db.get(models.Document, copia["id"])
    assert en_bd.user_id == USER
    versiones = db.query(models.DocumentVersion).filter_by(document_id=copia["id"]).all()
    assert len(versiones) == 1 and versiones[0].version_num == 1


def test_duplicar_no_comparte_el_contenido_con_el_original(client, db):
    original = _doc(db, "Original")
    copia_id = client.post(f"/data/documents/{original}/duplicate").json()["id"]
    copia = db.get(models.Document, copia_id)
    copia.content = {**copia.content, "situacion_significativa": "Editado en la copia"}
    db.commit()
    db.expire_all()
    assert db.get(models.Document, original).content["situacion_significativa"] == "Texto"


def test_duplicar_conserva_la_unidad_de_una_sesion(client, db):
    unidad = _doc(db, "Unidad")
    sesion = _doc(db, "Sesión", tipo="sesion", parent=unidad)
    copia_id = client.post(f"/data/documents/{sesion}/duplicate").json()["id"]
    assert db.get(models.Document, copia_id).parent_document_id == unidad


def test_duplicar_acota_el_titulo(client, db):
    original = _doc(db, "T" * 500)
    assert len(client.post(f"/data/documents/{original}/duplicate").json()["title"]) == data.MAX_LARGO_TITULO


def test_duplicar_un_documento_ajeno_o_inexistente_da_404(client, db):
    ajeno = _doc(db, "Ajeno", user=OTRO)
    assert client.post(f"/data/documents/{ajeno}/duplicate").status_code == 404
    assert client.post("/data/documents/no-existe/duplicate").status_code == 404
    assert db.query(models.Document).count() == 1


# --- Eliminar ---

def test_eliminar_borra_el_documento_y_su_historial(client, db):
    doc_id = _doc(db, "A borrar")
    otro = _doc(db, "Se queda")
    assert client.delete(f"/data/documents/{doc_id}").status_code == 204
    assert db.get(models.Document, doc_id) is None
    assert db.query(models.DocumentVersion).filter_by(document_id=doc_id).count() == 0
    assert db.get(models.Document, otro) is not None
    assert db.query(models.DocumentVersion).filter_by(document_id=otro).count() == 1


def test_eliminar_conserva_metricas_trabajos_y_sesiones_desvinculados(client, db):
    unidad = _doc(db, "Unidad")
    sesion = _doc(db, "Sesión", tipo="sesion", parent=unidad)
    db.add(models.PipelineRun(id="run-1", document_id=unidad, tipo="unidad"))
    db.add(models.GenerationJob(id="job-1", user_id=USER, tipo="unidad", status="done", result_document_id=unidad))
    db.commit()

    assert client.delete(f"/data/documents/{unidad}").status_code == 204
    db.expire_all()
    assert db.get(models.PipelineRun, "run-1").document_id is None        # la métrica se conserva
    assert db.get(models.GenerationJob, "job-1").result_document_id is None
    assert db.get(models.Document, sesion).parent_document_id is None      # la sesión sigue existiendo


def test_eliminar_un_documento_ajeno_no_lo_borra(client, db):
    ajeno = _doc(db, "Ajeno", user=OTRO)
    assert client.delete(f"/data/documents/{ajeno}").status_code == 404
    assert db.get(models.Document, ajeno) is not None
    assert db.query(models.DocumentVersion).filter_by(document_id=ajeno).count() == 1


def test_eliminar_dos_veces_da_404_la_segunda(client, db):
    doc_id = _doc(db, "Doc")
    assert client.delete(f"/data/documents/{doc_id}").status_code == 204
    assert client.delete(f"/data/documents/{doc_id}").status_code == 404
