"""HU-33: generación de documentos como jobs en segundo plano.

El cliente crea un job (202 + job_id) y consulta su estado por polling, de modo
que el trabajo sobrevive a que se cierre la pestaña. La generación en sí
reutiliza GenerationService (los mismos generadores SSE que el endpoint de
streaming): el runner consume sus eventos en vez de enviarlos por HTTP.

Fase 1 (ver backlog/HU-33): un pool de hilos propio dentro del proceso web.
No usa BackgroundTasks de Starlette porque esas tareas síncronas ocupan el
mismo threadpool que atiende las requests; un pool dedicado evita que varias
generaciones largas dejen sin hilos al resto de la API. El límite real de
llamadas simultáneas a Bedrock sigue siendo el de HU-34.
"""
import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from .. import models
from .generation_service import get_generation_service

logger = logging.getLogger(__name__)

TIPOS_VALIDOS = ("unidad", "sesion")
ESTADOS_ACTIVOS = ("pending", "running")

# Máximo de jobs activos (pendientes + en ejecución) por usuario: evita que un
# solo docente copie la cola entera con clics repetidos.
MAX_JOBS_ACTIVOS_POR_USUARIO = 3

# Un job activo sin cambios durante este tiempo se considera huérfano (p. ej.
# el servidor se reinició a mitad): una generación normal dura ~2-3 minutos.
MINUTOS_JOB_HUERFANO = 15

DEFAULT_WORKERS = 4

# Texto parcial de cada job en ejecución, solo en memoria de este proceso: se
# expone en el polling para conservar la vista previa en vivo del wizard sin
# escribir cada fragmento en la base de datos.
_progreso: Dict[str, str] = {}
_validando: set = set()          # jobs que ya pasaron de generar a validar/estructurar
_progreso_lock = threading.Lock()

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def _max_workers() -> int:
    raw = (os.environ.get("GENERATION_JOBS_MAX_WORKERS") or "").strip()
    try:
        valor = int(raw)
        return valor if valor >= 1 else DEFAULT_WORKERS
    except ValueError:
        return DEFAULT_WORKERS


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=_max_workers(), thread_name_prefix="gen-job"
                )
    return _executor


class LimiteJobsExcedido(Exception):
    """El usuario ya tiene el máximo de jobs activos."""


def _ahora() -> datetime:
    return datetime.utcnow()


# --------------------------------------------------------------------------
# Creación y ejecución
# --------------------------------------------------------------------------

