from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from ...core.pdf_generator import generar_pdf_unidad, generar_pdf_sesion
import os
import tempfile

router = APIRouter(prefix="/export", tags=["export"])

@router.post("/pdf")
async def export_pdf(
    data: dict = Body(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        temp_dir = tempfile.gettempdir()
        filename = f"document_{current_user.id}_{os.urandom(4).hex()}.pdf"
        filepath = os.path.join(temp_dir, filename)
        
        # Check if it's Unidad or Sesión based on keys
        if "situacion_significativa" in data or "secuencia_de_sesiones" in str(data).lower():
            generar_pdf_unidad(data, filepath)
        else:
            generar_pdf_sesion(data, filepath)
            
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
    # This would require adapting the existing docx_generator to accept a dict
    # For now, we simulate or use a simplified version
    try:
        temp_dir = tempfile.gettempdir()
        filename = f"document_{current_user.id}_{os.urandom(4).hex()}.docx"
        filepath = os.path.join(temp_dir, filename)
        
        # simplified call to existing generator
        # Note: In a real scenario, we'd ensure docx_generator is perfectly compatible with the frontend dict
        from docx import Document
        doc = Document()
        doc.add_heading(data.get("titulo", "Documento Educativo"), 0)
        for k, v in data.items():
            if k == "titulo": continue
            doc.add_heading(k.replace("_", " ").title(), level=1)
            doc.add_paragraph(str(v))
        doc.save(filepath)
        
        if current_user.stats:
            current_user.stats.exportaciones_docx += 1
            db.commit()
            
        return FileResponse(filepath, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename=f"{data.get('titulo', 'documento')}.docx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
