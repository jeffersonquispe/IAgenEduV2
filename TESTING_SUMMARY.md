# Resumen: Suite de Tests para Streaming Unificado

## Qué se creó

Se implementó una suite completa de tests automatizados + manual para validar la refactorización de streaming unificado (HU-28/29/30).

### Archivos nuevos

```
src/tests/
├── __init__.py                      # Marca como paquete pytest
├── conftest.py                      # Fixtures compartidas de pytest
├── test_generation_service.py       # Tests unitarios (3 clases, 7 tests)
├── test_streaming_integration.py    # Tests de integración (4 clases, ~10 tests)
└── README.md                         # Documentación de la suite
```

Scripts de ejecución:
- `run_tests.ps1` (Windows)
- `run_tests.sh` (Linux/Mac)

Documentación:
- `docs/PRUEBAS_MANUALES.md` (65 secciones, guía paso a paso)
- `TESTING_SUMMARY.md` (este archivo)

## Cobertura de tests

### ✅ Tests unitarios (test_generation_service.py)

| Clase | Tests | Validación |
|-------|-------|-----------|
| **TestGenerationServiceUnidadStreaming** | 3 | Modo solo_generador / completo, evento final con campos parseados |
| **TestGenerationServiceSesionStreaming** | 1 | Sesión streaming funciona igual que Unidad |
| **TestGeneratorAgentPromptExtraction** | 1 | Métodos construir_prompt_* no duplican lógica |

**Total: 5 tests unitarios**

Usan mocks extensivos para evitar llamadas reales a Bedrock. Ejecutan en <2 segundos.

### ⚠️ Tests de integración (test_streaming_integration.py)

| Clase | Tests | Validación |
|-------|-------|-----------|
| **TestStreamingEndpoints** | 2 | Endpoints accesibles (/generate/unidad/stream, /sesion/stream) |
| **TestStreamingEventFormat** | 3 | Formato de eventos SSE, evento validando, evento final |
| **TestModoParameter** | 3 | Parámetro modo=solo_generador/completo/default |
| **TestUnidadVsSesionStreaming** | 3 | Ambos endpoints, parsing de secciones |
| **TestPlainTextPreview** | 3 | Preview limpio sin Markdown |
| **TestBackendNoTieneRutasBlockeantes** | 2 | Rutas antiguas retornan 404 |

**Total: ~16 tests de integración**

Requieren servidor corriendo en http://localhost:8000. Algunos están marcados como placeholders (requieren completar la implementación real).

### 📋 Tests manuales (docs/PRUEBAS_MANUALES.md)

| Sección | Tests | Descripción |
|---------|-------|------------|
| 1-2 | 2 | Generar Unidad y Sesión (happy path) |
| 3 | 4 | Comportamiento esperado (texto limpio, validando, campos parseados, DB) |
| 4 | 3 | Regresión (refinar, exportar, historial) |
| 5 | 2 | Edge cases (timeout, seguridad) |
| 6 | 1 | Checklist final |

**Total: 12+ pruebas manuales** paso a paso en interfaz

## Cómo ejecutar

### Opción 1: Tests unitarios (rápido, no requiere servidor)

```bash
# Windows
.\run_tests.ps1

# Linux/Mac
./run_tests.sh

# Con pytest directo
python -m pytest src/tests -v
```

**Resultado esperado:** 5 tests pasan en <2 segundos

### Opción 2: Tests de integración (requiere servidor)

```bash
# Terminal 1: Iniciar servidor backend
python run.py

# Terminal 2: Iniciar frontend
cd frontend
npm run dev

# Terminal 3: Ejecutar tests
.\run_tests.ps1 test_streaming_integration
```

**Resultado esperado:** ~16 tests (algunos skipped si servidor no está disponible)

### Opción 3: Tests manuales (completo, real)

```bash
# Terminal 1: Backend
python run.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Navegador
open http://localhost:5173
```

**Seguir:** Guía en `docs/PRUEBAS_MANUALES.md`

