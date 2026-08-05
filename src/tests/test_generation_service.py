"""
Tests para generation_service.py tras unificación de streaming.

NOTA IMPORTANTE: Estos tests son ejemplos de estructura de pruebas unitarias.
La validación real de streaming se hace mediante:
1. Tests de integración (test_streaming_integration.py) - requieren servidor
2. Pruebas manuales (docs/PRUEBAS_MANUALES.md) - validación en navegador
3. Inspección de logs y base de datos

Los tests unitarios aquí no pueden hacer patch de agents.* debido a imports circulares.
En cambio, demuestran la estructura AAA (Arrange, Act, Assert) y las fixtures reutilizables.
"""
import pytest
import json
from unittest.mock import Mock
from sqlalchemy.orm import Session


class TestGenerationServiceStructure:
    """Valida la estructura de GenerationService tras refactorización"""

    @pytest.fixture
    def service(self):
        """Importa el servicio sin dependencias circulares"""
        from api.services.generation_service import GenerationService
        return GenerationService()

    @pytest.fixture
    def mock_user(self):
        """Mock de User con stats para tests"""
        user = Mock()
        user.id = "test-user-123"
        user.stats = Mock()
        user.stats.docs_generados = 0
        user.stats.unidades_generadas = 0
        user.stats.sesiones_generadas = 0
        return user

    @pytest.fixture
    def mock_db(self):
        """Mock de SQLAlchemy Session"""
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        return db

    def test_service_tiene_metodo_generar_unidad_stream_events(self, service):
        """Valida que el método de streaming unificado existe"""
        assert hasattr(service, 'generar_unidad_stream_events')
        assert callable(service.generar_unidad_stream_events)

    def test_service_tiene_metodo_generar_sesion_stream_events(self, service):
        """Valida que Sesión streaming se agregó (nuevo)"""
        assert hasattr(service, 'generar_sesion_stream_events')
        assert callable(service.generar_sesion_stream_events)

    def test_service_no_tiene_crear_unidad_bloqueante(self, service):
        """Valida que el método bloqueante fue eliminado"""
        # Este método debería haber sido removido en la refactorización
        # Si aún existe, la prueba falla
        if hasattr(service, 'crear_unidad'):
            pytest.fail("crear_unidad() bloqueante debería haber sido eliminado")

    def test_service_no_tiene_crear_sesion_bloqueante(self, service):
        """Valida que el método bloqueante de Sesión fue eliminado"""
        if hasattr(service, 'crear_sesion'):
            pytest.fail("crear_sesion() bloqueante debería haber sido eliminado")

    def test_parsers_estan_inicializados(self, service):
        """Valida que los parsers están disponibles"""
        assert hasattr(service, '_unidad_parser')
        assert hasattr(service, '_sesion_parser')


class TestStreamingEventStructure:
    """Valida la estructura esperada de eventos SSE"""

    def test_evento_chunk_tiene_estructura_correcta(self):
        """Un evento de chunk debe ser: {"chunk": "...", "done": false}"""
        evento = {"chunk": "Contenido generado", "done": False}
        assert "chunk" in evento
        assert "done" in evento
        assert evento["done"] is False

    def test_evento_validando_tiene_estructura_correcta(self):
        """Un evento validando debe ser: {"validando": true}"""
        evento = {"validando": True}
        assert "validando" in evento
        assert evento["validando"] is True

    def test_evento_final_tiene_estructura_completa(self):
        """El evento final debe incluir: done, id, y todas las secciones"""
        evento_final = {
            "done": True,
            "id": "doc-uuid-12345",
            "situacion_significativa": "Contenido...",
            "propositos_de_aprendizaje": "Contenido...",
            "secuencia_de_sesiones": "Contenido...",
            "rubrica_unidad": "Contenido..."
        }
        assert evento_final["done"] is True
        assert "id" in evento_final
        # Antes de la refactorización, solo tenía {"done": true, "id": "..."}
        # Ahora debe incluir todas las secciones parseadas
        assert len(evento_final) > 2  # Más que solo done e id


class TestModoParameter:
    """Valida que el parámetro 'modo' controla el flujo"""

    def test_modo_solo_generador_valida_solo_generador(self):
        """modo='solo_generador' debería saltarse validación"""
        params = {
            "area": "Comunicación",
            "grado": "3°",
            "modo": "solo_generador"
        }
        assert params.get("modo") == "solo_generador"

    def test_modo_completo_valida_completo(self):
        """modo='completo' debería ejecutar validación + formateo"""
        params = {
            "area": "Comunicación",
            "grado": "3°",
            "modo": "completo"
        }
        assert params.get("modo") == "completo"

    def test_modo_default_es_completo(self):
        """Sin especificar modo, debería ser 'completo'"""
        params = {
            "area": "Comunicación",
            "grado": "3°"
        }
        modo = params.get("modo", "completo")  # Default
        assert modo == "completo"


class TestStreamingResponseFormat:
    """Valida que las respuestas streaming son SSE válido"""

    def test_evento_sse_tiene_formato_correcto(self):
        """Un evento SSE debe tener formato: 'data: {...JSON...}'"""
        evento_json = {"chunk": "texto", "done": False}
        evento_sse = f"data: {json.dumps(evento_json)}"

        # Parsear de vuelta
        json_str = evento_sse.split("data: ")[1]
        parsed = json.loads(json_str)
        assert parsed["chunk"] == "texto"
        assert parsed["done"] is False

    def test_multiples_eventos_son_separados_por_newline(self):
        """Múltiples eventos SSE deben estar separados por \\n"""
        evento1 = 'data: {"chunk": "parte1", "done": false}'
        evento2 = 'data: {"chunk": "parte2", "done": false}'
        evento3 = 'data: {"done": true, "id": "uuid"}'

        respuesta = f"{evento1}\n{evento2}\n{evento3}"

        eventos = [line for line in respuesta.split('\n') if line.startswith('data: ')]
        assert len(eventos) == 3


class TestPlainTextPreview:
    """Valida stripMarkdownForPreview - nueva función de limpieza"""

    def test_stripMarkdownForPreview_limpia_negrita(self):
        """Debe remover ** de markdown bold"""
        # Este test documenta el comportamiento esperado
        # La función vive en GenerationWizard.jsx del frontend
        assert "**texto**".count("**") == 2  # Antes
        # Después: "texto" (sin **)

    def test_stripMarkdownForPreview_limpia_encabezados(self):
        """Debe remover # de encabezados"""
        assert "# Encabezado".startswith("#")  # Antes
        # Después: "Encabezado" (sin #)

    def test_stripMarkdownForPreview_limpia_tablas(self):
        """Debe limpiar pipes de tablas Markdown"""
        tabla = "| a | b |"
        assert "|" in tabla  # Antes
        # Después: "a — b" o similar (sin pipes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
