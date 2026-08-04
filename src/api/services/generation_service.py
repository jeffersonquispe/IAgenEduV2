# src/api/services/generation_service.py
"""
Capa de orquestación de la generación de documentos.

Antes vivía inline en routes/generation.py: llamaba al AgentCoordinator,
parseaba el resultado, y persistía Document/DocumentVersion/PipelineRun/
UserStats, todo mezclado con el manejo HTTP. Aquí queda separado en un
service para que los route handlers solo traduzcan HTTP <-> este servicio.

El parseo del contenido crudo por tipo de documento vive en content_parsers.py
(Strategy) — este servicio no conoce el detalle de cómo se parsea cada tipo.
"""
import json
import uuid
from typing import Any, Dict, Generator, Optional

from sqlalchemy.orm import Session

from .. import models
from .content_parsers import SesionContentParser, UnidadContentParser


class GenerationService:
    def __init__(self):
        self._unidad_parser = UnidadContentParser()
        self._sesion_parser = SesionContentParser()

    # ------------------------------------------------------------------
    # Persistencia (antes _save_pipeline_run / _save_version en generation.py)
    # ------------------------------------------------------------------

    def _save_pipeline_run(self, db: Session, doc_id: str, metricas,
                            area: str = "", grado: str = "", metod: str = ""):
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
        except Exception:
            # No fallar la request por un error de métricas
            db.rollback()

    def _save_version(self, db: Session, doc_id: str, content: dict, label: str, next_version: int):
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

    # ------------------------------------------------------------------
    # Unidad (async, no-streaming)
    # ------------------------------------------------------------------

    def crear_unidad(self, params: Dict[str, Any], current_user: models.User, db: Session) -> Dict[str, Any]:
        from ...agents.coordinator import get_coordinator

        area = params.get("area", "")
        grado = params.get("grado", "")
        competencias = params.get("competencias", [])
        competencias_texto = ", ".join(competencias) if isinstance(competencias, list) else competencias
        producto_final = params.get("producto_final", "")

        coordinator = get_coordinator(usar_validacion_llm=True)
        contenido, metricas = coordinator.generar_unidad_didactica(
            area_curricular=area, grado=grado,
            competencia_referencia=competencias_texto, temas=params.get("temas", ""),
            num_sesiones=int(params.get("num_sesiones", 6)), producto_final=producto_final,
        )

        doc_content = self._unidad_parser.parsear(contenido, area=area)

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

        self._save_version(db, doc_id, doc_content, "Generación inicial", 1)
        self._save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado))

        return {**doc_content, "id": doc_id, "contenido_crudo": contenido}

    # ------------------------------------------------------------------
    # Unidad (streaming SSE)
    # ------------------------------------------------------------------

    def generar_unidad_stream_events(self, params: Dict[str, Any], current_user: models.User,
                                      db: Session) -> Generator[str, None, None]:
        """
        Genera una unidad didáctica con streaming SSE.
        Yields líneas `data: {...}\n\n` — chunks de texto y, al final, el id del documento.

        Nota: a diferencia de crear_unidad(), este camino no pasa por
        ValidatorAgent/FormatterAgent (llama directo a Bedrock en streaming) y el
        documento se guarda solo con contenido_crudo, sin secciones parseadas.
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

        full_text = ""
        try:
            for chunk in bedrock.invocar_stream(prompt):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

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

    # ------------------------------------------------------------------
    # Sesión (async)
    # ------------------------------------------------------------------

    def crear_sesion(self, params: Dict[str, Any], current_user: models.User, db: Session) -> Dict[str, Any]:
        from ...agents.coordinator import get_coordinator

        area = params.get("area", "")
        grado = params.get("grado", "")
        tema_sesion = params.get("tema", "")
        metodologia = params.get("metodologia", "")
        nivel_educativo = params.get("nivel", "Secundaria")

        coordinator = get_coordinator(usar_validacion_llm=True)
        contenido, metricas = coordinator.generar_sesion_aprendizaje(
            titulo_unidad=params.get("titulo_unidad", ""), titulo_sesion=tema_sesion,
            nivel=nivel_educativo, grado=str(grado), seccion=params.get("seccion", "A"),
            duracion=params.get("duracion", "90 min"),
            competencias_unidad=params.get("propositos", ""), tema=tema_sesion, metodologia=metodologia,
        )

        doc_content = self._sesion_parser.parsear(contenido, tema_sesion=tema_sesion)

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

        self._save_version(db, doc_id, doc_content, "Generación inicial", 1)
        self._save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado), metod=metodologia)

        return {**doc_content, "id": doc_id}

    # ------------------------------------------------------------------
    # Refinamiento de un campo
    # ------------------------------------------------------------------

    def refinar(self, params: Dict[str, Any], current_user: models.User, db: Session) -> Dict[str, Any]:
        from ...core.bedrock_services import mejorar_documento_con_instruccion

        field_content = params.get("content")
        instruction = params.get("instruction")
        doc_id = params.get("doc_id")  # opcional; si se pasa, guarda versión

        nuevo_contenido = mejorar_documento_con_instruccion(field_content, instruction)

        if doc_id:
            doc = db.query(models.Document).filter(
                models.Document.id == doc_id,
                models.Document.user_id == current_user.id,
            ).first()
            if doc:
                next_v = (doc.current_version or 1) + 1
                self._save_version(db, doc_id, doc.content,
                                    f"Antes de refinar: {instruction[:60]}", next_v)
                doc.current_version = next_v
                db.commit()

        if current_user.stats:
            current_user.stats.mejoras_realizadas = (current_user.stats.mejoras_realizadas or 0) + 1
            db.commit()

        return {"refined_content": nuevo_contenido}


_default_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    global _default_service
    if _default_service is None:
        _default_service = GenerationService()
    return _default_service
