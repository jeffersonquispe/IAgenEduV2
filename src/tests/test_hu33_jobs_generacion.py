"""HU-33: generación como job en segundo plano (servicio + endpoints)."""
import json
import threading
import time
from datetime import timedelta
from functools import partial
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import models
from src.api.database import get_db
from src.api.routes import generation
from src.api.routes.auth import get_current_user
from src.api.services import job_service

# Ids con letras: SQLite daría afinidad numérica a un uuid solo de dígitos.
USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTRO = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

# El runner real, guardado antes de que los tests lo sustituyan con monkeypatch.
EJECUTAR_JOB_REAL = job_service.ejecutar_job


@pytest.fixture
def factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'jobs.db'}", connect_args={"check_same_thread": False})
    for t in (models.User.__table__, models.Document.__table__, models.GenerationJob.__table__):
        t.create(engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add_all([models.User(id=USER, email="a@x.com"), models.User(id=OTRO, email="b@x.com")])
    s.commit()
    s.close()
    return Session


@pytest.fixture
def db(factory):
    s = factory()
    yield s
    s.close()


def _evento(**kw):
    return f"data: {json.dumps(kw)}\n\n"


class ServicioFalso:
    """Imita GenerationService: guarda un documento y emite el evento final."""

    def __init__(self, error=None, explota=False, sin_done=False, espera=None):
        self.error, self.explota, self.sin_done, self.espera = error, explota, sin_done, espera
        self.recibido = None
        self.hilo = None

    def _gen(self, tipo, params, user, db):
        self.recibido = (tipo, params, user.id)
        self.hilo = threading.current_thread().name
        yield _evento(chunk="Hola ", done=False)
        yield _evento(chunk="mundo", done=False)
        if self.espera:
            self.espera.wait(10)
        if self.explota:
            raise RuntimeError("Bedrock caído")
        if self.sin_done:
            return
        if self.error:
            yield _evento(done=True, error=self.error)
            return
        doc = models.Document(id="doc-1", user_id=user.id, type=tipo, title="T",
                              content={"situacion_significativa": "S"})
        db.add(doc)
        db.commit()
        yield _evento(done=True, id="doc-1", situacion_significativa="S")

    def generar_unidad_stream_events(self, params, user, db):
        return self._gen("unidad", params, user, db)

    def generar_sesion_stream_events(self, params, user, db):
        return self._gen("sesion", params, user, db)

    def __getattr__(self, nombre):
        # Las reglas de validación de entrada (validar_*/normalizar_*) las usan las
        # rutas antes de crear el job; el fake las delega en el servicio real para
        # que añadir una regla nueva no obligue a tocar este archivo.
        if nombre.startswith(("validar_", "normalizar_")):
            from src.api.services.generation_service import GenerationService
            return getattr(GenerationService, nombre)
        raise AttributeError(nombre)


# --- Servicio ---

def test_job_exitoso_pasa_a_done_con_el_documento(db, factory):
    job = job_service.crear_job(db, USER, "unidad", {"area": "Matemática"})
    assert job.status == "pending"
    svc = ServicioFalso()
    job_service.ejecutar_job(job.id, session_factory=factory, service=svc)
    db.expire_all()
    job = db.get(models.GenerationJob, job.id)
    assert job.status == "done" and job.result_document_id == "doc-1" and job.error is None
    tipo, params, user_id = svc.recibido
    assert tipo == "unidad" and params == {"area": "Matemática"} and user_id == USER


def test_job_de_sesion_usa_el_generador_de_sesion(db, factory):
    job = job_service.crear_job(db, USER, "sesion", {})
    svc = ServicioFalso()
    job_service.ejecutar_job(job.id, session_factory=factory, service=svc)
    assert svc.recibido[0] == "sesion"


def test_error_del_servicio_deja_el_job_en_failed_con_el_mensaje(db, factory):
    job = job_service.crear_job(db, USER, "unidad", {})
    job_service.ejecutar_job(job.id, session_factory=factory, service=ServicioFalso(error="Máximo 2 competencias"))
    db.expire_all()
    j = db.get(models.GenerationJob, job.id)
    assert j.status == "failed" and "Máximo 2" in j.error and j.result_document_id is None


def test_excepcion_inesperada_no_deja_el_job_colgado_en_running(db, factory):
    job = job_service.crear_job(db, USER, "unidad", {})
    job_service.ejecutar_job(job.id, session_factory=factory, service=ServicioFalso(explota=True))
    db.expire_all()
    j = db.get(models.GenerationJob, job.id)
    assert j.status == "failed" and "Bedrock caído" in j.error


def test_stream_sin_evento_final_es_fallo(db, factory):
    job = job_service.crear_job(db, USER, "unidad", {})
    job_service.ejecutar_job(job.id, session_factory=factory, service=ServicioFalso(sin_done=True))
    db.expire_all()
    j = db.get(models.GenerationJob, job.id)
    assert j.status == "failed" and "sin devolver" in j.error


def test_ejecutar_dos_veces_el_mismo_job_no_lo_repite(db, factory):
    job = job_service.crear_job(db, USER, "unidad", {})
    svc = ServicioFalso()
    job_service.ejecutar_job(job.id, session_factory=factory, service=svc)
    svc.recibido = None
    job_service.ejecutar_job(job.id, session_factory=factory, service=svc)
    assert svc.recibido is None


def test_el_progreso_en_memoria_se_limpia_al_terminar(db, factory):
    job = job_service.crear_job(db, USER, "unidad", {})
    job_service.ejecutar_job(job.id, session_factory=factory, service=ServicioFalso())
    assert job.id not in job_service._progreso


def test_job_huerfano_se_marca_como_failed_al_consultarlo(db):
    job = job_service.crear_job(db, USER, "unidad", {})
    job.status = "running"
    job.updated_at = job_service._ahora() - timedelta(minutes=job_service.MINUTOS_JOB_HUERFANO + 1)
    db.commit()
    j = job_service.obtener_job(db, USER, job.id)
    assert j.status == "failed" and "interrumpió" in j.error


def test_job_reciente_en_ejecucion_no_se_marca_huerfano(db):
    job = job_service.crear_job(db, USER, "unidad", {})
    job.status = "running"
    db.commit()
    assert job_service.obtener_job(db, USER, job.id).status == "running"


def test_un_job_solo_es_visible_para_su_dueno(db):
    job = job_service.crear_job(db, USER, "unidad", {})
    assert job_service.obtener_job(db, OTRO, job.id) is None
    assert job_service.listar_jobs(db, OTRO) == []


def test_limite_de_jobs_activos_por_usuario(db):
    for _ in range(job_service.MAX_JOBS_ACTIVOS_POR_USUARIO):
        job_service.crear_job(db, USER, "unidad", {})
    with pytest.raises(job_service.LimiteJobsExcedido):
        job_service.crear_job(db, USER, "unidad", {})
    job_service.crear_job(db, OTRO, "unidad", {})          # otro usuario no se ve afectado


def test_los_huerfanos_no_cuentan_contra_el_limite(db):
    for _ in range(job_service.MAX_JOBS_ACTIVOS_POR_USUARIO):
        j = job_service.crear_job(db, USER, "unidad", {})
        j.updated_at = job_service._ahora() - timedelta(hours=1)
    db.commit()
    job_service.crear_job(db, USER, "unidad", {})          # no lanza


def test_tipo_invalido(db):
    with pytest.raises(ValueError):
        job_service.crear_job(db, USER, "examen", {})


def test_serializar_incluye_texto_parcial_solo_mientras_corre(db):
    job = job_service.crear_job(db, USER, "unidad", {})
    job_service._progreso[job.id] = "texto a medias"
    assert "texto_parcial" not in job_service.serializar(job)       # aún pending
    job.status = "running"
    assert job_service.serializar(job)["texto_parcial"] == "texto a medias"
    job_service._progreso.pop(job.id)


# --- Endpoints (integración HTTP) ---

@pytest.fixture
def app_cliente(factory, monkeypatch):
    svc = ServicioFalso()
    # La ruta llama a job_service.encolar -> ejecutar_job; se le inyecta la BD
    # de prueba y el servicio falso, pero se conserva el pool de hilos real.
    monkeypatch.setattr(job_service, "ejecutar_job",
                        partial(EJECUTAR_JOB_REAL, session_factory=factory, service=svc))
    monkeypatch.setattr(generation, "get_generation_service", lambda: svc)
    app = FastAPI()
    app.include_router(generation.router)
    app.dependency_overrides[get_db] = lambda: factory()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=USER)
    return TestClient(app), svc