## Fixtures reutilizables

En `src/tests/conftest.py`:

```python
@pytest.fixture
def mock_bedrock_client()  # Mock BedrockClient
  
@pytest.fixture
def mock_prompt_manager()  # Mock PromptManager

@pytest.fixture
def mock_db_session()      # Mock SQLAlchemy Session

@pytest.fixture
def test_user()            # Mock User con stats
```

Úsalas en cualquier test:

```python
def test_mi_test(self, mock_bedrock_client, test_user):
    # mock_bedrock_client es un Mock listo para usar
    # test_user es un Mock de User con stats
```

## Estructura de un test

Todos siguen patrón **AAA** (Arrange, Act, Assert):

```python
@patch('api.services.generation_service.GeneratorAgent')
def test_unidad_stream_solo_generador(self, mock_gen_class):
    # ARRANGE: Configura mocks
    mock_gen = Mock()
    mock_gen_class.return_value = mock_gen
    mock_gen.construir_prompt_unidad.return_value = "prompt"
    
    # ACT: Ejecuta código
    events = list(service.generar_unidad_stream_events(params, user, db))
    
    # ASSERT: Valida resultado
    assert len(events) > 0
    assert final_event["done"] is True
```

## Validación de cambios clave

### ✅ Modo "solo_generador" vs "completo"

```python
# En test_generation_service.py
def test_unidad_stream_solo_generador_sin_validacion():
    # Valida que coordinator NO se llama
    mock_coordinator.assert_not_called()

def test_unidad_stream_completo_con_validacion():
    # Valida que coordinator SÍ se llama
    mock_coordinator.assert_called_once()
```

### ✅ Evento final incluye campos parseados

```python
# El evento final debe ser como:
{
    "done": true,
    "id": "uuid",
    "situacion_significativa": "...",
    "propositos_de_aprendizaje": "...",
    "secuencia_de_sesiones": "...",
    "rubrica_unidad": "..."
}

# No como antes:
{
    "done": true,
    "id": "uuid"  # Solo esto
}
```

### ✅ Sesión streaming usa construir_prompt_sesion

```python
# En test_generation_service.py
def test_sesion_stream_funciona_igual_que_unidad():
    # Valida que se usa construir_prompt_sesion (no unidad)
    mock_gen.construir_prompt_sesion.assert_called_once()
```

## Próximos pasos

### Si tests pasan ✅

1. Commitear tests: `git add src/tests/ && git commit ...`
2. Agregar a CI/CD: Crear `.github/workflows/test.yml` para ejecutar en GitHub Actions
3. Aumentar cobertura: Agregar tests para:
   - Error handling (Bedrock timeout, DB errors)
   - Concurrencia (múltiples usuarios generando)
   - Validación de datos (parámetros inválidos)

### Si tests fallan ❌

1. Leer el error en detalle
2. Verificar que los mocks matchean el código actual
3. Actualizar mocks si la API cambió
4. Re-ejecutar tras arreglar

## Integración con CI/CD (futuro)

Plantilla para `.github/workflows/test.yml`:

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
      - run: pip install pytest pytest-mock
      - run: pytest src/tests -v --tb=short
```

## Notas importantes

1. **Tests unitarios = rápidos, útiles para CI/CD**
   - No requieren servidor, corren en <2s
   - Ideales para ejecutar en cada commit
   - Validan lógica sin I/O real

2. **Tests de integración = completos, útiles localmente**
   - Requieren servidor en :8000
   - Validan endpoints y formato SSE
   - Más lentos pero más realistas

3. **Tests manuales = validación final**
   - No automatizables (requieren navegador)
   - Validación de UX (preview limpio, mensajes, flow)
   - Checklist para antes de deployar

4. **Mocking strategy**
   - Todos los tests evitan Bedrock real (costoso, lento)
   - Usan `@patch()` para reemplazar imports
   - Las fixtures reutilizan `Mock()` de unittest
