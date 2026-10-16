# core/rag_service.py
import boto3
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

from .retrieval_estructurado import BM25, RecuperadorCurricular, tokens

logger = logging.getLogger(__name__)

# Rutas a JSON para RAG local
def _base_data_paths() -> List[Path]:
    base = Path(__file__).resolve().parent.parent.parent
    base_alt = base.parent
    return [base, base_alt]

_CURRICULO_JSON = "data/curriculo_secundaria_peru_2016.json"
_ORIENTACIONES_JSON = "data/orientaciones_pedagogicas_cneb.json"
_SESION_EF_EPT_JSON = "data/sesion_ef_ept_planificacion_curricular.json"
_SESION_3_EVAL_JSON = "data/sesion_3_evaluacion_formativa_ef_ept.json"
_ENFOQUE_MODULO1_JSON = "data/enfoque_por_competencias_modulo1.json"
_METODOLOGIAS_ACTIVAS_2026_JSON = "data/metodologias_activas_innovacion_educativa_2026.json"


# Resúmenes del currículo que el Programa Curricular completo (recuperación estructurada) reemplaza con más detalle:
# un párrafo por área y por ciclo. Seguir ofreciéndolos como "contexto complementario" solo agrega redundancia (y a
# veces errores: el resumen del ciclo VII para un alumno de 1.°). Se conserva "estandares_desempenos" porque explica
# el CONCEPTO (qué es un estándar frente a un desempeño), cosa que los datos estructurados no hacen.
_CHUNKS_CURRICULO_SUPERADOS = {"ciclo_vi", "ciclo_vii"}
_PALABRAS_GENERICAS_DE_CONSULTA = {"programacion", "curricular", "grado", "secundaria"}


def _chunk_superado(chunk_id: str) -> bool:
    return chunk_id.startswith("area_") or chunk_id in _CHUNKS_CURRICULO_SUPERADOS


def _cargar_json_local(nombre: str) -> Optional[Dict[str, Any]]:
    """Carga un JSON desde data/ (curriculo u orientaciones)."""
    for base in _base_data_paths():
        path = base / nombre
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo cargar {nombre} desde {path}: {e}")
    return None


def _cargar_curriculo_local() -> Optional[Dict[str, Any]]:
    """Carga el Programa Curricular Educación Secundaria Perú 2016 desde JSON local."""
    return _cargar_json_local(_CURRICULO_JSON)


def _cargar_orientaciones_local() -> Optional[Dict[str, Any]]:
    """Carga Orientaciones para planificación, mediación y evaluación (CNEB) desde JSON local."""
    return _cargar_json_local(_ORIENTACIONES_JSON)


def _cargar_sesion_ef_ept_local() -> Optional[Dict[str, Any]]:
    """Carga Sesión 2 EF/EPT - Planificación Curricular (enfoque por competencias y carisma salesiano) desde JSON local."""
    return _cargar_json_local(_SESION_EF_EPT_JSON)


def _cargar_sesion_3_eval_local() -> Optional[Dict[str, Any]]:
    """Carga Sesión 3 EF/EPT - La Evaluación Formativa (enfoque por competencias y sentido salesiano) desde JSON local."""
    return _cargar_json_local(_SESION_3_EVAL_JSON)


def _cargar_enfoque_modulo1_local() -> Optional[Dict[str, Any]]:
    """Carga Enfoque por competencias - Módulo 1 (capacitación, planificación y evaluación formativa) desde JSON local."""
    return _cargar_json_local(_ENFOQUE_MODULO1_JSON)


def _cargar_metodologias_activas_2026_local() -> Optional[Dict[str, Any]]:
    """Carga Metodologías Activas para la Innovación Educativa 2026 (Aula Invertida, ABP, Gamificación) desde JSON local."""
    return _cargar_json_local(_METODOLOGIAS_ACTIVAS_2026_JSON)


