# Setup de Testing

## Instalación de dependencias

### 1. Instalar pytest y plugins recomendados

```bash
pip install pytest pytest-mock pytest-asyncio
```

Esto instala:
- `pytest`: Framework de testing
- `pytest-mock`: Simpifica uso de mocks (alternativa a `unittest.mock`)
- `pytest-asyncio`: Soporte para tests async/await

### 2. Verificar instalación

```bash
pytest --version
```

Debería ver algo como: `pytest 7.x.x`

## Ejecución de tests

### Opción A: Usar scripts provided

**Windows (PowerShell):**
```bash
.\run_tests.ps1
```

**Linux/Mac (Bash):**
```bash
./run_tests.sh
```

### Opción B: Usar pytest directamente

```bash
# Todos los tests
pytest src/tests -v

# Con más detalle
pytest src/tests -vv --tb=long

# Solo un archivo
pytest src/tests/test_generation_service.py -v

# Solo tests que contengan "unidad"
pytest src/tests -k "unidad" -v
```

## Configuración de pytest (opcional)

Si quieres configurar pytest globalmente, crear `pytest.ini` en la raíz del proyecto:

```ini
[pytest]
testpaths = src/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

Esto hace que `pytest` sin argumentos busque en `src/tests/` automáticamente.

## Integración con VS Code (opcional)

1. Instalar extensión "Python" de Microsoft
2. Instalar "Test Explorer" de Littlefox Studios
3. Crear `.vscode/settings.json`:

```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["src/tests"],
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true
}
```

4. Abrir el Test Explorer sidebar (icono de frasco de laboratorio)
5. Ver y ejecutar tests desde la interfaz

## Troubleshooting

### Error: "No module named pytest"

```bash
# Solución
pip install pytest
```

### Error: "ModuleNotFoundError: No module named 'api'"

Esto significa que pytest no encuentra el módulo del proyecto. Soluciones:

**Opción 1:** Ejecutar desde la raíz del proyecto
```bash
cd c:\Users\Jeff\Desktop\Tesis 2\ia-gen-edu
pytest src/tests
```

**Opción 2:** Crear `pytest.ini` en raíz con:
```ini
[pytest]
pythonpath = .
```

**Opción 3:** Editar conftest.py para manejar imports (ya está hecho en nuestro conftest.py):
```python
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
```

### Error: "assert_called_once" no existe

Esto indica que estás usando `Mock` incorrectamente. Solución:

```python
from unittest.mock import Mock

mock_obj = Mock()
mock_obj.method()
mock_obj.method.assert_called_once()  # Correcto
mock_obj.assert_called_once()         # Incorrecto
```

## Próximas pruebas

Después de instalar pytest y verificar que los tests funcionan:

1. Ejecutar todos los tests:
   ```bash
   pytest src/tests -v
   ```

2. Verificar cobertura (opcional):
   ```bash
   pip install pytest-cov
   pytest src/tests --cov=src --cov-report=html
   ```

3. Abrir `htmlcov/index.html` para ver qué código está siendo testeado

## Referencia rápida

```bash
# Instalar todo
pip install pytest pytest-mock pytest-asyncio pytest-cov

# Ejecutar tests
pytest src/tests -v

# Ejecutar con cobertura
pytest src/tests --cov=src -v

# Ejecutar un test específico
pytest src/tests/test_generation_service.py::TestGenerationServiceUnidadStreaming::test_unidad_stream_solo_generador_sin_validacion

# Ejecutar tests que matcheen un pattern
pytest src/tests -k "unidad" -v

# Ejecutar y parar al primer fallo
pytest src/tests -x -v

# Ejecutar últimos tests que fallaron
pytest src/tests --lf -v
```
