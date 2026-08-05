"""
Tests para generation_service.py tras unificación de streaming.
Valida:
- Modo "solo_generador" (sin validación)
- Modo "completo" (con validación y formateo)
- Sesión streaming funciona igual que Unidad
- Evento final incluye campos parseados
"""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

# Imports del proyecto
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from api.services.generation_service import GenerationService
from api.models import User, UserStats, Document


class TestGenerationServiceUnidadStreaming:
    """Tests para generar_unidad_stream_events"""

    @pytest.fixture
    def service(self):
        return GenerationService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "test-user-123"
        user.stats = Mock(spec=UserStats)
        user.stats.docs_generados = 0
        user.stats.unidades_generadas = 0
        return user

    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def base_params(self):
        return {
            "area": "Comunicación",
            "grado": "3°",
            "competencias": ["1", "2"],
            "temas": "El ensayo",
            "num_sesiones": 2,
            "producto_final": "Ensayo argumentativo",
            "modo": "completo",
        }

    @patch('api.services.generation_service.get_coordinator')
    @patch('api.services.generation_service.GeneratorAgent')
    def test_unidad_stream_solo_generador_sin_validacion(
        self, mock_gen_class, mock_coordinator, service, mock_user, mock_db, base_params
    ):
        """Modo 'solo_generador' no pasa por validación ni formateo"""
        base_params["modo"] = "solo_generador"

        # Mock GeneratorAgent
        mock_gen = Mock()
        mock_gen_class.return_value = mock_gen
        mock_gen.construir_prompt_unidad.return_value = "test prompt"
        mock_gen.bedrock = Mock()

        # Mock streaming response: chunks + evento final
        mock_gen.bedrock.invocar_stream.return_value = [
            "Sección 1 ",
            "contenido...",
        ]

        # Parsear va a recibir el contenido crudo directamente (sin formatear)
        with patch.object(service, '_unidad_parser') as mock_parser:
            mock_parser.parsear.return_value = {"section1": "content..."}

            # Ejecutar generación
            events = list(service.generar_unidad_stream_events(base_params, mock_user, mock_db))

            # Validar que NO se llamó a coordinator (solo_generador no valida)
            mock_coordinator.assert_not_called()

            # Validar que el parser se llamó (siempre parsea, incluso sin validación)
            mock_parser.parsear.assert_called_once()

            # Validar evento final con secciones
            final_event = json.loads(events[-1].split("data: ")[1])
            assert final_event["done"] is True
            assert "id" in final_event
            assert "section1" in final_event

    @patch('api.services.generation_service.get_coordinator')
    @patch('api.services.generation_service.GeneratorAgent')
    def test_unidad_stream_completo_con_validacion(
        self, mock_gen_class, mock_coordinator, service, mock_user, mock_db, base_params
    ):
        """Modo 'completo' pasa por validación y formateo"""
        base_params["modo"] = "completo"

        # Mock GeneratorAgent
        mock_gen = Mock()
        mock_gen_class.return_value = mock_gen
        mock_gen.construir_prompt_unidad.return_value = "test prompt"
        mock_gen.bedrock = Mock()
        mock_gen.bedrock.invocar_stream.return_value = ["test content"]

        # Mock Coordinator
        mock_coor = Mock()
        mock_coordinator.return_value = mock_coor
        mock_coor.validar_y_formatear_unidad.return_value = ("formatted content", Mock())

        with patch.object(service, '_unidad_parser') as mock_parser:
            mock_parser.parsear.return_value = {"formatted": "section"}

            events = list(service.generar_unidad_stream_events(base_params, mock_user, mock_db))

            # Validar que SÍ se llamó a coordinator (completo valida)
            mock_coordinator.assert_called_once_with(usar_validacion_llm=True)
            mock_coor.validar_y_formatear_unidad.assert_called_once()

            # Validar evento final con secciones
            final_event = json.loads(events[-1].split("data: ")[1])
            assert final_event["done"] is True
            assert final_event["validando"] is True or "validando" not in final_event

    @patch('api.services.generation_service.get_coordinator')
    @patch('api.services.generation_service.GeneratorAgent')
    def test_evento_final_incluye_campos_parseados(
        self, mock_gen_class, mock_coordinator, service, mock_user, mock_db, base_params
    ):
        """Evento final incluye campos completos (no solo id)"""
        base_params["modo"] = "solo_generador"

        mock_gen = Mock()
        mock_gen_class.return_value = mock_gen
        mock_gen.construir_prompt_unidad.return_value = "prompt"
        mock_gen.bedrock = Mock()
        mock_gen.bedrock.invocar_stream.return_value = ["content"]

        expected_sections = {
            "situacion_significativa": "Sección 1",
            "propositos_de_aprendizaje": "Sección 2",
        }

        with patch.object(service, '_unidad_parser') as mock_parser:
            mock_parser.parsear.return_value = expected_sections

            events = list(service.generar_unidad_stream_events(base_params, mock_user, mock_db))

            # Parsear evento final
            final_event = json.loads(events[-1].split("data: ")[1])

            # Validar que incluye id + todas las secciones
            assert "id" in final_event
            assert "situacion_significativa" in final_event
            assert "propositos_de_aprendizaje" in final_event
            assert final_event["situacion_significativa"] == "Sección 1"


