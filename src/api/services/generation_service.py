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
import re
import uuid
from typing import Any, Dict, Generator, Optional

from sqlalchemy.orm import Session

from .. import models
from .content_parsers import SesionContentParser, UnidadContentParser


# HU-45: `Lineamientos.docx` restringe la Unidad a "Competencia (Máximo hasta
# 2 competencias)" — enforced aquí porque el wizard (frontend) puede
# saltearse cualquier validación de UI.
MAX_COMPETENCIAS_UNIDAD = 2


class ConflictoDeVersion(Exception):
    """El documento cambió desde la versión que el cliente tenía (p. ej. se guardó en otra pestaña)."""

    def __init__(self, version_actual: int):
        super().__init__(f"El documento está en la versión {version_actual}.")
        self.version_actual = version_actual

# HU-43: el enlace del recurso previo entra tal cual al prompt y luego a una
# tabla Markdown. Se exige http(s) y se excluyen espacios (evita meter varias
# líneas/instrucciones) y los caracteres que romperían la tabla o el prompt.
MAX_LARGO_RECURSO_PREVIO = 500
_PATRON_RECURSO_PREVIO = re.compile(r"^https?://[^\s<>\"'`{}|\\^]+$", re.IGNORECASE)


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

    def _plantilla_activa(self, db: Session, user_id: str, tipo: str) -> Optional[Dict[str, Any]]:
        """HU-49: esquema de la plantilla institucional activa (HU-48) del
        docente para este tipo de documento, si existe. None conserva el
        comportamiento actual (prompts .md fijos) — sin regresión."""
        plantilla = db.query(models.DocumentTemplate).filter(
            models.DocumentTemplate.user_id == user_id,
            models.DocumentTemplate.tipo == tipo,
            models.DocumentTemplate.activa.is_(True),
        ).first()
        return plantilla.esquema if plantilla else None

    def _perfil_institucional(self, db: Session, user_id: str):
        """HU-32: perfil institucional (HU-31) del docente, o None si no lo configuró.
        Es opcional: sin perfil la generación es exactamente la de antes. Un fallo
        al leerlo nunca debe impedir generar, así que se degrada a None."""
        try:
            return db.query(models.InstitutionProfile).filter(
                models.InstitutionProfile.user_id == user_id
            ).first()
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def normalizar_recurso_previo(valor: Any) -> str:
        """HU-43: devuelve el enlace limpio, "" si no se indicó, o lanza
        ValueError si no es un http(s) válido. La ruta lo traduce a HTTP 422."""
        if valor is None:
            return ""
        if not isinstance(valor, str):
            raise ValueError("El recurso previo debe ser un enlace de texto.")
        valor = valor.strip()
        if not valor:
            return ""
        if len(valor) > MAX_LARGO_RECURSO_PREVIO:
            raise ValueError(
                f"El enlace del recurso previo es demasiado largo (máximo {MAX_LARGO_RECURSO_PREVIO} caracteres)."
            )
        if not _PATRON_RECURSO_PREVIO.match(valor):
            raise ValueError(
                "El recurso previo debe ser un enlace válido que empiece con http:// o https:// y no contenga espacios."
            )
        return valor

    @staticmethod
    def normalizar_datos_informativos(params: Dict[str, Any]) -> Dict[str, Any]:
        """HU-46: valida secciones y fechas de la Unidad; ValueError -> HTTP 422 en la ruta."""
        # Import local, igual que los de agents: con un import `...core` al inicio
        # el módulo no se puede importar como `api.services...` (sin prefijo src).
        from ...core.datos_informativos import normalizar_datos_unidad
        return normalizar_datos_unidad(params)

    @staticmethod
    def validar_limite_competencias(params: Dict[str, Any]) -> None:
        """HU-45: lanza ValueError si la Unidad excede MAX_COMPETENCIAS_UNIDAD.
        La ruta lo traduce a HTTP 422 antes de abrir el stream."""
        competencias = params.get("competencias", [])
        if isinstance(competencias, list) and len(competencias) > MAX_COMPETENCIAS_UNIDAD:
            raise ValueError(
                f"Máximo {MAX_COMPETENCIAS_UNIDAD} competencias por Unidad (elegiste {len(competencias)})."
            )

    @staticmethod
    def _registrar_area_grado(stats, area, grado) -> None:
        """HU-37: acumula áreas/grados distintos usados (insignias Explorador
        y Multi-grado). Reasigna una lista nueva porque las columnas JSON no
        detectan mutaciones in-place."""
        area = str(area).strip() if area else ""
        grado = str(grado).strip() if grado else ""
        areas = list(stats.areas_usadas or [])
        grados = list(stats.grados_usados or [])
        if area and area not in areas:
            stats.areas_usadas = areas + [area]
        if grado and grado not in grados:
            stats.grados_usados = grados + [grado]

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
        try:
            self.validar_limite_competencias(params)
            datos_unidad = self.normalizar_datos_informativos(params)  # HU-46
        except ValueError as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"
            return
        # HU-35: GeneratorAgent._construir_contexto_competencia separa por "\n".
        competencias_texto = "\n".join(competencias) if isinstance(competencias, list) else competencias
        producto_final = params.get("producto_final", "")
        num_sesiones = int(params.get("num_sesiones", 6))
        temas = params.get("temas", "")
        modo = params.get("modo", "completo")

        # HU-49: si el docente tiene una plantilla institucional activa
        # (HU-48) para 'unidad', la generación sigue su estructura exacta en
        # vez del prompt fijo unidad_didactica.md.
        plantilla_esquema = self._plantilla_activa(db, current_user.id, "unidad")
        # HU-32: perfil institucional (HU-31), opcional. Se carga una sola vez y
        # sirve al prompt (contexto y valores) y a los datos informativos (HU-46).
        perfil = self._perfil_institucional(db, current_user.id)

        gen = GeneratorAgent()
        prompt = gen.construir_prompt_unidad(
            area_curricular=area,
            grado=grado,
            competencia_referencia=competencias_texto,
            temas=temas,
            num_sesiones=num_sesiones,
            producto_final=producto_final,
            plantilla_esquema=plantilla_esquema,
            institution_profile=perfil,
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
                    num_sesiones=num_sesiones,
                    plantilla_esquema=plantilla_esquema,
                )
            else:
                contenido_final = full_text

            doc_content = self._unidad_parser.parsear(contenido_final, area=area, num_sesiones=num_sesiones)

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
            # HU-46: DATOS INFORMATIVOS armados con el perfil institucional y los
            # datos del wizard, como primera sección. Con una plantilla
            # institucional activa (HU-49) la estructura la define esa plantilla.
            if not plantilla_esquema:
                from ...core.datos_informativos import construir_datos_informativos_unidad
                datos_inf = construir_datos_informativos_unidad(
                    perfil, area, grado, datos_unidad,
                    docente=getattr(current_user, "full_name", None),
                )
                if datos_inf:
                    doc_content = {"datos_informativos": datos_inf, **doc_content}
            if metricas:
                doc_content["validacion"] = metricas.resumen_validacion()  # HU-30
            new_doc = models.Document(
                id=doc_id, user_id=current_user.id, type="unidad",
                title=f"Unidad Didáctica - {area}", content=doc_content, current_version=1,
                area_curricular=area or None, grado=str(grado) if grado else None,
            )
            db.add(new_doc)

            if current_user.stats:
                current_user.stats.docs_generados = (current_user.stats.docs_generados or 0) + 1
                current_user.stats.unidades_generadas = (current_user.stats.unidades_generadas or 0) + 1
                self._registrar_area_grado(current_user.stats, area, grado)
            db.commit()

            self._save_version(db, doc_id, doc_content, f"Generación inicial (streaming, modo={modo})", 1)
            if metricas:
                self._save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado))

            yield f"data: {json.dumps({'done': True, 'id': doc_id, 'version': 1, **doc_content})}\n\n"
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
        tema_sesion = params.get("tema", "")
        metodologia = params.get("metodologia", "")
        nivel_educativo = params.get("nivel", "Secundaria")
        modo = params.get("modo", "completo")
        # HU-43: segunda defensa; las rutas ya responden 422 antes de llegar aquí.
        try:
            recurso_previo = self.normalizar_recurso_previo(params.get("recurso_previo"))
        except ValueError as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"
            return

        # HU-22: si el docente eligió una Unidad ya generada (en vez de
        # retipear el título a mano), resolvemos título y competencias desde
        # esa Unidad — el servidor es la fuente de verdad, no lo que mande el
        # cliente, para que la vinculación no dependa de que el frontend haya
        # copiado bien los datos.
        unidad_id = params.get("unidad_id")
        unidad_padre = None
        if unidad_id:
            unidad_padre = db.query(models.Document).filter(
                models.Document.id == unidad_id,
                models.Document.user_id == current_user.id,
                models.Document.type == "unidad",
            ).first()

        if unidad_padre:
            titulo_unidad = unidad_padre.title or ""
            competencias_unidad = (unidad_padre.content or {}).get("propositos_de_aprendizaje", "")
        else:
            titulo_unidad = params.get("titulo_unidad", "")
            competencias_unidad = params.get("propositos", "")

        plantilla_esquema = self._plantilla_activa(db, current_user.id, "sesion")
        perfil = self._perfil_institucional(db, current_user.id)  # HU-32

        gen = GeneratorAgent()
        prompt = gen.construir_prompt_sesion(
            titulo_unidad=titulo_unidad,
            titulo_sesion=tema_sesion,
            nivel=nivel_educativo,
            grado=str(grado),
            seccion=params.get("seccion", "A"),
            duracion=params.get("duracion", "90 min"),
            competencias_unidad=competencias_unidad,
            tema=tema_sesion,
            metodologia=metodologia,
            plantilla_esquema=plantilla_esquema,
            recurso_previo=recurso_previo,
            institution_profile=perfil,
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
                    plantilla_esquema=plantilla_esquema,
                )
            else:
                contenido_final = full_text

            doc_content = self._sesion_parser.parsear(contenido_final, tema_sesion=tema_sesion)

            if metricas:
                doc_content["validacion"] = metricas.resumen_validacion()  # HU-30
            new_doc = models.Document(
                id=doc_id, user_id=current_user.id, type="sesion",
                title=f"Sesión - {tema_sesion}", content=doc_content, current_version=1,
                parent_document_id=unidad_padre.id if unidad_padre else None,
                area_curricular=area or None, grado=str(grado) if grado else None,
            )
            db.add(new_doc)

            if current_user.stats:
                current_user.stats.docs_generados = (current_user.stats.docs_generados or 0) + 1
                current_user.stats.sesiones_generadas = (current_user.stats.sesiones_generadas or 0) + 1
                self._registrar_area_grado(current_user.stats, area, grado)
            db.commit()

            self._save_version(db, doc_id, doc_content, f"Generación inicial (streaming, modo={modo})", 1)
            if metricas:
                self._save_pipeline_run(db, doc_id, metricas, area=area, grado=str(grado), metod=metodologia)

            yield f"data: {json.dumps({'done': True, 'id': doc_id, 'version': 1, **doc_content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'done': True, 'error': str(e)})}\n\n"

    # ------------------------------------------------------------------
    # Refinamiento de un campo
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Revalidación tras editar o refinar (HU-30)
    # ------------------------------------------------------------------

    MAX_CARACTERES_REVALIDACION = 300_000

    @classmethod
    def revalidar(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recalcula el estado de validación del documento tal como está ahora en el Editor.

        `params`: {tipo: "unidad"|"sesion", content: {campo: texto}, detalle_previo: [...]}.
        No usa la IA ni la base de datos: son controles sobre las secciones actuales
        (ver validators/revalidacion.py). Lanza ValueError si la entrada no es válida;
        la ruta lo traduce a HTTP 422.
        """
        from ...validators.revalidacion import revalidar_contenido, tipos_soportados
        from ...agents.coordinator import PipelineMetrics

        tipo = params.get("tipo")
        if tipo not in tipos_soportados():
            raise ValueError("tipo debe ser 'unidad' o 'sesion'.")
        contenido = params.get("content")
        if not isinstance(contenido, dict) or not all(isinstance(v, str) for v in contenido.values()):
            raise ValueError("content debe ser un objeto con las secciones como texto.")
        if sum(len(v) for v in contenido.values()) > cls.MAX_CARACTERES_REVALIDACION:
            raise ValueError("El documento es demasiado grande para revalidarlo.")
        detalle_previo = params.get("detalle_previo")
        if detalle_previo is not None and not isinstance(detalle_previo, list):
            raise ValueError("detalle_previo debe ser una lista.")

        reporte = revalidar_contenido(contenido, tipo, detalle_previo)
        metricas = PipelineMetrics(tipo=tipo)
        metricas.aplicar_reporte(reporte)
        return {**metricas.resumen_validacion(), "revalidado": True}

    # ------------------------------------------------------------------
    # Guardado de lo editado en el Editor
    # ------------------------------------------------------------------

    # Tope de versiones por documento: la primera y las más recientes. Sin él, guardar con
    # frecuencia haría crecer el historial sin límite.
    MAX_VERSIONES_POR_DOCUMENTO = 30

    def guardar_cambios(self, db: Session, current_user: models.User, doc_id: str,
                        params: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda las secciones editadas de un documento y registra una versión nueva.

        `params`: {content: {campo: texto}, base_version?: int}. Solo se aceptan los campos de
        contenido conocidos (core/campos_documento.py); lo demás del documento (validación,
        texto crudo...) se conserva. Si el documento tenía validación, se recalcula aquí en el
        servidor y se guarda. Lanza ValueError (entrada inválida), LookupError (no existe o es de
        otro usuario) o ConflictoDeVersion (cambió desde la versión que el cliente conoce).
        """
        from ...core.campos_documento import CAMPOS_DE_CONTENIDO

        contenido = params.get("content")
        if not isinstance(contenido, dict):
            raise ValueError("content debe ser un objeto con las secciones.")
        nuevos: Dict[str, str] = {}
        for campo in CAMPOS_DE_CONTENIDO:
            if campo in contenido:
                if not isinstance(contenido[campo], str):
                    raise ValueError(f"La sección {campo} debe ser texto.")
                nuevos[campo] = contenido[campo]
        if sum(len(v) for v in nuevos.values()) > self.MAX_CARACTERES_REVALIDACION:
            raise ValueError("El documento es demasiado grande para guardarlo.")
        base_version = params.get("base_version")
        if base_version is not None and (not isinstance(base_version, int) or isinstance(base_version, bool)):
            raise ValueError("base_version debe ser un entero.")

        # with_for_update: dos guardados simultáneos no pueden tomar el mismo número de versión.
        doc = db.query(models.Document).filter(
            models.Document.id == doc_id,
            models.Document.user_id == current_user.id,
        ).with_for_update().first()
        if doc is None:
            raise LookupError("Documento no encontrado")
        actual = doc.current_version or 1
        if base_version is not None and base_version != actual:
            raise ConflictoDeVersion(actual)

        anterior = dict(doc.content or {})
        if all(anterior.get(k) == v for k, v in nuevos.items()):
            return {"id": doc.id, "version": actual, "guardado": False,
                    "validacion": anterior.get("validacion")}

        combinado = {**anterior, **nuevos}
        previa = anterior.get("validacion")
        if isinstance(previa, dict):
            combinado["validacion"] = self.revalidar({
                "tipo": doc.type,
                "content": {k: combinado[k] for k in CAMPOS_DE_CONTENIDO if isinstance(combinado.get(k), str)},
                "detalle_previo": previa.get("detalle"),
            })

        nueva = actual + 1
        try:
            doc.content = combinado               # se reasigna el dict: una columna JSON no detecta mutaciones
            doc.current_version = nueva
            db.add(models.DocumentVersion(document_id=doc.id, version_num=nueva,
                                          content=combinado, change_label="Edición guardada"))
            db.flush()
            self._podar_versiones(db, doc.id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return {"id": doc.id, "version": nueva, "guardado": True, "validacion": combinado.get("validacion")}

    def _podar_versiones(self, db: Session, doc_id: str) -> None:
        versiones = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == doc_id
        ).order_by(models.DocumentVersion.version_num.desc()).all()
        if len(versiones) <= self.MAX_VERSIONES_POR_DOCUMENTO:
            return
        conservar = {v.id for v in versiones[: self.MAX_VERSIONES_POR_DOCUMENTO - 1]} | {versiones[-1].id}
        for v in versiones:
            if v.id not in conservar:
                db.delete(v)

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
