# src/agents/generator_agent.py
"""
Agente Generador: especializado en crear contenido educativo.
Solo genera contenido; NO se encarga de formato ni validación.
"""
import logging
from typing import Optional

from ..core.bedrock_client import get_bedrock_client, BedrockClient
from ..core.prompt_manager import get_prompt_manager, PromptManager
from ..core.rag_service import RAGEducativoService
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
    ) -> str:
        """
        Construye el prompt para generar una unidad didáctica.
        Extrae la lógica de armado del prompt del método generar_unidad_didactica().
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

        prompt = self.prompt_manager.cargar(
            "unidad_didactica",
            area_curricular=area_curricular,
            grado=grado,
            contexto_competencia=contexto_competencia,
            contexto_temas=contexto_temas,
            contexto_sesiones=contexto_sesiones,
            contexto_producto=contexto_producto,
            num_sesiones=num_sesiones,
            valores_texto=', '.join(resolver_valores_institucionales()),
            enfoques_texto='; '.join(resolver_enfoques_transversales()),
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
    ) -> str:
        """
        Construye el prompt para generar una sesión de aprendizaje.
        Extrae la lógica de armado del prompt del método generar_sesion_aprendizaje().
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
        contexto_metodologia = self._construir_contexto_metodologia(metodologia)

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

    def _construir_contexto_metodologia(self, metodologia: str) -> str:
        """Construye instrucciones de estilo según la metodología elegida."""
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