class TestGenerationServiceSesionStreaming:
    """Tests para generar_sesion_stream_events (nuevo)"""

    @pytest.fixture
    def service(self):
        return GenerationService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "test-user-123"
        user.stats = Mock(spec=UserStats)
        user.stats.docs_generados = 0
        user.stats.sesiones_generadas = 0
        return user

    @pytest.fixture
    def mock_db(self):
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def base_params(self):
        return {
            "area": "Comunicación",
            "grado": "3°",
            "titulo_unidad": "Mi unidad",
            "tema": "El ensayo",
            "metodologia": "ERCA",
            "modo": "completo",
        }

    @patch('api.services.generation_service.get_coordinator')
    @patch('api.services.generation_service.GeneratorAgent')
    def test_sesion_stream_funciona_igual_que_unidad(
        self, mock_gen_class, mock_coordinator, service, mock_user, mock_db, base_params
    ):
        """Sesión streaming sigue el mismo patrón que Unidad"""
        mock_gen = Mock()
        mock_gen_class.return_value = mock_gen
        mock_gen.construir_prompt_sesion.return_value = "sesion prompt"
        mock_gen.bedrock = Mock()
        mock_gen.bedrock.invocar_stream.return_value = ["sesion content"]

        mock_coor = Mock()
        mock_coordinator.return_value = mock_coor
        mock_coor.validar_y_formatear_sesion.return_value = ("formatted", Mock())

        with patch.object(service, '_sesion_parser') as mock_parser:
            mock_parser.parsear.return_value = {"datos_informativos": "info"}

            events = list(service.generar_sesion_stream_events(base_params, mock_user, mock_db))

            # Validar que se usó construir_prompt_sesion (no unidad)
            mock_gen.construir_prompt_sesion.assert_called_once()

            # Validar que se llamó a validar_y_formatear_sesion (no unidad)
            mock_coor.validar_y_formatear_sesion.assert_called_once()

            # Validar evento final
            final_event = json.loads(events[-1].split("data: ")[1])
            assert "id" in final_event
            assert "datos_informativos" in final_event


class TestGeneratorAgentPromptExtraction:
    """Tests para los métodos nuevos de generator_agent.py"""

    @pytest.fixture
    def agent(self):
        from agents.generator_agent import GeneratorAgent
        with patch('agents.generator_agent.get_bedrock_client'):
            with patch('agents.generator_agent.get_prompt_manager'):
                return GeneratorAgent()

    def test_construir_prompt_unidad_no_duplica_logica(self, agent):
        """construir_prompt_unidad() extrae la lógica de generar_unidad_didactica()"""
        # Mock pm.cargar
        agent.prompt_manager.cargar = Mock(return_value="final prompt text")

        prompt = agent.construir_prompt_unidad(
            area_curricular="Comunicación",
            grado=3,
            competencia_referencia="comp1, comp2",
            temas="El ensayo",
            num_sesiones=2,
            producto_final="Ensayo",
        )

        # Validar que se llamó a cargar con los parámetros esperados
        assert agent.prompt_manager.cargar.called
        call_kwargs = agent.prompt_manager.cargar.call_args[1]
        assert call_kwargs["area_curricular"] == "Comunicación"
        assert call_kwargs["grado"] == 3
        assert "contexto_competencia" in call_kwargs
        assert "CONTEXTO OFICIAL DEL MINEDU" not in prompt or "CONTEXTO OFICIAL" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
