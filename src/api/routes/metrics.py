# src/api/routes/metrics.py
"""
Endpoints de métricas del pipeline de generación.
Proporciona datos estadísticos útiles para análisis e investigación.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from typing import List, Dict, Any

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
async def get_metrics_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Resumen global de métricas del pipeline para el usuario actual.
    Incluye promedio de puntaje, distribución de errores, áreas más usadas.
    """
    runs = db.query(models.PipelineRun).filter(
        models.PipelineRun.document_id.in_(
            db.query(models.Document.id).filter(models.Document.user_id == current_user.id)
        )
    ).all()

    if not runs:
        return {
            "total_generaciones": 0,
            "promedio_puntaje": 0,
            "promedio_duracion_ms": 0,
            "total_correcciones": 0,
            "areas_top": [],
            "metodologias": [],
            "distribucion_tipo": {"unidad": 0, "sesion": 0},
        }

    total = len(runs)
    promedio_puntaje = round(sum(r.puntaje_validacion for r in runs) / total, 1)
    promedio_duracion = round(sum(r.duracion_ms for r in runs) / total)
    total_correcciones = sum(r.correcciones_aplicadas for r in runs)

    # Áreas más usadas
    areas_counter: Dict[str, int] = {}
    for r in runs:
        if r.area_curricular:
            areas_counter[r.area_curricular] = areas_counter.get(r.area_curricular, 0) + 1
    areas_top = sorted(
        [{"area": k, "count": v} for k, v in areas_counter.items()],
        key=lambda x: x["count"], reverse=True
    )[:5]

    # Metodologías usadas
    metod_counter: Dict[str, int] = {}
    for r in runs:
        if r.metodologia:
            metod_counter[r.metodologia] = metod_counter.get(r.metodologia, 0) + 1
    metodologias = [{"metodologia": k, "count": v} for k, v in metod_counter.items()]

    # Distribución por tipo
    unidades = sum(1 for r in runs if r.tipo == "unidad")
    sesiones = sum(1 for r in runs if r.tipo == "sesion")

    return {
        "total_generaciones": total,
        "promedio_puntaje": promedio_puntaje,
        "promedio_duracion_ms": promedio_duracion,
        "total_correcciones": total_correcciones,
        "areas_top": areas_top,
        "metodologias": metodologias,
        "distribucion_tipo": {"unidad": unidades, "sesion": sesiones},
    }


@router.get("/runs")
async def get_pipeline_runs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Últimas 50 ejecuciones del pipeline para el usuario actual."""
    runs = db.query(models.PipelineRun).filter(
        models.PipelineRun.document_id.in_(
            db.query(models.Document.id).filter(models.Document.user_id == current_user.id)
        )
    ).order_by(models.PipelineRun.timestamp.desc()).limit(50).all()

    return [
        {
            "id": r.id,
            "document_id": r.document_id,
            "tipo": r.tipo,
            "area_curricular": r.area_curricular,
            "grado": r.grado,
            "metodologia": r.metodologia,
            "puntaje_validacion": r.puntaje_validacion,
            "errores_criticos": r.errores_criticos,
            "errores_advertencia": r.errores_advertencia,
            "correcciones_aplicadas": r.correcciones_aplicadas,
            "tokens_aprox": r.tokens_aprox,
            "duracion_ms": r.duracion_ms,
            "llm_model": r.llm_model,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in runs
    ]


@router.get("/document/{doc_id}/versions")
async def get_document_versions(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lista de versiones de un documento específico."""
    # Verificar propiedad
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id,
    ).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    versions = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == doc_id
    ).order_by(models.DocumentVersion.version_num.desc()).all()

    return [
        {
            "id": v.id,
            "version_num": v.version_num,
            "change_label": v.change_label,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.post("/document/{doc_id}/restore/{version_num}")
async def restore_document_version(
    doc_id: str,
    version_num: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Restaura el contenido de un documento a una versión anterior."""
    from fastapi import HTTPException

    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == doc_id,
        models.DocumentVersion.version_num == version_num,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versión no encontrada")

    # Guardar estado actual como nueva versión antes de restaurar
    next_version = (doc.current_version or 1) + 1
    snapshot = models.DocumentVersion(
        document_id=doc_id,
        version_num=next_version,
        content=doc.content,
        change_label=f"Antes de restaurar v{version_num}",
    )
    db.add(snapshot)

    # Restaurar
    doc.content = version.content
    doc.current_version = next_version
    db.commit()
    db.refresh(doc)

    return {"message": f"Documento restaurado a versión {version_num}", "content": doc.content}