def _esperar_estado(cliente, job_id, estados, timeout=5):
    fin = time.time() + timeout
    while time.time() < fin:
        r = cliente.get(f"/generate/jobs/{job_id}")
        if r.json()["status"] in estados:
            return r.json()
        time.sleep(0.02)
    raise AssertionError(f"el job no llegó a {estados}")


def test_post_responde_202_y_el_job_termina_en_segundo_plano(app_cliente):
    cliente, svc = app_cliente
    r = cliente.post("/generate/unidad/jobs", json={"area": "Matemática", "competencias": ["A"]})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    final = _esperar_estado(cliente, job_id, {"done", "failed"})
    assert final["status"] == "done"
    assert final["resultado"]["id"] == "doc-1" and final["resultado"]["done"] is True
    assert final["resultado"]["situacion_significativa"] == "S"
    assert svc.hilo.startswith("gen-job")          # corrió en el pool dedicado, no en la request


def test_post_no_espera_a_que_termine_la_generacion(app_cliente):
    cliente, svc = app_cliente
    svc.espera = threading.Event()
    r = cliente.post("/generate/sesion/jobs", json={"tema": "T"})
    assert r.status_code == 202                    # volvió aunque la generación sigue bloqueada
    job_id = r.json()["job_id"]
    _esperar_estado(cliente, job_id, {"running"})
    time.sleep(0.1)
    parcial = cliente.get(f"/generate/jobs/{job_id}").json()
    assert parcial["status"] == "running" and "resultado" not in parcial
    assert parcial["texto_parcial"] == "Hola mundo"
    svc.espera.set()
    assert _esperar_estado(cliente, job_id, {"done", "failed"})["status"] == "done"


