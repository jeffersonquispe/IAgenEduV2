from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from ..services.generation_service import get_generation_service
from ..services import job_service
import asyncio

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("/unidad/stream")
async def create_unidad_stream(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Genera una unidad didáctica con streaming SSE.
    El cliente recibe chunks JSON: {"chunk": "...", "done": false}
    Cuando validando: {"validando": true}
    Al final: {"done": true, "id": "<doc_uuid>", ...secciones...}
    """
    service = get_generation_service()
    try:
        service.validar_limite_competencias(params)  # HU-45
        service.normalizar_datos_informativos(params)  # HU-46
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return StreamingResponse(
        service.generar_unidad_stream_events(params, current_user, db),
        media_type="text/event-stream",
    )


@router.post("/sesion/stream")
async def create_sesion_stream(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Genera una sesión de aprendizaje con streaming SSE.
    El cliente recibe chunks JSON: {"chunk": "...", "done": false}
    Cuando validando: {"validando": true}
    Al final: {"done": true, "id": "<doc_uuid>", ...secciones...}
    """
    service = get_generation_service()
    try:
        service.normalizar_recurso_previo(params.get("recurso_previo"))  # HU-43
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return StreamingResponse(
        service.generar_sesion_stream_events(params, current_user, db),
        media_type="text/event-stream",
    )


# --- HU-33: generación como job en segundo plano -------------------------------

def _crear_y_encolar(tipo: str, params: Dict[str, Any], db: Session, user: models.User):
    try:
        job = job_service.crear_job(db, user.id, tipo, params)
    except job_service.LimiteJobsExcedido as e:
        raise HTTPException(status_code=429, detail=str(e))
    job_service.encolar(job.id)
    return {"job_id": job.id, "status": job.status}


@router.post("/unidad/jobs", status_code=202)
async def create_unidad_job(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Crea un job de generación de Unidad y responde 202 de inmediato con su
    job_id; el trabajo corre en segundo plano (consultar con GET /generate/jobs/{id})."""
    try:
        get_generation_service().validar_limite_competencias(params)  # HU-45
        get_generation_service().normalizar_datos_informativos(params)  # HU-46
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _crear_y_encolar("unidad", params, db, current_user)


@router.post("/sesion/jobs", status_code=202)
async def create_sesion_job(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Crea un job de generación de Sesión (ver create_unidad_job)."""
    try:
        get_generation_service().normalizar_recurso_previo(params.get("recurso_previo"))  # HU-43
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _crear_y_encolar("sesion", params, db, current_user)


@router.get("/jobs")
async def list_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Jobs recientes del usuario (para que el Dashboard muestre los que siguen
    en curso o fallaron aunque se haya cerrado la pestaña)."""
    jobs = job_service.listar_jobs(db, current_user.id, limit=max(1, min(limit, 50)))
    return [job_service.serializar(j) for j in jobs]


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Estado de un job; con status=done incluye `resultado` (el documento)."""
    job = job_service.obtener_job(db, current_user.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job_service.serializar(job, db, incluir_resultado=True)


@router.post("/validar")
async def revalidate_document(
    params: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
):
    """HU-30: recalcula la validación del documento tal como está en el Editor (tras editar
    o refinar una sección). Sin IA y sin tocar la base de datos."""
    try:
        return get_generation_service().revalidar(params)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/refine")
async def refine_field(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Refina un campo con IA y guarda versión anterior del documento."""
    try:
        service = get_generation_service()
        return await asyncio.to_thread(service.refinar, params, current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
