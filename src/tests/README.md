# Test Suite

Suite de tests automatizados para validar la refactorización de generación unificada en streaming.

## Setup

### 1. Instalar pytest (si aún no está instalado)

```bash
pip install pytest pytest-mock pytest-asyncio
```

### 2. Estructura de archivos

```
src/tests/
├── __init__.py                    # Marca como paquete
├── conftest.py                    # Fixtures compartidas y configuración
├── test_generation_service.py     # Tests del servicio de generación
├── test_streaming_endpoints.py    # Tests de endpoints (próximo)
└── README.md                      # Este archivo
```

## Ejecución

### Todos los tests

**En Windows (PowerShell):**
```bash
.\run_tests.ps1
```

**En Linux/Mac:**
```bash
./run_tests.sh
```

**Con pytest directamente:**
```bash
python -m pytest src/tests -v
```

### Tests específicos

```bash
# Solo tests de generation_service
.\run_tests.ps1 test_generation_service

# Solo tests que contengan "unidad" en el nombre
.\run_tests.ps1 unidad

# Con output más detallado
python -m pytest src/tests -vv --tb=long
```

## Qué valida cada archivo

### `test_generation_service.py`

**TestGenerationServiceUnidadStreaming:**
- ✅ Modo `solo_generador` no pasa por validación
- ✅ Modo `completo` pasa por validación y formateo
- ✅ Evento final incluye campos parseados (no solo id)
- ✅ `generador_agent.construir_prompt_unidad()` se llama correctamente

**TestGenerationServiceSesionStreaming:**
- ✅ Sesión streaming funciona igual que Unidad
- ✅ Se usa `construir_prompt_sesion()` (no unidad)
- ✅ Se llama `validar_y_formatear_sesion()` (no unidad)

**TestGeneratorAgentPromptExtraction:**
- ✅ `construir_prompt_unidad()` no duplica lógica
- ✅ Extrae parámetros correctamente

## Estructura de tests

Cada test sigue el patrón **AAA** (Arrange, Act, Assert):

1. **Arrange**: configura mocks y fixtures
2. **Act**: ejecuta el código siendo probado
3. **Assert**: valida el comportamiento

Ejemplo:

```python
def test_unidad_stream_solo_generador_sin_validacion(self, service, mock_user, mock_db):
    # Arrange
    mock_gen.construir_prompt_unidad.return_value = "test prompt"
    
    # Act
    events = list(service.generar_unidad_stream_events(params, mock_user, mock_db))
    
    # Assert
    mock_coordinator.assert_not_called()  # No se validó
    final_event["done"] is True           # Evento terminó
```

## Fixtures disponibles

Definidas en `conftest.py`:

| Fixture | Descripción |
|---------|-------------|
| `mock_bedrock_client` | Mock de BedrockClient para generación |
| `mock_prompt_manager` | Mock de PromptManager para prompts |
| `mock_db_session` | Mock de SQLAlchemy Session |
| `test_user` | Mock de User con stats |

Úsalas en tus tests:

```python
def test_ejemplo(self, mock_bedrock_client, test_user, mock_db_session):
    # test_user es un Mock de User con stats
    # mock_db_session es un Mock de Session
    ...
```

## Mocking Strategy

Para evitar hacer llamadas reales a Bedrock (lentas y costosas), todos los tests usan mocks con `@patch`:

```python
@patch('api.services.generation_service.GeneratorAgent')
def test_algo(self, mock_gen_class):
    # GeneratorAgent está mockeado
    mock_gen = Mock()
    mock_gen_class.return_value = mock_gen
    mock_gen.construir_prompt_unidad.return_value = "test prompt"
    ...
```

## Agregar nuevos tests

1. Crea una clase que herede de `object` o usa pytest sin clase
2. Crea métodos `test_*()` con el fixture que necesites
3. Usa `@patch()` para los mocks de I/O pesado
4. Valida con `assert` al final

Plantilla:

```python
class TestMyFeature:
    @pytest.fixture
    def service(self):
        return GenerationService()
    
    @patch('api.services.generation_service.GeneratorAgent')
    def test_mi_feature(self, mock_gen, service):
        # Arrange
        mock_gen.return_value.metodo.return_value = "resultado"
        
        # Act
        resultado = service.algo(params)
        
        # Assert
        assert resultado == "esperado"
```

## CI/CD Integration (futuro)

Cuando esté listo, agregar a `.github/workflows/test.yml`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt pytest
      - run: pytest src/tests -v
```

## Notas

- Los tests no requieren Bedrock real (todo está mockeado)
- Ejecución típica: < 2 segundos para todos
- Si un test falla, leer el error y revisar los mocks vs el código actual
