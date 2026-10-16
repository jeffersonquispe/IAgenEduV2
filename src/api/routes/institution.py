# src/api/routes/institution.py
"""
HU-31: perfil institucional del docente.
HU-48: subida y consulta de la plantilla institucional (Unidad/Sesión).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .auth import get_current_user
from ...core.template_parser import parsear_plantilla
from ...core.control_documentario import normalizar_control
from ...core.valores_institucionales import listar_presets
from ..services.perfil_control import proteger_control

router = APIRouter(prefix="/institucion", tags=["institucion"])

_TIPOS_VALIDOS = ("unidad", "sesion")


def _proteger_control(db: Session, perfil) -> None:
    """HU-47: si la migración 20261009_institution_control_documentario.sql todavía no se aplicó,
    se responde con `None` en vez de romper la pantalla (ver services/perfil_control.py)."""
    proteger_control(db, perfil)


@router.get("", response_model=schemas.InstitutionProfile)
def get_perfil_institucional(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perfil = db.query(models.InstitutionProfile).filter(
        models.InstitutionProfile.user_id == current_user.id
    ).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil institucional no configurado")
    _proteger_control(db, perfil)
    return perfil


@router.get("/presets-valores")
def get_presets_valores(current_user: models.User = Depends(get_current_user)):
    """HU-36: listas de valores sugeridas que el docente puede elegir de forma explícita
    (p. ej. la de una institución católica). Elegir una solo rellena el formulario: se
    guarda como valores propios del perfil cuando el docente pulsa Guardar."""
    return listar_presets()


@router.put("", response_model=schemas.InstitutionProfile)
def upsert_perfil_institucional(
    payload: schemas.InstitutionProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza el perfil institucional. El perfil es opcional: un
    docente sin perfil configurado sigue generando documentos exactamente
    igual que hoy (ver resolver_valores_institucionales() en
    valores_institucionales.py, que ya tolera institution_profile=None)."""
    perfil = db.query(models.InstitutionProfile).filter(
        models.InstitutionProfile.user_id == current_user.id
    ).first()
    if not perfil:
        perfil = models.InstitutionProfile(user_id=current_user.id)
        db.add(perfil)

    datos = payload.model_dump(exclude_unset=True)
    if "control_documentario" in datos:
        # Se guarda limpio (sin campos vacíos); None si el docente lo vació por completo.
        datos["control_documentario"] = normalizar_control(datos["control_documentario"]) or None
    for campo, valor in datos.items():
        setattr(perfil, campo, valor)
    perfil.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(perfil)
    _proteger_control(db, perfil)
    return perfil


@router.post("/plantilla", response_model=schemas.DocumentTemplateSummary)
async def subir_plantilla(
    tipo: str = Form(...),
    archivo: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sube la plantilla .docx (silueta) de Unidad o Sesión. Reemplaza la
    plantilla activa anterior del mismo tipo para generaciones futuras; no
    altera documentos ya generados con la plantilla previa (HU-48)."""
    if tipo not in _TIPOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"tipo debe ser uno de {_TIPOS_VALIDOS}")
    if not archivo.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=422, detail="El archivo debe ser un .docx")

    contenido = await archivo.read()
    try:
        esquema = parsear_plantilla(contenido)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    db.query(models.DocumentTemplate).filter(
        models.DocumentTemplate.user_id == current_user.id,
        models.DocumentTemplate.tipo == tipo,
        models.DocumentTemplate.activa.is_(True),
    ).update({"activa": False})

    nueva = models.DocumentTemplate(
        user_id=current_user.id,
        tipo=tipo,
        nombre_archivo=archivo.filename,
        archivo_original=contenido,
        esquema=esquema.to_dict(),
        activa=True,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.get("/plantilla/{tipo}", response_model=schemas.DocumentTemplateSummary)
def obtener_plantilla_activa(
    tipo: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if tipo not in _TIPOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"tipo debe ser uno de {_TIPOS_VALIDOS}")

    plantilla = db.query(models.DocumentTemplate).filter(
        models.DocumentTemplate.user_id == current_user.id,
        models.DocumentTemplate.tipo == tipo,
        models.DocumentTemplate.activa.is_(True),
    ).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="No hay plantilla activa para este tipo")
    return plantilla


@router.delete("/plantilla/{tipo}")
def desactivar_plantilla(
    tipo: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Vuelve al comportamiento por defecto (prompts .md fijos) para este tipo de documento."""
    if tipo not in _TIPOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"tipo debe ser uno de {_TIPOS_VALIDOS}")

    actualizadas = db.query(models.DocumentTemplate).filter(
        models.DocumentTemplate.user_id == current_user.id,
        models.DocumentTemplate.tipo == tipo,
        models.DocumentTemplate.activa.is_(True),
    ).update({"activa": False})
    db.commit()
    return {"desactivadas": actualizadas}
