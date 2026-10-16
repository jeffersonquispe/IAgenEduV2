from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from ...core.pdf_generator import generar_pdf_unidad, generar_pdf_sesion
from ...core.docx_export import generar_docx
from ...core.control_documentario import construir_control
from ...core.campos_documento import CAMPOS_DE_CONTENIDO, ordenar_secciones
from ..services.perfil_control import proteger_control
from ...core.template_parser import rellenar_plantilla_docx
import os
import tempfile

router = APIRouter(prefix="/export", tags=["export"])

# Campos de contenido real por tipo de documento; cualquier otra clave del
# payload (done, id, type, contenido_crudo, ...) es metadata del evento SSE
# del streaming y no debe aparecer en el documento exportado.
_CONTENT_FIELDS = CAMPOS_DE_CONTENIDO     # fuente única en core/campos_documento.py


def _filtrar_contenido_exportable(data: dict) -> dict:
    filtrado = ordenar_secciones({k: v for k, v in data.items() if k in _CONTENT_FIELDS and v})
    filtrado["titulo"] = data.get("titulo", "Documento")
    return filtrado


def _detectar_tipo(data: dict) -> str:
    """Mismo criterio que ya usaba /pdf para distinguir Unidad de Sesión,
    reutilizado también por /docx (HU-50) para saber qué plantilla buscar."""
    if "situacion_significativa" in data or "secuencia_de_sesiones" in str(data).lower():
        return "unidad"
    return "sesion"


@router.post("/pdf")
async def export_pdf(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        data = _filtrar_contenido_exportable(data)
        temp_dir = tempfile.gettempdir()
        filename = f"document_{current_user.id}_{os.urandom(4).hex()}.pdf"
        filepath = os.path.join(temp_dir, filename)

        # HU-50: la exportación a PDF-desde-plantilla-original no es viable hoy
        # sin un conversor docx->pdf en el servidor (LibreOffice/Word) — se
        # mantiene el generador propio para PDF; DOCX sí reutiliza la
        # plantilla subida (ver /docx más abajo).
        tipo = _detectar_tipo(data)
        # HU-47: encabezado de control documentario si el perfil lo tiene configurado.
        perfil = db.query(models.InstitutionProfile).filter(
            models.InstitutionProfile.user_id == current_user.id
        ).first()
        proteger_control(db, perfil)      # sin la migración de HU-47 no debe romper la transacción
        control = construir_control(perfil, tipo)
        if tipo == "unidad":
            generar_pdf_unidad(data, filepath, control=control)
        else:
            generar_pdf_sesion(data, filepath, control=control)

        if current_user.stats:
            current_user.stats.exportaciones_pdf += 1
            db.commit()

        return FileResponse(filepath, media_type='application/pdf', filename=f"{data.get('titulo', 'documento')}.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/docx")
async def export_docx(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        data = _filtrar_contenido_exportable(data)
        tipo = _detectar_tipo(data)
        temp_dir = tempfile.gettempdir()
        filename = f"document_{current_user.id}_{os.urandom(4).hex()}.docx"
        filepath = os.path.join(temp_dir, filename)

        # HU-50: si el docente tiene una plantilla institucional activa
        # (HU-48) para este tipo de documento, se rellena el .docx ORIGINAL
        # que subió (preserva diseño, logos, encabezado de control
        # documentario) en vez de reconstruir el documento desde cero.
        plantilla = db.query(models.DocumentTemplate).filter(
            models.DocumentTemplate.user_id == current_user.id,
            models.DocumentTemplate.tipo == tipo,
            models.DocumentTemplate.activa.is_(True),
        ).first()

        advertencia = None
        if plantilla:
            contenido_docx, advertencia = rellenar_plantilla_docx(
                archivo_original=plantilla.archivo_original,
                esquema=plantilla.esquema,
                contenido=data,
            )
            with open(filepath, "wb") as f:
                f.write(contenido_docx)
        else:
            # Sin plantilla institucional (HU-23): documento con formato institucional
            # (encabezado, secciones numeradas, tablas con cabecera, pie con numeración).
            perfil = db.query(models.InstitutionProfile).filter(
                models.InstitutionProfile.user_id == current_user.id
            ).first()
            proteger_control(db, perfil)      # ídem: lectura segura de la columna diferida
            with open(filepath, "wb") as f:
                f.write(generar_docx(data, tipo, perfil))

        if current_user.stats:
            current_user.stats.exportaciones_docx += 1
            db.commit()

        headers = {"X-Export-Advertencia": advertencia} if advertencia else None
        return FileResponse(
            filepath, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=f"{data.get('titulo', 'documento')}.docx", headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
