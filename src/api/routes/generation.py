from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from ..services.generation_service import get_generation_service
import asyncio

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("/unidad")
async def create_unidad(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Genera una unidad didáctica completa (async, no bloqueante)."""
    try:
        service = get_generation_service()
        return await asyncio.to_thread(service.crear_unidad, params, current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unidad/stream")
async def create_unidad_stream(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Genera una unidad didáctica con streaming SSE.
    El cliente recibe chunks JSON: {"chunk": "...", "done": false}
    Al final: {"done": true, "id": "<doc_uuid>"}
    """
    service = get_generation_service()
    return StreamingResponse(
        service.generar_unidad_stream_events(params, current_user, db),
        media_type="text/event-stream",
    )


@router.post("/sesion")
async def create_sesion(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Genera una sesión de aprendizaje (async, no bloqueante)."""
    try:
        service = get_generation_service()
        return await asyncio.to_thread(service.crear_sesion, params, current_user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
