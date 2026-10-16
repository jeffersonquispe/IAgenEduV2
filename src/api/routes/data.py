import copy
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from typing import Any, Dict, List, Optional
from ...core import ejemplos as biblioteca_ejemplos
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


def _escapar_like(texto: str) -> str:
    """Escapa % y _ para que la búsqueda de texto sea literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def construir_consulta_documentos(
    db: Session,
    user_id,
    type: Optional[str] = None,
    area_curricular: Optional[str] = None,
    grado: Optional[str] = None,
    q: Optional[str] = None,
):
    """HU-24: consulta de documentos del usuario con filtros opcionales.

    Área y grado se guardan en el propio documento, así que el filtro alcanza
    a todos, también a los generados en modo "solo_generador" (que no tienen
    PipelineRun).
    """
    consulta = db.query(models.Document).filter(models.Document.user_id == user_id)
    if type:
        consulta = consulta.filter(models.Document.type == type)
    if area_curricular:
        consulta = consulta.filter(models.Document.area_curricular == area_curricular)
    if grado:
        consulta = consulta.filter(models.Document.grado == grado)
    if q and q.strip():
        consulta = consulta.filter(
            models.Document.title.ilike(f"%{_escapar_like(q.strip())}%", escape="\\")
        )
    return consulta


@router.get("/documents")
async def get_user_documents(
    response: Response,
    type: Optional[str] = Query(None, pattern="^(unidad|sesion)$"),
    area_curricular: Optional[str] = None,
    grado: Optional[str] = None,
    q: Optional[str] = Query(None, max_length=100),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Documentos del usuario, el de actividad más reciente primero. Sin parámetros se
    comporta como antes (últimos 10). El total sin paginar va en el header
    X-Total-Count para no cambiar la forma de la respuesta (lista).

    `updated_at` es la última actividad: la versión más reciente del documento (cada guardado o
    refinado crea una) o, si no tuviera, su fecha de creación. Se deriva de document_versions para
    no requerir una columna nueva en la base."""
    consulta = construir_consulta_documentos(
        db, current_user.id, type=type, area_curricular=area_curricular, grado=grado, q=q,
    )
    response.headers["X-Total-Count"] = str(consulta.count())
    actividad = _ultima_actividad()
    filas = (
        consulta.add_columns(actividad.label("actividad"))
        .order_by(actividad.desc(), models.Document.created_at.desc())
        .offset(offset).limit(limit).all()
    )
    return [_resumen_documento(d, act) for d, act in filas]


def _ultima_actividad():
    """Expresión SQL: fecha de la versión más reciente del documento (o su creación)."""
    ultima_version = (
        select(func.max(models.DocumentVersion.created_at))
        .where(models.DocumentVersion.document_id == models.Document.id)
        .correlate(models.Document)
        .scalar_subquery()
    )
    return func.coalesce(ultima_version, models.Document.created_at)


def _resumen_documento(d: models.Document, actividad=None) -> Dict[str, Any]:
    return {
        "id": d.id,
        "title": d.title,
        "type": d.type,
        "created_at": d.created_at,
        "updated_at": actividad or d.created_at,
        "current_version": d.current_version or 1,
        "area_curricular": d.area_curricular,
        "grado": d.grado,
        "content": d.content,
    }


def _documento_propio(db: Session, doc_id: str, user_id) -> models.Document:
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id, models.Document.user_id == user_id,
    ).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


MAX_LARGO_TITULO = 200
PREFIJO_COPIA = "Copia de "


@router.post("/documents/{doc_id}/duplicate", status_code=201)
async def duplicar_documento(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Crea una copia independiente (versión 1, sin historial) de un documento propio.

    Sirve para partir de una unidad o sesión ya revisada sin tocar el original. No cuenta como
    generación: no pasa por la IA ni suma puntos o estadísticas."""
    original = _documento_propio(db, doc_id, current_user.id)
    contenido = copy.deepcopy(original.content or {})
    titulo = (PREFIJO_COPIA + (original.title or "Documento"))[:MAX_LARGO_TITULO]
    if isinstance(contenido.get("titulo"), str):
        contenido["titulo"] = titulo
    copia = models.Document(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        type=original.type,
        title=titulo,
        content=contenido,
        current_version=1,
        parent_document_id=original.parent_document_id,
        area_curricular=original.area_curricular,
        grado=original.grado,
    )
    try:
        db.add(copia)
        db.flush()
        db.add(models.DocumentVersion(
            document_id=copia.id, version_num=1, content=contenido, change_label="Copia de otro documento",
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(copia)
    return _resumen_documento(copia)


@router.delete("/documents/{doc_id}", status_code=204)
async def eliminar_documento(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Elimina un documento propio y su historial de versiones.

    Lo que lo referencia se conserva desvinculado: las métricas de generación (pipeline_runs, útiles
    para la evaluación), los trabajos de generación terminados y las sesiones que colgaban de una
    unidad eliminada. Es irreversible."""
    doc = _documento_propio(db, doc_id, current_user.id)
    try:
        db.query(models.PipelineRun).filter(models.PipelineRun.document_id == doc.id).update(
            {models.PipelineRun.document_id: None}, synchronize_session=False)
        db.query(models.GenerationJob).filter(models.GenerationJob.result_document_id == doc.id).update(
            {models.GenerationJob.result_document_id: None}, synchronize_session=False)
        db.query(models.Document).filter(models.Document.parent_document_id == doc.id).update(
            {models.Document.parent_document_id: None}, synchronize_session=False)
        db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).delete(
            synchronize_session=False)
        db.delete(doc)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return Response(status_code=204)


@router.put("/documents/{doc_id}")
async def guardar_documento(
    doc_id: str,
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Guarda las secciones editadas en el Editor y registra una versión nueva.

    Body: {content: {campo: texto}, base_version?: int}. Con `base_version`, si el documento
    cambió desde esa versión (p. ej. se guardó en otra pestaña) responde 409 en vez de
    pisar el cambio ajeno.
    """
    from ..services.generation_service import ConflictoDeVersion, get_generation_service

    try:
        return get_generation_service().guardar_cambios(db, current_user, doc_id, params)
    except LookupError:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except ConflictoDeVersion as e:
        raise HTTPException(status_code=409, detail={
            "code": "version_conflict",
            "version_actual": e.version_actual,
            "message": "Este documento cambió en otra pestaña o sesión. Recárgalo para ver la última versión.",
        })
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/ejemplos")
async def listar_ejemplos(current_user: models.User = Depends(get_current_user)):
    """HU-44: ejemplos completos de Unidad y Sesión (resumen de cada uno). Solo lee
    archivos: no consume el pipeline de IA, no escribe en la base de datos ni cuenta
    para la gamificación."""
    return biblioteca_ejemplos.listar_ejemplos()


@router.get("/ejemplos/{ejemplo_id}")
async def obtener_ejemplo(ejemplo_id: str, current_user: models.User = Depends(get_current_user)):
    """HU-44: un ejemplo con su contenido, en la misma forma que Document.content."""
    ejemplo = biblioteca_ejemplos.obtener_ejemplo(ejemplo_id)
    if ejemplo is None:
        raise HTTPException(status_code=404, detail="Ejemplo no encontrado")
    return ejemplo


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