def test_job_fallido_se_reporta_con_su_error(app_cliente):
    cliente, svc = app_cliente
    svc.error = "sin cuota"
    job_id = cliente.post("/generate/sesion/jobs", json={}).json()["job_id"]
    final = _esperar_estado(cliente, job_id, {"failed", "done"})
    assert final["status"] == "failed" and final["error"] == "sin cuota"


def test_unidad_con_mas_de_2_competencias_responde_422_y_no_crea_job(app_cliente):
    cliente, _ = app_cliente
    r = cliente.post("/generate/unidad/jobs", json={"competencias": ["A", "B", "C"]})
    assert r.status_code == 422 and "Máximo 2" in r.json()["detail"]
    assert cliente.get("/generate/jobs").json() == []


def test_limite_de_jobs_activos_responde_429(app_cliente):
    cliente, svc = app_cliente
    svc.espera = threading.Event()
    for _ in range(job_service.MAX_JOBS_ACTIVOS_POR_USUARIO):
        assert cliente.post("/generate/sesion/jobs", json={}).status_code == 202
    r = cliente.post("/generate/sesion/jobs", json={})
    assert r.status_code == 429
    svc.espera.set()


def test_job_de_otro_usuario_da_404(app_cliente, factory):
    cliente, _ = app_cliente
    s = factory()
    ajeno = job_service.crear_job(s, OTRO, "unidad", {})
    s.close()
    assert cliente.get(f"/generate/jobs/{ajeno.id}").status_code == 404
    assert cliente.get("/generate/jobs/no-existe").status_code == 404


def test_listado_devuelve_solo_los_jobs_del_usuario_mas_recientes_primero(app_cliente, factory):
    cliente, _ = app_cliente
    s = factory()
    job_service.crear_job(s, OTRO, "unidad", {})
    s.close()
    a = cliente.post("/generate/sesion/jobs", json={}).json()["job_id"]
    _esperar_estado(cliente, a, {"done", "failed"})
    time.sleep(0.01)
    b = cliente.post("/generate/sesion/jobs", json={}).json()["job_id"]
    _esperar_estado(cliente, b, {"done", "failed"})
    ids = [j["id"] for j in cliente.get("/generate/jobs").json()]
    assert ids == [b, a]