def _buscar_contexto_local(
    query: str,
    grado: int,
    area: str,
    curriculo: Dict[str, Any],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Búsqueda local por palabras clave y texto.
    Usa keywords del documento y coincidencias en el texto de cada chunk.
    """
    chunks = curriculo.get("chunks", [])
    keywords_globales = set(k.lower() for k in curriculo.get("keywords", []))
    query_lower = query.lower()
    # Tokens de la consulta para scoring
    query_tokens = set(query_lower.split())
    # Añadir términos del área y grado
    query_tokens.add(area.replace("_", " "))
    query_tokens.add(f"{grado}")

    scored: List[tuple] = []
    for ch in chunks:
        text = (ch.get("text") or "").lower()
        section = (ch.get("section") or "").lower()
        chunk_keywords = [k.lower() for k in ch.get("keywords", [])]
        score = 0.0
        # Coincidencia con keywords del chunk
        for kw in chunk_keywords:
            if kw in query_lower or any(t in kw for t in query_tokens):
                score += 0.5
        # Coincidencia de tokens en texto
        for t in query_tokens:
            if len(t) > 2 and t in text:
                score += 0.3
            if len(t) > 2 and t in section:
                score += 0.4
        # Keywords globales del currículo que coincidan con la consulta
        for kw in keywords_globales:
            if kw in query_lower and (kw in text or kw in section):
                score += 0.4
        if score > 0:
            scored.append((score, ch))

    scored.sort(key=lambda x: -x[0])
    documentos = []
    meta = curriculo.get("metadata", {})
    fuente_nombre = meta.get("documento", "Currículo Secundaria Perú 2016")
    for s, ch in scored[:top_k]:
        documentos.append({
            "contenido": f"[{ch.get('section', '')}]\n{ch.get('text', '')}",
            "fuente": f"{fuente_nombre} - {ch.get('section', '')}",
            "score": min(1.0, s),
            "metadata": {"section": ch.get("section"), **meta},
        })
    return documentos


class RAGEducativoService:
    """
    Servicio RAG especializado para contenido educativo peruano.
    Usa Amazon Bedrock Knowledge Bases si está configurado; si no, fallback
    al Programa Curricular Educación Secundaria Perú 2016 (data/curriculo_secundaria_peru_2016.json).
    """
    KB_PLACEHOLDER = "KB-CURRICULO-ID-HERE"

    # Recuperacion estructurada (desempeños por area/grado/competencia). RAG_ESTRUCTURADO=0 la desactiva.
    MAX_DOCUMENTOS = 10
    MAX_ESTRUCTURADOS = 5   # el resto de los puestos queda para el contexto complementario (orientaciones, metodologías)

    @property
    def bedrock_runtime(self):
        # perezoso: crear el cliente exige region/credenciales y el servicio debe poder usarse sin ellas
        if self._bedrock_runtime is None:
            self._bedrock_runtime = boto3.client('bedrock-runtime')
        return self._bedrock_runtime

    @property
    def bedrock_agent(self):
        if self._bedrock_agent is None:
            self._bedrock_agent = boto3.client('bedrock-agent-runtime')
        return self._bedrock_agent

    def __init__(self):
        self._bedrock_runtime = None
        self._bedrock_agent = None
        self._recuperador: Optional[RecuperadorCurricular] = None
        if os.environ.get('RAG_ESTRUCTURADO', '1') != '0':
            try:
                self._recuperador = RecuperadorCurricular.desde_json()
            except Exception as e:  # sin el corpus nuevo el servicio sigue como antes
                logger.warning(f"Recuperación estructurada no disponible: {e}")
        self.knowledge_base_ids = {
            'curriculo_nacional': os.environ.get('BEDROCK_KB_CURRICULO_ID', 'KB-CURRICULO-ID-HERE'),
            'rubricas_evaluacion': 'KB-RUBRICAS-ID-HERE',
            'metodologias': 'KB-METODOLOGIAS-ID-HERE',
            'recursos_educativos': 'KB-RECURSOS-ID-HERE'
        }
        self._curriculo_local: Optional[Dict[str, Any]] = _cargar_curriculo_local()
        self._orientaciones_local: Optional[Dict[str, Any]] = _cargar_orientaciones_local()
        self._sesion_ef_ept_local: Optional[Dict[str, Any]] = _cargar_sesion_ef_ept_local()
        self._sesion_3_eval_local: Optional[Dict[str, Any]] = _cargar_sesion_3_eval_local()
        self._enfoque_modulo1_local: Optional[Dict[str, Any]] = _cargar_enfoque_modulo1_local()
        self._metodologias_activas_2026_local: Optional[Dict[str, Any]] = _cargar_metodologias_activas_2026_local()
        # Índice BM25 del contexto complementario. RAG_COMPLEMENTARIO_BM25=0 vuelve al puntaje por palabras clave anterior.
        self._indice_complementario = None
        if os.environ.get('RAG_COMPLEMENTARIO_BM25', '1') != '0':
            try:
                self._indice_complementario = self._construir_indice_complementario()
            except Exception as e:
                logger.warning(f"Índice BM25 del contexto complementario no disponible, se usa el puntaje anterior: {e}")

    def _construir_indice_complementario(self):
        """BM25 sobre los JSON locales de orientaciones, metodologías, capacitación y resumen del currículo."""
        chunks = []
        for datos in (self._curriculo_local, self._orientaciones_local, self._sesion_ef_ept_local,
                      self._sesion_3_eval_local, self._enfoque_modulo1_local, self._metodologias_activas_2026_local):
            if not datos:
                continue
            meta = datos.get("metadata", {})
            nombre = meta.get("documento", "Documento MINEDU")
            for ch in datos.get("chunks", []):
                if self._recuperador is not None and datos is self._curriculo_local and _chunk_superado(ch.get("id", "")):
                    continue
                chunks.append({
                    "section": ch.get("section", ""), "text": ch.get("text", ""), "keywords": ch.get("keywords", []),
                    "_fuente": f"{nombre} - {ch.get('section', '')}", "_meta": {"section": ch.get("section"), **meta},
                })
        return (chunks, BM25(chunks)) if chunks else None

    def _buscar_complementario_bm25(self, query: str, limite: int = 10) -> List[Dict[str, Any]]:
        if not self._indice_complementario:
            return []
        chunks, bm25 = self._indice_complementario
        # el prefijo "programación curricular {área} {grado} grado secundaria" no dice nada del contenido pedagógico buscado
        consulta = " ".join(t for t in tokens(query) if t not in _PALABRAS_GENERICAS_DE_CONSULTA)
        puntajes = bm25.scores(consulta)
        mejores = [i for i in sorted(range(len(puntajes)), key=lambda i: -puntajes[i])[:limite] if puntajes[i] > 0]
        if not mejores:
            return []
        maximo = puntajes[mejores[0]]
        return [{
            'contenido': f"[{chunks[i]['section']}]\n{chunks[i]['text']}",
            'fuente': chunks[i]['_fuente'],
            'score': puntajes[i] / maximo,
            'metadata': chunks[i]['_meta'],
        } for i in mejores]

    def buscar_contexto_curricular(self, query: str, grado: int, area: str = "ciencia_tecnologia",
                                   competencia: Optional[str] = None) -> Dict:
        """
        Busca contexto relevante: primero la recuperación estructurada del Programa Curricular (desempeños del
        grado, capacidades y estándar del ciclo, filtrados por área/grado y, si se conoce, por la competencia
        elegida) y luego el contexto complementario (Bedrock KB o JSON locales: orientaciones, metodologías...).
        `competencia`: texto del wizard, una competencia por línea. Si la parte estructurada falla, el resultado
        es el mismo que antes de existir.
        """
        estructurados = self._recuperar_estructurado(query, grado, area, competencia)
        complementarios = self._buscar_contexto_complementario(query, grado, area).get('documentos', [])
        vistos = {d['contenido'] for d in estructurados}
        docs = (estructurados + [d for d in complementarios if d.get('contenido') not in vistos])[:self.MAX_DOCUMENTOS]
        return {'documentos': docs, 'total_encontrados': len(docs), 'estructurados': min(len(estructurados), len(docs))}

    def _recuperar_estructurado(self, query: str, grado: int, area: str, competencia: Optional[str]) -> List[Dict[str, Any]]:
        if self._recuperador is None:
            return []
        try:
            competencias = [c for c in (competencia or '').split('\n') if c.strip()]
            # Sin competencia elegida, Claude debe "seleccionar las más apropiadas del área": necesita ver los
            # desempeños de todas las competencias del área en ese grado (como máximo 4), no solo los 2 mejores.
            chunks = self._recuperador.recuperar(query, grado, area, competencias or None,
                                                 k=self.MAX_ESTRUCTURADOS, m=4, con_resto=False)
        except Exception as e:  # nunca debe romper la generación
            logger.warning(f"Recuperación estructurada falló, se continúa sin ella: {e}")
            return []
        docs = []
        for ch in chunks:
            paginas = ch.get('paginas') or []
            docs.append({
                'contenido': f"[{ch.get('section', '')}]\n{ch.get('text', '')}",
                'fuente': "Programa Curricular de Educación Secundaria (MINEDU, 2016) - "
                          f"{ch.get('section', '')}" + (f" (p. {', '.join(map(str, paginas))})" if paginas else ""),
                'score': 1.0,
                'metadata': {k: ch.get(k) for k in ('tipo', 'area', 'competencia', 'ciclo', 'grado', 'paginas')}
                            | {'chunk_id': ch.get('id'), 'recuperacion': 'estructurada'},
            })
        return docs

    def _buscar_contexto_complementario(self, query: str, grado: int, area: str = "ciencia_tecnologia") -> Dict:
        """
        Contexto complementario (orientaciones, metodologías, etc.).
        Primero intenta Bedrock KB; si no está configurado o falla, usa los JSON locales.
        """
        kb_id = self.knowledge_base_ids.get('curriculo_nacional') or self.KB_PLACEHOLDER
        if kb_id != self.KB_PLACEHOLDER:
            try:
                query_enriquecida = f"""
                Buscar información sobre: {query}
                Contexto: Educación secundaria {grado}º grado, área de {area.replace('_', ' ')}
                País: Perú, Currículo Nacional de Educación Básica
                """
                response = self.bedrock_agent.retrieve(
                    knowledgeBaseId=kb_id,
                    retrievalQuery={'text': query_enriquecida},
                    retrievalConfiguration={
                        'vectorSearchConfiguration': {
                            'numberOfResults': 10,
                            'overrideSearchType': 'HYBRID'
                        }
                    }
                )
                documentos_relevantes = []
                for result in response.get('retrievalResults', []):
                    documentos_relevantes.append({
                        'contenido': result.get('content', {}).get('text', ''),
                        'fuente': result.get('location', {}).get('s3Location', {}).get('uri', ''),
                        'score': result.get('score', 0),
                        'metadata': result.get('metadata', {})
                    })
                return {'documentos': documentos_relevantes, 'total_encontrados': len(documentos_relevantes)}
            except Exception as e:
                logger.warning(f"Bedrock KB no disponible, usando curriculo local: {e}")

        # Búsqueda local con BM25 (sin tildes ni stopwords) sobre orientaciones, metodologías y capacitación.
        if self._indice_complementario:
            docs = self._buscar_complementario_bm25(query, self.MAX_DOCUMENTOS)
            return {'documentos': docs, 'total_encontrados': len(docs)}

        # Fallback: búsqueda local en curriculo + orientaciones CNEB + sesión EF/EPT (planificación curricular, carisma salesiano)
        todos_docs: List[Dict[str, Any]] = []
        if self._curriculo_local:
            todos_docs.extend(_buscar_contexto_local(query, grado, area, self._curriculo_local, top_k=8))
        if self._orientaciones_local:
            todos_docs.extend(_buscar_contexto_local(query, grado, area, self._orientaciones_local, top_k=6))
        if self._sesion_ef_ept_local:
            todos_docs.extend(_buscar_contexto_local(query, grado, area, self._sesion_ef_ept_local, top_k=5))
        if self._sesion_3_eval_local:
            todos_docs.extend(_buscar_contexto_local(query, grado, area, self._sesion_3_eval_local, top_k=5))
        if self._enfoque_modulo1_local:
            todos_docs.extend(_buscar_contexto_local(query, grado, area, self._enfoque_modulo1_local, top_k=5))
        if self._metodologias_activas_2026_local:
            todos_docs.extend(_buscar_contexto_local(query, grado, area, self._metodologias_activas_2026_local, top_k=6))
        if todos_docs:
            todos_docs.sort(key=lambda d: d.get("score", 0), reverse=True)
            documentos_finales = todos_docs[:10]
            return {'documentos': documentos_finales, 'total_encontrados': len(documentos_finales)}
        return {'documentos': [], 'total_encontrados': 0}
    
    def generar_con_contexto_rag(self, prompt: str, contexto_documentos: List[Dict]) -> str:
        """
        Genera contenido usando RAG con documentos del MINEDU
        """
        try:
            # Construir contexto enriquecido
            contexto_rag = self._construir_contexto_educativo(contexto_documentos)
            
            prompt_con_rag = f"""Eres un experto en educación peruana especializado en el Currículo Nacional de Educación Básica. 

CONTEXTO OFICIAL DEL MINEDU:
{contexto_rag}

INSTRUCCIONES:
{prompt}

Basa tu respuesta EXCLUSIVAMENTE en el contexto oficial proporcionado. Si no encuentras información suficiente en el contexto, menciona qué información específica faltaría para completar la respuesta.

Estructura tu respuesta de manera profesional y alineada con los documentos oficiales del MINEDU."""
            
            # No enviar top_p junto con temperature: algunos modelos Claude en
            # Bedrock rechazan la petición con ValidationException si se
            # especifican ambos (ver bedrock_client.py).
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt_con_rag
                    }
                ],
                "temperature": 0.3,  # Más conservador para contenido educativo oficial
            })
            
            # HU-34: comparte el límite de concurrencia con BedrockClient.
            from .bedrock_client import get_limite_concurrencia
            with get_limite_concurrencia():
                response = self.bedrock_runtime.invoke_model(
                    body=body,
                    modelId='anthropic.claude-opus-4-6-v1',
                    accept='application/json',
                    contentType='application/json'
                )
                response_body = json.loads(response.get('body').read())
            return response_body.get('content', [{}])[0].get('text', '')
            
        except Exception as e:
            logger.error(f"Error en generación RAG: {e}")
            return f"Error al generar contenido con RAG: {e}"
    
    def _construir_contexto_educativo(self, documentos: List[Dict]) -> str:
        """
        Construye el contexto enriquecido para el prompt
        """
        if not documentos:
            return "No se encontró contexto específico en los documentos oficiales."
        
        contexto_partes = []
        for i, doc in enumerate(documentos[:5], 1):  # Limitar a top 5 documentos
            fuente = doc.get('fuente', 'Documento MINEDU')
            contenido = doc.get('contenido', '')
            score = doc.get('score', 0)
            
            contexto_partes.append(f"""
DOCUMENTO {i} (Relevancia: {score:.2f}):
Fuente: {fuente}
Contenido:
{contenido}
---""")
        
        return '\n'.join(contexto_partes)

# Función integrada para programación curricular con RAG
def generar_programacion_curricular_rag(grado: int, competencia: str, capacidades: str, contenidos: str) -> str:
    """
    Genera programación curricular usando RAG con documentos oficiales del MINEDU
    """
    try:
        rag_service = RAGEducativoService()
        
        # 1. Buscar contexto relevante
        query_busqueda = f"""
        programación curricular ciencia y tecnología {grado} grado secundaria
        competencias capacidades desempeños criterios evaluación
        {competencia} {contenidos}
        """
        
        contexto = rag_service.buscar_contexto_curricular(
            query=query_busqueda,
            grado=grado,
            area="ciencia_tecnologia"
        )
        
        # 2. Generar con contexto RAG
        prompt_programacion = f"""
        Genera una programación curricular completa para {grado}º de secundaria en el área de Ciencia y Tecnología.

        DATOS ESPECÍFICOS:
        - Grado: {grado}º de secundaria  
        - Competencia: {competencia}
        - Capacidades: {capacidades}
        - Contenidos: {contenidos}

        FORMATO REQUERIDO:
        Crea una tabla completa con las columnas: COMPETENCIA, CAPACIDADES, CONTENIDOS, DESEMPEÑOS, CRITERIOS DE EVALUACIÓN, INSTRUMENTOS DE EVALUACIÓN.

        REQUISITOS:
        - Usar EXCLUSIVAMENTE la información oficial del contexto proporcionado
        - Los desempeños deben ser específicos, observables y medibles
        - Criterios de evaluación alineados con cada desempeño
        - Instrumentos variados y pertinentes
        - Formato profesional del MINEDU
        """
        
        resultado = rag_service.generar_con_contexto_rag(
            prompt=prompt_programacion,
            contexto_documentos=contexto['documentos']
        )
        
        # 3. Agregar metadatos de las fuentes consultadas
        fuentes_consultadas = [doc['fuente'] for doc in contexto['documentos'][:3]]
        resultado_final = f"""{resultado}

FUENTES OFICIALES CONSULTADAS:
{chr(10).join([f"- {fuente}" for fuente in fuentes_consultadas])}

Total de documentos oficiales analizados: {contexto['total_encontrados']}
"""
        
        return resultado_final
        
    except Exception as e:
        logger.error(f"Error en programación curricular RAG: {e}")
        return f"Error al generar programación curricular con RAG: {e}"

# Configuración de AWS Knowledge Bases - Script de setup
def setup_knowledge_bases():
    """
    Script para configurar las Knowledge Bases necesarias
    """
    setup_script = """
    # 1. Crear bucket S3 para documentos
    aws s3 mb s3://minedu-documentos-educativos-peru
    
    # 2. Subir documentos del MINEDU
    aws s3 sync ./documentos_minedu/ s3://minedu-documentos-educativos-peru/curriculo/
    
    # 3. Crear Knowledge Base via CLI o Console
    # - Currículo Nacional de Educación Básica
    # - Rúbricas de evaluación
    # - Metodologías de enseñanza
    # - Recursos educativos
    
    # 4. Configurar embeddings con Amazon Titan
    # 5. Sincronizar datos
    """
    return setup_script

# Ejemplo de uso
if __name__ == "__main__":
    # Test básico
    rag_service = RAGEducativoService()
    
    test_query = "competencias ciencia tecnología 3 secundaria"
    resultado = rag_service.buscar_contexto_curricular(
        query=test_query,
        grado=3,
        area="ciencia_tecnologia"  
    )
    
    print(f"Documentos encontrados: {resultado['total_encontrados']}")
    for doc in resultado['documentos'][:2]:
        print(f"Score: {doc['score']}")
        print(f"Contenido: {doc['contenido'][:200]}...")
        print("---")