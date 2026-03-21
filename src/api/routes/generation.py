from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from ..database import get_db
from ..routes.auth import get_current_user
from .. import models
from ...core.bedrock_services import (
    generar_unidad_didactica,
    generar_sesion_aprendizaje,
    mejorar_documento_con_instruccion,
)
import asyncio
import json
import os
import uuid

router = APIRouter(prefix="/generate", tags=["generation"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extraer_rubrica(contenido: str) -> str:
    """Extrae la tabla de rúbrica del contenido generado."""
    if not contenido:
        return ""
    lineas = contenido.split("\n")
    rubrica_lineas = []
    en_rubrica = False
    for linea in lineas:
        l_upper = linea.upper()
        if (("| CRITERIO" in l_upper or "CRITERIO DE EVALUACI" in l_upper)
                and ("INICIO" in l_upper or " AD " in l_upper or "DESTACADO" in l_upper
                     or "LOGRADO" in l_upper or "PROCESO" in l_upper)):
            en_rubrica = True
        if en_rubrica:
            if linea.strip().startswith("|"):
                rubrica_lineas.append(linea)
            elif rubrica_lineas and not linea.strip():
                rubrica_lineas.append(linea)
            elif rubrica_lineas and not linea.strip().startswith("|"):
                break
    return "\n".join(rubrica_lineas).strip()


def _save_pipeline_run(db: Session, doc_id: str, metricas, area: str = "", grado: str = "", metod: str = ""):
    """Persiste un PipelineRun en la base de datos."""
    try:
        run = models.PipelineRun(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            tipo=metricas.tipo if metricas else "desconocido",
            area_curricular=area,
            grado=grado,
            metodologia=metod,
            puntaje_validacion=getattr(metricas, "puntaje_validacion", 0),
            errores_criticos=getattr(metricas, "errores_criticos", 0),
            errores_advertencia=getattr(metricas, "errores_advertencia", 0),
            correcciones_aplicadas=getattr(metricas, "correcciones_aplicadas", 0),
            tokens_aprox=getattr(metricas, "tokens_aprox", 0),
            duracion_ms=getattr(metricas, "duracion_ms", 0),
            llm_model=getattr(metricas, "llm_model", ""),
        )
        db.add(run)
        db.commit()
    except Exception as e:
        # No fallar la request por un error de métricas
        db.rollback()


def _save_version(db: Session, doc_id: str, content: dict, label: str, next_version: int):
    """Guarda un snapshot del documento como DocumentVersion."""
    try:
        v = models.DocumentVersion(
            document_id=doc_id,
            version_num=next_version,
            content=content,
            change_label=label,
        )
        db.add(v)
        db.commit()
    except Exception:
        db.rollback()


# ---------------------------------------------------------------------------
# Generate Unidad (standard, async)
# ---------------------------------------------------------------------------

@router.post("/unidad")
async def create_unidad(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Genera una unidad didáctica completa (async, no bloqueante)."""
    try:
        from ...app.docx_parsers import (
            extraer_situacion_significativa_completa,
            extraer_propositos_completo,
            extraer_valores_enfoques_transversales,
            extraer_secuencia_sesiones,
        )

        area = params.get("area", "")
        grado = params.get("grado", "")
        competencias = params.get("competencias", [])
        competencias_texto = ", ".join(competencias) if isinstance(competencias, list) else competencias
        producto_final = params.get("producto_final", "")

        # Llamada async: no bloquea el event loop
        contenido, metricas = await asyncio.to_thread(
            _run_unidad,
            area, grado, competencias_texto,
            params.get("temas", ""),
            int(params.get("num_sesiones", 6)),
            producto_final,
        )

        # Parsear secciones
        situacion_extr = extraer_situacion_significativa_completa(contenido)
        propositos_extr = extraer_propositos_completo(contenido)
        valores_dict = extraer_valores_enfoques_transversales(contenido)
        sesiones_list = extraer_secuencia_sesiones(contenido)
        rubrica_unidad = _extraer_rubrica(contenido)

        secuencia_sesiones_str = ""
        for i, ses in enumerate(sesiones_list):
            if ses.get("titulo"):
                secuencia_sesiones_str += (
                    f"Sesión {i+1}: {ses.get('titulo')}\n"
                    f"Criterio: {ses.get('criterio')}\n"
                    f"Actividades: {ses.get('actividades')}\n\n"
                )

        doc_content = {
            "titulo": f"Unidad Didáctica - {area}",
            "situacion_significativa": situacion_extr,
            "propositos_de_aprendizaje": propositos_extr,
            "valores_y_enfoques_transversales": (
                f"Valores: {valores_dict.get('valores')}\n\nEnfoques: {valores_dict.get('enfoques_transversales')}"
            ),
            "secuencia_de_sesiones": secuencia_sesiones_str,
            "rubrica_unidad": rubrica_unidad,
        }

        doc_id = str(uuid.uuid4())
        new_doc = models.Document(
            id=doc_id, user_id=current_user.id, type="unidad",
            title=f"Unidad Didáctica - {area}", content=doc_content, current_version=1,
        )
        db.add(new_doc)

        if current_user.stats:
            current_user.stats.docs_generados = (current_user.stats.docs_generados or 0) + 1
            current_user.stats.unidades_generadas = (current_user.stats.unidades_generadas or 0) + 1
        db.commit()

        # Guardar versión inicial + métricas
        _save_version(db, doc_id, doc_content, "Generación inicial", 1)
        _save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado))

        return {**doc_content, "id": doc_id, "contenido_crudo": contenido}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_unidad(area, grado, competencias_texto, temas, num_sesiones, producto_final):
    """Wrapper sincrónico para uso con asyncio.to_thread."""
    from ...agents.coordinator import get_coordinator
    coordinator = get_coordinator(usar_validacion_llm=True)
    return coordinator.generar_unidad_didactica(
        area_curricular=area, grado=grado,
        competencia_referencia=competencias_texto, temas=temas,
        num_sesiones=num_sesiones, producto_final=producto_final,
    )


# ---------------------------------------------------------------------------
# Generate Unidad STREAM
# ---------------------------------------------------------------------------

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
    from ...core.bedrock_client import get_bedrock_client
    from ...core.prompt_manager import get_prompt_manager
    from ...agents.generator_agent import GeneratorAgent, VALORES_PERMITIDOS, ENFOQUES_TRANSVERSALES_PERMITIDOS

    area = params.get("area", "")
    grado = params.get("grado", "")
    competencias = params.get("competencias", [])
    competencias_texto = ", ".join(competencias) if isinstance(competencias, list) else competencias
    producto_final = params.get("producto_final", "")
    num_sesiones = int(params.get("num_sesiones", 6))
    temas = params.get("temas", "")

    # Construir prompt igual que GeneratorAgent
    gen = GeneratorAgent()
    contexto_competencia = gen._construir_contexto_competencia(competencias_texto, area, grado)
    contexto_temas = f"\nTEMAS ESPECÍFICOS A INCLUIR:\n{temas}\n" if temas else ""
    contexto_sesiones = (
        f"\nNÚMERO DE SESIONES: EXACTAMENTE {num_sesiones} sesiones, "
        f"numeradas del 1 al {num_sesiones}.\n"
    )
    contexto_producto = (
        f"\nPRODUCTO FINAL DE UNIDAD (OBLIGATORIO):\n{producto_final}\n"
        f"La rúbrica DEBE evaluar dimensiones de este producto.\n"
    ) if producto_final else ""

    pm = get_prompt_manager()
    prompt = pm.cargar(
        "unidad_didactica",
        area_curricular=area, grado=grado,
        contexto_competencia=contexto_competencia,
        contexto_temas=contexto_temas, contexto_sesiones=contexto_sesiones,
        contexto_producto=contexto_producto, num_sesiones=num_sesiones,
        valores_texto=", ".join(VALORES_PERMITIDOS),
        enfoques_texto="; ".join(ENFOQUES_TRANSVERSALES_PERMITIDOS),
    )

    doc_id = str(uuid.uuid4())
    bedrock = get_bedrock_client()

    def event_generator():
        full_text = ""
        try:
            for chunk in bedrock.invocar_stream(prompt):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            # Guardar en BD tras completar el stream
            doc_content = {"titulo": f"Unidad Didáctica - {area}", "contenido_crudo": full_text}
            new_doc = models.Document(
                id=doc_id, user_id=current_user.id, type="unidad",
                title=f"Unidad Didáctica - {area}", content=doc_content, current_version=1,
            )
            db.add(new_doc)
            db.commit()

            yield f"data: {json.dumps({'done': True, 'id': doc_id})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Generate Sesión (async)
# ---------------------------------------------------------------------------

@router.post("/sesion")
async def create_sesion(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Genera una sesión de aprendizaje (async, no bloqueante)."""
    try:
        area = params.get("area", "")
        grado = params.get("grado", "")
        tema_sesion = params.get("tema", "")
        metodologia = params.get("metodologia", "")
        nivel_educativo = params.get("nivel", "Secundaria")

        contenido, metricas = await asyncio.to_thread(
            _run_sesion,
            params.get("titulo_unidad", ""), tema_sesion, nivel_educativo,
            grado, params.get("seccion", "A"), params.get("duracion", "90 min"),
            params.get("propositos", ""), tema_sesion, metodologia,
        )

        # Parsear secciones
        datos_informativos = propositos_ap = secuencia_didactica = reflexion = ""
        current_section = "datos"
        for line in contenido.split("\n"):
            lu = line.upper()
            if "DATOS INFORMATIVOS" in lu:
                current_section = "datos"
            elif "PROPÓSITOS DE APRENDIZAJE" in lu or "II. PROP" in lu:
                current_section = "propositos"
            elif "SECUENCIA DIDÁCTICA" in lu or "III. SECU" in lu:
                current_section = "secuencia"
            elif "REFLEXIÓN" in lu or "IV. REFLEX" in lu:
                current_section = "reflexion"
            else:
                if current_section == "datos":
                    datos_informativos += line + "\n"
                elif current_section == "propositos":
                    propositos_ap += line + "\n"
                elif current_section == "secuencia":
                    secuencia_didactica += line + "\n"
                elif current_section == "reflexion":
                    reflexion += line + "\n"

        rubrica_sesion = _extraer_rubrica(contenido)

        doc_content = {
            "titulo": f"Sesión - {tema_sesion}",
            "datos_informativos": datos_informativos.strip(),
            "propositos_de_aprendizaje": propositos_ap.strip(),
            "secuencia_didactica": secuencia_didactica.strip(),
            "reflexion_sobre_la_actividad": reflexion.strip(),
            "rubrica_sesion": rubrica_sesion,
            "contenido_crudo": contenido,
        }

        doc_id = str(uuid.uuid4())
        new_doc = models.Document(
            id=doc_id, user_id=current_user.id, type="sesion",
            title=f"Sesión - {tema_sesion}", content=doc_content, current_version=1,
        )
        db.add(new_doc)

        if current_user.stats:
            current_user.stats.docs_generados = (current_user.stats.docs_generados or 0) + 1
            current_user.stats.sesiones_generadas = (current_user.stats.sesiones_generadas or 0) + 1
        db.commit()

        _save_version(db, doc_id, doc_content, "Generación inicial", 1)
        _save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado), metod=metodologia)

        return {**doc_content, "id": doc_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_sesion(titulo_unidad, titulo_sesion, nivel, grado, seccion, duracion,
               competencias_unidad, tema, metodologia):
    from ...agents.coordinator import get_coordinator
    coordinator = get_coordinator(usar_validacion_llm=True)
    return coordinator.generar_sesion_aprendizaje(
        titulo_unidad=titulo_unidad, titulo_sesion=titulo_sesion,
        nivel=nivel, grado=str(grado), seccion=seccion, duracion=duracion,
        competencias_unidad=competencias_unidad, tema=tema, metodologia=metodologia,
    )


# ---------------------------------------------------------------------------
# Refine field (with versioning)
# ---------------------------------------------------------------------------

@router.post("/refine")
async def refine_field(
    params: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Refina un campo con IA y guarda versión anterior del documento."""
    field_content = params.get("content")
    instruction = params.get("instruction")
    doc_id = params.get("doc_id")  # opcional; si se pasa, guarda versión

    try:
        nuevo_contenido = await asyncio.to_thread(
            mejorar_documento_con_instruccion, field_content, instruction
        )

        # Si se pasa doc_id, guardar snapshot previo
        if doc_id:
            doc = db.query(models.Document).filter(
                models.Document.id == doc_id,
                models.Document.user_id == current_user.id,
            ).first()
            if doc:
                next_v = (doc.current_version or 1) + 1
                _save_version(db, doc_id, doc.content,
                              f"Antes de refinar: {instruction[:60]}", next_v)
                doc.current_version = next_v
                db.commit()

        if current_user.stats:
            current_user.stats.mejoras_realizadas = (current_user.stats.mejoras_realizadas or 0) + 1
            db.commit()

        return {"refined_content": nuevo_contenido}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
