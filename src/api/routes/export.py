from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from ...core.pdf_generator import generar_pdf_unidad, generar_pdf_sesion
from ...core.markdown_table import parse_markdown_table
import os
import tempfile

router = APIRouter(prefix="/export", tags=["export"])

# Campos de contenido real por tipo de documento; cualquier otra clave del
# payload (done, id, type, contenido_crudo, ...) es metadata del evento SSE
# del streaming y no debe aparecer en el documento exportado.
_CONTENT_FIELDS = {
    "situacion_significativa", "propositos_de_aprendizaje",
    "valores_y_enfoques_transversales", "secuencia_de_sesiones", "rubrica_unidad",
    "datos_informativos", "secuencia_didactica",
    "reflexion_sobre_la_actividad", "rubrica_sesion",
}


def _filtrar_contenido_exportable(data: dict) -> dict:
    filtrado = {k: v for k, v in data.items() if k in _CONTENT_FIELDS and v}
    filtrado["titulo"] = data.get("titulo", "Documento")
    return filtrado


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
        data = _filtrar_contenido_exportable(data)
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

            tabla = parse_markdown_table(str(v))
            if tabla:
                word_table = doc.add_table(rows=len(tabla), cols=len(tabla[0]))
                word_table.style = "Light Grid Accent 1"
                for fila_idx, fila in enumerate(tabla):
                    for col_idx, celda in enumerate(fila):
                        word_table.cell(fila_idx, col_idx).text = celda
            else:
                doc.add_paragraph(str(v))
        doc.save(filepath)
        
        if current_user.stats:
            current_user.stats.exportaciones_docx += 1
            db.commit()
            
        return FileResponse(filepath, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename=f"{data.get('titulo', 'documento')}.docx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