def crear_job(db: Session, user_id: str, tipo: str, params: Dict[str, Any]) -> models.GenerationJob:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo de job inválido: {tipo}")

    # Los huérfanos no deben contar contra el límite del usuario.
    for j in _jobs_activos(db, user_id):
        _marcar_si_huerfano(db, j)
    if len(_jobs_activos(db, user_id)) >= MAX_JOBS_ACTIVOS_POR_USUARIO:
        raise LimiteJobsExcedido(
            f"Ya tienes {MAX_JOBS_ACTIVOS_POR_USUARIO} generaciones en curso. "
            f"Espera a que termine alguna."
        )

    job = models.GenerationJob(
        id=str(uuid.uuid4()), user_id=user_id, tipo=tipo, status="pending",
        params=dict(params or {}),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def encolar(job_id: str, ejecutor: Optional[Callable[[str], None]] = None) -> None:
    """Envía el job al pool dedicado. `ejecutor` permite sustituir el runner en tests."""
    _get_executor().submit(ejecutor or ejecutar_job, job_id)


def _parsear_evento(linea: str) -> Optional[Dict[str, Any]]:
    if not linea.startswith("data: "):
        return None
    try:
        return json.loads(linea[len("data: "):])
    except ValueError:
        return None


def _session_factory():
    from ..database import SessionLocal  # import tardío: exige DATABASE_URL
    return SessionLocal


def ejecutar_job(job_id: str, session_factory: Optional[Callable[[], Session]] = None,
                 service: Any = None) -> None:
    """Corre un job hasta el final. Siempre deja el job en 'done' o 'failed'.

    Usa su PROPIA sesión de base de datos: la de la request que lo creó se
    cierra cuando esa request responde.
    """
    db = (session_factory or _session_factory())()
    try:
        job = db.get(models.GenerationJob, job_id)
        if job is None or job.status != "pending":
            return
        job.status = "running"
        db.commit()

        user = db.get(models.User, job.user_id)
        svc = service or get_generation_service()
        generador = (svc.generar_unidad_stream_events if job.tipo == "unidad"
                     else svc.generar_sesion_stream_events)

        error: Optional[str] = None
        doc_id: Optional[str] = None
        texto = ""
        for linea in generador(dict(job.params or {}), user, db):
            evento = _parsear_evento(linea)
            if not evento:
                continue
            if evento.get("chunk"):
                texto += evento["chunk"]
                with _progreso_lock:
                    _progreso[job_id] = texto
            if evento.get("validando"):
                with _progreso_lock:
                    _validando.add(job_id)
            if evento.get("done"):
                error = evento.get("error")
                doc_id = evento.get("id")

        _finalizar(db, job_id, doc_id=doc_id, error=error)
    except Exception as e:  # el runner nunca debe dejar un job colgado en 'running'
        logger.exception("[Jobs] Falló el job %s", job_id)
        _finalizar(db, job_id, doc_id=None, error=str(e))
    finally:
        with _progreso_lock:
            _progreso.pop(job_id, None)
            _validando.discard(job_id)
        db.close()


def _finalizar(db: Session, job_id: str, doc_id: Optional[str], error: Optional[str]) -> None:
    try:
        db.rollback()  # descarta una transacción rota por un fallo previo
        job = db.get(models.GenerationJob, job_id)
        if job is None:
            return
        if error or not doc_id:
            job.status = "failed"
            job.error = error or "La generación terminó sin devolver un documento."
        else:
            job.status = "done"
            job.result_document_id = doc_id
            job.error = None
        db.commit()
    except Exception:
        logger.exception("[Jobs] No se pudo registrar el resultado del job %s", job_id)


# --------------------------------------------------------------------------
# Consulta
# --------------------------------------------------------------------------

def _jobs_activos(db: Session, user_id: str) -> List[models.GenerationJob]:
    return db.query(models.GenerationJob).filter(
        models.GenerationJob.user_id == user_id,
        models.GenerationJob.status.in_(ESTADOS_ACTIVOS),
    ).all()


def _marcar_si_huerfano(db: Session, job: models.GenerationJob, ahora: Optional[datetime] = None) -> None:
    if job.status not in ESTADOS_ACTIVOS or job.updated_at is None:
        return
    limite = (ahora or _ahora()) - timedelta(minutes=MINUTOS_JOB_HUERFANO)
    if job.updated_at < limite:
        job.status = "failed"
        job.error = ("La generación se interrumpió (el servidor se reinició o tardó "
                     "demasiado). Vuelve a intentarlo.")
        db.commit()


def obtener_job(db: Session, user_id: str, job_id: str) -> Optional[models.GenerationJob]:
    """Un job solo es visible para su dueño."""
    job = db.query(models.GenerationJob).filter(
        models.GenerationJob.id == job_id,
        models.GenerationJob.user_id == user_id,
    ).first()
    if job:
        _marcar_si_huerfano(db, job)
    return job


def listar_jobs(db: Session, user_id: str, limit: int = 20) -> List[models.GenerationJob]:
    jobs = db.query(models.GenerationJob).filter(
        models.GenerationJob.user_id == user_id,
    ).order_by(models.GenerationJob.created_at.desc()).limit(limit).all()
    for j in jobs:
        _marcar_si_huerfano(db, j)
    return jobs


def serializar(job: models.GenerationJob, db: Optional[Session] = None,
               incluir_resultado: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": job.id,
        "tipo": job.tipo,
        "status": job.status,
        "error": job.error,
        "result_document_id": job.result_document_id,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
    if job.status == "running":
        with _progreso_lock:
            texto = _progreso.get(job.id)
            validando = job.id in _validando
        if texto:
            out["texto_parcial"] = texto
        out["etapa"] = "validando" if validando else "generando"
    if incluir_resultado and job.status == "done" and db is not None and job.result_document_id:
        doc = db.query(models.Document).filter(models.Document.id == job.result_document_id).first()
        if doc:
            # Misma forma que el evento final del stream, que es lo que espera el Editor.
            out["resultado"] = {"done": True, "id": doc.id, "version": doc.current_version or 1,
                                **(doc.content or {})}
    return out
