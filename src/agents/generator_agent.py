# src/agents/generator_agent.py
"""
Agente Generador: especializado en crear contenido educativo.
Solo genera contenido; NO se encarga de formato ni validación.
"""
import logging
from typing import Any, Optional

from ..core.bedrock_client import get_bedrock_client, BedrockClient
from ..core.prompt_manager import get_prompt_manager, PromptManager
from ..core.rag_service import RAGEducativoService
from ..core.contexto_institucional import construir_contexto_institucional
from ..core.matriz_axiologica import construir_filas_matriz, instrucciones_matriz
from ..core.valores_institucionales import (
    resolver_valores_institucionales,
    resolver_enfoques_transversales,
)

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """
    Agente especializado en generar contenido educativo.
    Usa prompts externalizados y enriquecimiento RAG.
    """

    def __init__(
        self,
        bedrock: BedrockClient = None,
        prompt_manager: PromptManager = None,
    ):
        self.bedrock = bedrock or get_bedrock_client()
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.rag_service = None  # Se inicializa lazy

    def _get_rag(self) -> RAGEducativoService:
        if self.rag_service is None:
            try:
                self.rag_service = RAGEducativoService()
            except Exception as e:
                logger.warning(f"[Generator] No se pudo inicializar RAG: {e}")
        return self.rag_service

    def construir_prompt_unidad(
        self,
        area_curricular: str,
        grado: int,
        competencia_referencia: str = None,
        temas: str = None,
        num_sesiones: int = 6,
        producto_final: str = None,
        plantilla_esquema: Optional[dict] = None,
        institution_profile: Optional[Any] = None,
    ) -> str:
        """
        Construye el prompt para generar una unidad didáctica.

        HU-32: `institution_profile` (HU-31) aporta el contexto institucional y
        los valores/enfoques propios del colegio; sin perfil el prompt es el de siempre.
        Extrae la lógica de armado del prompt del método generar_unidad_didactica().

        HU-49: si `plantilla_esquema` viene informado (plantilla institucional
        subida por el docente, HU-48), el prompt se construye dinámicamente a
        partir de ESA estructura en vez de cargar el template fijo
        `unidad_didactica.md` — mismas reglas pedagógicas, distinta estructura
        de tablas/columnas de salida.
        """
        contexto_competencia = self._construir_contexto_competencia(
            competencia_referencia, area_curricular, grado
        )
        contexto_temas = ""
        if temas and temas.strip():
            contexto_temas = f"\nTEMAS ESPECÍFICOS A INCLUIR:\n{temas}\n"

        contexto_sesiones = (
            f"\nNÚMERO DE SESIONES: EXACTAMENTE {num_sesiones} sesiones, "
            f"numeradas del 1 al {num_sesiones}.\n"
        )

        contexto_producto = ""
        if producto_final and producto_final.strip():
            contexto_producto = (
                f"\nPRODUCTO FINAL DE UNIDAD (OBLIGATORIO):\n"
                f"{producto_final}\n"
                f"REGLA CRÍTICA: La rúbrica analítica DEBE evaluar dimensiones de este producto. "
                f"La situación significativa DEBE mencionar este producto como meta de los estudiantes.\n"
            )
        else:
            contexto_producto = (
                "\nPRODUCTO FINAL: Define un producto tangible apropiado para el área y los temas "
                "(ej. ensayo, maqueta, infografía, prototipo, exposición). "
                "La rúbrica evaluará ese producto.\n"
            )

        contexto_rag = self._buscar_contexto_rag(area_curricular, grado, temas or "", competencia_referencia)
        contexto_institucional = construir_contexto_institucional(institution_profile)
        valores = resolver_valores_institucionales(institution_profile)
        enfoques = resolver_enfoques_transversales(institution_profile)
        # HU-42: filas de la matriz axiológica (las del perfil, o valores/enfoques emparejados).
        contexto_matriz = instrucciones_matriz(construir_filas_matriz(institution_profile), enfoques)

        if plantilla_esquema:
            from ..core.template_parser import construir_prompt_desde_plantilla

            contexto = (
                f"ÁREA CURRICULAR: {area_curricular}. GRADO: {grado}° de secundaria (Perú, CNEB/MINEDU).\n"
                f"{contexto_competencia}{contexto_temas}{contexto_sesiones}{contexto_producto}{contexto_institucional}\n"
                f"Valores institucionales sugeridos: {', '.join(valores)}.\n"
                f"Enfoques transversales sugeridos: {'; '.join(enfoques)}.\n"
                f"Genera EXACTAMENTE {num_sesiones} sesiones y {num_sesiones} criterios de evaluación, "
                f"uno por sesión, sin repetir temas ni criterios entre sesiones."
            )
            reglas = self.prompt_manager.cargar_seccion(
                "unidad_didactica", "REGLA DE CALIDAD PEDAGÓGICA"
            )
            prompt = construir_prompt_desde_plantilla(plantilla_esquema, reglas, contexto)
        else:
            prompt = self.prompt_manager.cargar(
                "unidad_didactica",
                area_curricular=area_curricular,
                grado=grado,
                contexto_competencia=contexto_competencia,
                contexto_temas=contexto_temas,
                contexto_sesiones=contexto_sesiones,
                contexto_producto=contexto_producto,
                contexto_institucional=contexto_institucional,
                contexto_matriz=contexto_matriz,
                num_sesiones=num_sesiones,
                valores_texto=', '.join(valores),
                enfoques_texto='; '.join(enfoques),
            )

        if contexto_rag:
            prompt = f"CONTEXTO OFICIAL DEL MINEDU:\n{contexto_rag}\n\n{prompt}"

        return prompt

    def generar_unidad_didactica(
        self,
        area_curricular: str,
        grado: int,
        competencia_referencia: str = None,
        temas: str = None,
        num_sesiones: int = 6,
        producto_final: str = None,
    ) -> str:
        """
        Genera una unidad didáctica completa.

        Returns:
            Contenido generado (puede tener problemas de formato;
            el FormatterAgent lo limpia después).
        """
        prompt = self.construir_prompt_unidad(
            area_curricular=area_curricular,
            grado=grado,
            competencia_referencia=competencia_referencia,
            temas=temas,
            num_sesiones=num_sesiones,
            producto_final=producto_final,
        )

        logger.info(
            f"[Generator] Generando unidad didáctica: {area_curricular}, "
            f"grado={grado}, sesiones={num_sesiones}"
        )

        contenido = self.bedrock.invocar(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7,
        )

        logger.info(f"[Generator] Unidad generada, longitud: {len(contenido)}")
        return contenido

    def construir_prompt_sesion(
        self,
        titulo_unidad: str,
        titulo_sesion: str,
        nivel: str,
        grado: str,
        seccion: str,
        duracion: str,
        competencias_unidad: str = None,
        tema: str = None,
        metodologia: str = None,
        plantilla_esquema: Optional[dict] = None,
        recurso_previo: Optional[str] = None,
        institution_profile: Optional[Any] = None,
    ) -> str:
        """
        Construye el prompt para generar una sesión de aprendizaje.

        `recurso_previo` (HU-43): enlace del material que los estudiantes
        revisan en casa; solo se usa con Aula Invertida.
        Extrae la lógica de armado del prompt del método generar_sesion_aprendizaje().

        HU-49: mismo mecanismo de plantilla dinámica que construir_prompt_unidad.
        """
        # Truncar títulos a 255 chars (restricción de API)
        LIMITE = 255
        if titulo_unidad and len(titulo_unidad) > LIMITE:
            titulo_unidad = titulo_unidad[:LIMITE - 3].rstrip() + "..."
        if titulo_sesion and len(titulo_sesion) > LIMITE:
            titulo_sesion = titulo_sesion[:LIMITE - 3].rstrip() + "..."

        texto_competencias = ""
        if competencias_unidad:
            texto_competencias = (
                f"USAR EXACTAMENTE LAS COMPETENCIAS DE LA UNIDAD: {competencias_unidad}"
            )
        else:
            texto_competencias = (
                "Competencia: [texto]. Capacidades: [cap 1], [cap 2]. "
                "Criterios de evaluación: [criterio 1], [criterio 2]."
            )

        contexto_tema = f"- Tema de la sesión: {tema}" if tema else ""
        contexto_metodologia = self._construir_contexto_metodologia(metodologia, recurso_previo)
        contexto_institucional = construir_contexto_institucional(institution_profile)  # HU-32
        # HU-42: para la sesión se prioriza 1-2 filas de la matriz según el tema.
        contexto_matriz = instrucciones_matriz(
            construir_filas_matriz(institution_profile),
            resolver_enfoques_transversales(institution_profile),
            por_sesion=True,
        )

        if plantilla_esquema:
            from ..core.template_parser import construir_prompt_desde_plantilla

            contexto = (
                f"Título de la Unidad: {titulo_unidad}. Título de la Sesión: {titulo_sesion}.\n"
                f"Nivel: {nivel}. Grado: {grado}. Sección: {seccion}. Duración: {duracion}.\n"
                f"{texto_competencias}\n{contexto_tema}\n{contexto_metodologia}{contexto_institucional}"
            )
            reglas = self.prompt_manager.cargar_seccion(
                "sesion_aprendizaje", "INSTRUCCIONES DE METODOLOGÍA"
            )
            prompt = construir_prompt_desde_plantilla(plantilla_esquema, reglas, contexto)
        else:
            prompt = self.prompt_manager.cargar(
                "sesion_aprendizaje",
                titulo_unidad=titulo_unidad,
                titulo_sesion=titulo_sesion,
                nivel=nivel,
                grado=grado,
                seccion=seccion,
                duracion=duracion,
                texto_competencias=texto_competencias,
                contexto_tema=contexto_tema,
                contexto_metodologia=contexto_metodologia,
                contexto_institucional=contexto_institucional,
                contexto_matriz=contexto_matriz,
            )

        return prompt

    def generar_sesion_aprendizaje(
        self,
        titulo_unidad: str,
        titulo_sesion: str,
        nivel: str,
        grado: str,
        seccion: str,
        duracion: str,
        competencias_unidad: str = None,
        tema: str = None,
        metodologia: str = None,
    ) -> str:
        """Genera una sesión de aprendizaje completa."""
        prompt = self.construir_prompt_sesion(
            titulo_unidad=titulo_unidad,
            titulo_sesion=titulo_sesion,
            nivel=nivel,
            grado=grado,
            seccion=seccion,
            duracion=duracion,
            competencias_unidad=competencias_unidad,
            tema=tema,
            metodologia=metodologia,
        )

        logger.info(f"[Generator] Generando sesión: {titulo_sesion}")
        return self.bedrock.invocar(prompt=prompt, max_tokens=4000, temperature=0.7)

    def mejorar_documento(
        self,
        texto_documento: str,
        instruccion_usuario: str,
        tipo_documento: str = "documento",
    ) -> str:
        """Mejora un documento según la instrucción del usuario."""
        prompt = self.prompt_manager.cargar(
            "mejora_documento",
            tipo_documento=tipo_documento,
            texto_documento=texto_documento,
            instruccion_usuario=instruccion_usuario,
        )

        resultado = self.bedrock.invocar(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.4,
            min_longitud_respuesta=20,
        )
        return resultado if resultado else texto_documento

    def corregir(self, contenido: str, errores: list) -> str:
        """
        Corrige contenido basándose en errores del validador.
        El validador envía una lista de errores y el generador los corrige.
        """
        errores_texto = "\n".join(
            [f"- [{e.get('tipo', e.tipo if hasattr(e, 'tipo') else 'ERROR')}] "
             f"{e.get('mensaje', e.mensaje if hasattr(e, 'mensaje') else str(e))}"
             for e in errores]
        )

        prompt = f"""Eres un editor experto en documentos educativos del MINEDU Perú.

El siguiente documento tiene errores que debes corregir:

ERRORES DETECTADOS:
{errores_texto}

DOCUMENTO A CORREGIR:
\"\"\"
{contenido}
\"\"\"

TAREA:
1. Corrige TODOS los errores listados arriba.
2. Conserva la estructura y formato de tabla (| ITEM | CONTENIDO |).
3. Devuelve ÚNICAMENTE el documento corregido, sin explicaciones.

Responde solo con el documento completo corregido."""

        logger.info(f"[Generator] Corrigiendo {len(errores)} errores")
        return self.bedrock.invocar(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.3,
        )

    # --- Métodos auxiliares ---

    def _construir_contexto_metodologia(self, metodologia: str, recurso_previo: Optional[str] = None) -> str:
        """Construye instrucciones de estilo según la metodología elegida.

        HU-43: con Aula Invertida, si el docente indicó el enlace del recurso
        previo, se le ordena al modelo citarlo textualmente en el INICIO en vez
        de inventar una referencia genérica. Con otras metodologías se ignora."""
        if not metodologia or not metodologia.strip():
            return ""

        met = metodologia.strip().upper()

        if "ABP" in met or "BASADO EN PROBLEMAS" in met:
            return (
                "- Metodología: ABP (Aprendizaje Basado en Problemas)\n"
                "  INSTRUCCIÓN DE ESTILO: El INICIO debe presentar un problema real, "
                "cercano al estudiante. NO explicar teoría al inicio. "
                "El DESARROLLO debe seguir los pasos: análisis del problema → "
                "investigación → diseño de solución → validación ante pares."
            )
        elif "INVERTIDA" in met or "FLIPPED" in met:
            return (
                "- Metodología: Aula Invertida (Flipped Classroom)\n"
                "  INSTRUCCIÓN DE ESTILO: El INICIO no presenta contenido nuevo; "
                "verifica lo estudiado en casa con 3-4 preguntas. El docente NO expone. "
                "El DESARROLLO se dedica íntegramente a debates grupales, "
                "análisis de casos y creación colaborativa."
                + self._instruccion_recurso_previo(recurso_previo)
            )
        elif "ERCA" in met:
            return (
                "- Metodología: ERCA (Experiencia → Reflexión → Conceptualización → Aplicación)\n"
                "  INSTRUCCIÓN DE ESTILO: El INICIO es una actividad vivencial concreta "
                "(experimento, juego de rol, caso real) SIN teoría previa. "
                "El DESARROLLO va de reflexión guiada → conceptualización → aplicación práctica."
            )
        else:
            return f"- Metodología: {metodologia}"


    @staticmethod
    def _instruccion_recurso_previo(recurso_previo: Optional[str]) -> str:
        if not recurso_previo or not recurso_previo.strip():
            return ""
        return (
            "\n  RECURSO PREVIO (enlace que los estudiantes revisan en casa): "
            f"{recurso_previo.strip()}\n"
            "  En el INICIO, la verificación de lo estudiado en casa DEBE citar este "
            "enlace tal cual, completo y sin modificarlo, como el material previo."
        )

    def _construir_contexto_competencia(
        self, competencia: str, area: str, grado: int
    ) -> str:
        """Construye el bloque de contexto de competencias para el prompt."""
        if not competencia or not competencia.strip():
            return (
                f"\nCOMPETENCIAS: Selecciona las más apropiadas del CNEB para "
                f"{area} en {grado}° de secundaria.\n"
            )

        competencias_lista = [c.strip() for c in competencia.split('\n') if c.strip()]

        if len(competencias_lista) > 1:
            texto = '\n'.join([f"- {c}" for c in competencias_lista])
            return (
                f"\nCOMPETENCIAS OBLIGATORIAS (USAR SOLO ESTAS):\n{texto}\n"
                f"NO agregues otras competencias. Usa EXACTAMENTE estas {len(competencias_lista)}.\n"
            )
        else:
            return (
                f"\nCOMPETENCIA OBLIGATORIA (USAR SOLO ESTA):\n"
                f"{competencia}\n"
                f"Usa SOLO esta competencia. NO agregues otras.\n"
            )

    def _buscar_contexto_rag(self, area: str, grado: int, temas: str, competencia: "str | None" = None) -> str:
        """Busca contexto relevante en el RAG para enriquecer la generación.
        `competencia`: la(s) competencia(s) elegida(s) en el wizard; con ella los desempeños se recuperan por
        búsqueda exacta (área + grado + competencia) en vez de por similitud."""
        rag = self._get_rag()
        if not rag:
            return ""

        try:
            query = f"programación curricular {area} {grado} grado secundaria {temas}"
            resultado = rag.buscar_contexto_curricular(
                query=query, grado=grado, area=area.replace(" ", "_").lower(), competencia=competencia
            )
            docs = resultado.get('documentos', [])
            if not docs:
                return ""

            partes = []
            for i, doc in enumerate(docs[:7], 1):  # hasta 5 estructurados + al menos 2 complementarios
                fuente = doc.get('fuente', 'MINEDU')
                contenido = doc.get('contenido', '')
                partes.append(f"Documento {i} ({fuente}):\n{contenido}")

            return '\n---\n'.join(partes)
        except Exception as e:
            logger.warning(f"[Generator] Error en RAG: {e}")
            return ""
