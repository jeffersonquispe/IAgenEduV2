"""
Configuración compartida de pytest para todos los tests.
Define fixtures comunes, configuración de logging, y helpers.
"""
import pytest
import sys
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def setup_path():
    """Asegura que el proyecto pueda importarse desde los tests"""
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_bedrock_client():
    """Mock de BedrockClient para tests que necesitan generación"""
    from unittest.mock import Mock
    client = Mock()
    client.invocar = Mock(return_value="Contenido generado de prueba")
    client.invocar_stream = Mock(return_value=iter([
        "Chunk 1 ",
        "Chunk 2 ",
        "Chunk 3"
    ]))
    return client


@pytest.fixture
def mock_prompt_manager():
    """Mock de PromptManager para tests que necesitan prompts"""
    from unittest.mock import Mock
    pm = Mock()
    pm.cargar = Mock(return_value="Prompt template renderizado")
    return pm


@pytest.fixture
def mock_db_session():
    """Mock de SQLAlchemy Session para tests de persistencia"""
    from unittest.mock import Mock
    from sqlalchemy.orm import Session
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def test_user():
    """Mock de User con stats para tests"""
    from unittest.mock import Mock
    from api.models import User, UserStats

    user = Mock(spec=User)
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.stats = Mock(spec=UserStats)
    user.stats.docs_generados = 0
    user.stats.unidades_generadas = 0
    user.stats.sesiones_generadas = 0
    user.stats.mejoras_realizadas = 0
    user.stats.puntos = 0
    user.stats.areas_usadas = []
    user.stats.grados_usados = []
    return user
