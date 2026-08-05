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
    # Unidad (streaming SSE)
    # ------------------------------------------------------------------

    def generar_unidad_stream_events(self, params: Dict[str, Any], current_user: models.User,
                                      db: Session) -> Generator[str, None, None]:
        """
        Genera una unidad didáctica con streaming SSE.
        Yields líneas `data: {...}\n\n` — chunks de texto, validación, y resultado final con secciones.

        Parámetro `modo`:
        - "solo_generador": rápido, solo GeneratorAgent, sin validación
        - "completo" (default): GeneratorAgent + ValidatorAgent + FormatterAgent
        """
        from ...agents.generator_agent import GeneratorAgent
        from ...agents.coordinator import get_coordinator

        area = params.get("area", "")
        grado = params.get("grado", "")
        competencias = params.get("competencias", [])
        competencias_texto = ", ".join(competencias) if isinstance(competencias, list) else competencias
        producto_final = params.get("producto_final", "")
        num_sesiones = int(params.get("num_sesiones", 6))
        temas = params.get("temas", "")
        modo = params.get("modo", "completo")

        gen = GeneratorAgent()
        prompt = gen.construir_prompt_unidad(
            area_curricular=area,
            grado=grado,
            competencia_referencia=competencias_texto,
            temas=temas,
            num_sesiones=num_sesiones,
            producto_final=producto_final,
        )

        doc_id = str(uuid.uuid4())
        bedrock = gen.bedrock

        full_text = ""
        metricas = None
        try:
            for chunk in bedrock.invocar_stream(prompt):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            if modo == "completo":
                yield f"data: {json.dumps({'validando': True})}\n\n"
                coordinator = get_coordinator(usar_validacion_llm=True)
                contenido_final, metricas = coordinator.validar_y_formatear_unidad(
                    contenido=full_text,
                    area_curricular=area,
                    grado=grado,
                )
            else:
                contenido_final = full_text

            doc_content = self._unidad_parser.parsear(contenido_final, area=area)

            # Fallback: si el parser retorna campos vacíos, use contenido_final directamente
            if not any([doc_content.get(k, '').strip() for k in ['situacion_significativa', 'propositos_de_aprendizaje', 'secuencia_de_sesiones']]):
                print(f"[WARNING] Parser retornó campos vacíos para Unidad, usando fallback")
                doc_content = {
                    "titulo": f"Unidad Didáctica - {area}",
                    "situacion_significativa": contenido_final[:500] if contenido_final else "",
                    "propositos_de_aprendizaje": contenido_final[500:1500] if len(contenido_final) > 500 else "",
                    "secuencia_de_sesiones": contenido_final[1500:] if len(contenido_final) > 1500 else "",
                    "rubrica_unidad": "",
                }
            new_doc = models.Document(
                id=doc_id, user_id=current_user.id, type="unidad",
                title=f"Unidad Didáctica - {area}", content=doc_content, current_version=1,
            )
            db.add(new_doc)

            if current_user.stats:
                current_user.stats.docs_generados = (current_user.stats.docs_generados or 0) + 1
                current_user.stats.unidades_generadas = (current_user.stats.unidades_generadas or 0) + 1
            db.commit()

            self._save_version(db, doc_id, doc_content, f"Generación inicial (streaming, modo={modo})", 1)
            if metricas:
                self._save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado))

            yield f"data: {json.dumps({'done': True, 'id': doc_id, **doc_content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"

    # ------------------------------------------------------------------
    # Sesión (streaming SSE)
    # ------------------------------------------------------------------

    def generar_sesion_stream_events(self, params: Dict[str, Any], current_user: models.User,
                                      db: Session) -> Generator[str, None, None]:
        """
        Genera una sesión de aprendizaje con streaming SSE.
        Yields líneas `data: {...}\n\n` — chunks de texto, validación, y resultado final con secciones.

        Parámetro `modo`:
        - "solo_generador": rápido, solo GeneratorAgent, sin validación
        - "completo" (default): GeneratorAgent + ValidatorAgent + FormatterAgent
        """
        from ...agents.generator_agent import GeneratorAgent
        from ...agents.coordinator import get_coordinator

        area = params.get("area", "")
        grado = params.get("grado", "")
        titulo_unidad = params.get("titulo_unidad", "")
        tema_sesion = params.get("tema", "")
        metodologia = params.get("metodologia", "")
        nivel_educativo = params.get("nivel", "Secundaria")
        modo = params.get("modo", "completo")

        gen = GeneratorAgent()
        prompt = gen.construir_prompt_sesion(
            titulo_unidad=titulo_unidad,
            titulo_sesion=tema_sesion,
            nivel=nivel_educativo,
            grado=str(grado),
            seccion=params.get("seccion", "A"),
            duracion=params.get("duracion", "90 min"),
            competencias_unidad=params.get("propositos", ""),
            tema=tema_sesion,
            metodologia=metodologia,
        )

        doc_id = str(uuid.uuid4())
        bedrock = gen.bedrock

        full_text = ""
        metricas = None
        try:
            for chunk in bedrock.invocar_stream(prompt):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

            if modo == "completo":
                yield f"data: {json.dumps({'validando': True})}\n\n"
                coordinator = get_coordinator(usar_validacion_llm=True)
                contenido_final, metricas = coordinator.validar_y_formatear_sesion(
                    contenido=full_text,
                    grado=str(grado),
                    metodologia=metodologia,
                )
            else:
                contenido_final = full_text

            doc_content = self._sesion_parser.parsear(contenido_final, tema_sesion=tema_sesion)

            new_doc = models.Document(
                id=doc_id, user_id=current_user.id, type="sesion",
                title=f"Sesión - {tema_sesion}", content=doc_content, current_version=1,
            )
            db.add(new_doc)

            if current_user.stats:
                current_user.stats.docs_generados = (current_user.stats.docs_generados or 0) + 1
                current_user.stats.sesiones_generadas = (current_user.stats.sesiones_generadas or 0) + 1
            db.commit()

            self._save_version(db, doc_id, doc_content, f"Generación inicial (streaming, modo={modo})", 1)
            if metricas:
                self._save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado), metod=metodologia)

            yield f"data: {json.dumps({'done': True, 'id': doc_id, **doc_content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"

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
