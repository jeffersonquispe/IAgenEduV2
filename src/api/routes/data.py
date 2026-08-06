from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from typing import List
from ...core.competencias_curriculares import (
    AREAS_CURRICULARES_SECUNDARIA,
    GRADOS_SECUNDARIA,
    obtener_lista_competencias_formateada,
    obtener_competencias_por_area,
    obtener_temas_por_area_y_grado,
    TEMAS_POR_AREA_Y_GRADO,
)

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/options")
async def get_curriculum_options():
    return {
        "areas": AREAS_CURRICULARES_SECUNDARIA,
        "grados": GRADOS_SECUNDARIA,
        "competencias": obtener_lista_competencias_formateada(),
        "temas_por_area": TEMAS_POR_AREA_Y_GRADO,
    }


@router.get("/competencias")
async def get_competencias_by_area(area: str = Query(..., description="Área curricular")):
    """
    Devuelve solo las competencias correspondientes al área curricular indicada.
    El frontend usa esto para filtrar el selector de competencias.
    """
    comps = obtener_competencias_por_area(area)
    return [
        {"numero": c["numero"], "nombre": c["nombre"]}
        for c in comps
    ]


@router.get("/temas")
async def get_temas_by_area_grado(
    area: str = Query(..., description="Área curricular"),
    grado: str = Query(..., description="Grado (1°, 2°, ...)"),
):
    """Devuelve temas sugeridos para el área y grado seleccionados."""
    temas = obtener_temas_por_area_y_grado(area, grado)
    return {"temas": temas}


@router.get("/documents")
async def get_user_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    docs = db.query(models.Document).filter(
        models.Document.user_id == current_user.id
    ).order_by(models.Document.created_at.desc()).limit(10).all()

    return [
        {
            "id": d.id,
            "title": d.title,
            "type": d.type,
            "created_at": d.created_at,
            "content": d.content,
        }
        for d in docs
    ]


@router.get("/unidades")
async def get_user_unidades(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Unidades Didácticas del usuario, para el selector de "unidad padre" al
    crear una Sesión (HU-22) — reemplaza el campo de texto libre donde el
    docente retipeaba el título a mano.
    """
    unidades = db.query(models.Document).filter(
        models.Document.user_id == current_user.id,
        models.Document.type == "unidad",
    ).order_by(models.Document.created_at.desc()).all()

    return [
        {
            "id": u.id,
            "title": u.title,
            "propositos_de_aprendizaje": (u.content or {}).get("propositos_de_aprendizaje", ""),
            "created_at": u.created_at,
        }
        for u in unidades
    ]
