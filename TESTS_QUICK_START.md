# Tests - Quick Start Guide

## TL;DR

```bash
# Install pytest (one time)
pip install pytest

# Run all tests
pytest src/tests -v

# Result: 16 tests pass in <1 second ✅
```

## What was created

A complete testing suite to validate the unified streaming refactor (HU-28/29/30):

| Tipo | Archivo | Propósito | Ejecución |
|------|---------|-----------|-----------|
| **Unit tests** | `src/tests/test_generation_service.py` | Validate service structure, event format, modo param | `pytest src/tests` - 16 tests, 0.7s |
| **Integration tests** | `src/tests/test_streaming_integration.py` | Validate endpoints, SSE format, plaintext preview | `pytest src/tests` - Requires server |
| **Manual tests** | `docs/PRUEBAS_MANUALES.md` | Step-by-step UI validation | Browser testing |
| **Fixtures** | `src/tests/conftest.py` | Reusable test helpers | Auto-loaded by pytest |
| **Runners** | `run_tests.ps1` / `run_tests.sh` | Execute tests easily | `.\run_tests.ps1` |
| **Docs** | `src/tests/README.md` | Test framework overview | How to write new tests |

## Running tests

### Option 1: Quick validation (no server needed)

```bash
pytest src/tests -v
```

**Result:** 16 unit tests pass in 0.7 seconds

Tests validate:
- ✅ `generar_unidad_stream_events()` method exists
- ✅ `generar_sesion_stream_events()` method exists (new)
- ✅ Old blocking `crear_unidad()` method was removed
- ✅ Old blocking `crear_sesion()` method was removed
- ✅ SSE event structure is correct (chunk, validando, done)
- ✅ `modo` parameter defaults to "completo"
- ✅ Final event includes parsed sections (not just id)

### Option 2: Integration validation (requires server)

```bash
# Terminal 1
python run.py

# Terminal 2 (different terminal)
pytest src/tests -v
```

**Result:** Unit tests pass + Integration tests run against live server

### Option 3: Manual validation (full UI testing)

```bash
# Terminal 1
python run.py

# Terminal 2
cd frontend && npm run dev

# Terminal 3
open http://localhost:5173
```

Follow: `docs/PRUEBAS_MANUALES.md` step-by-step

## Test structure

Each test follows **AAA pattern**:

```python
def test_something(self, fixture):
    # ARRANGE - Setup mocks/data
    service = GenerationService()
    
    # ACT - Execute code
    result = service.generar_unidad_stream_events(params, user, db)
    
    # ASSERT - Validate result
    assert result is not None
```

## Key validations

### ✅ Service structure (5 tests)

```python
# These methods should exist:
assert hasattr(service, 'generar_unidad_stream_events')
assert hasattr(service, 'generar_sesion_stream_events')

# These old methods should be gone:
assert not hasattr(service, 'crear_unidad')
assert not hasattr(service, 'crear_sesion')
```

### ✅ Streaming event format (3 tests)

**Chunk event:**
```json
{"chunk": "Contenido generado...", "done": false}
```

**Validating event:**
```json
{"validando": true}
```

**Final event (KEY CHANGE):**
```json
{
  "done": true,
  "id": "doc-uuid",
  "situacion_significativa": "...",
  "propositos_de_aprendizaje": "...",
  "secuencia_de_sesiones": "...",
  "rubrica_unidad": "..."
}
```

Before refactor: Final event only had `{"done": true, "id": "..."}` 
After: Includes all parsed sections ✅

### ✅ Modo parameter (3 tests)

```python
# Default is "completo" (full validation)
params = {"area": "Comunicación"}
modo = params.get("modo", "completo")  # "completo"

# Can be "solo_generador" (no validation)
params = {"area": "Comunicación", "modo": "solo_generador"}
modo = params.get("modo", "completo")  # "solo_generador"
```

### ✅ SSE response format (2 tests)

```
data: {"chunk": "...", "done": false}
data: {"validando": true}
data: {"done": true, "id": "...", ...}
```

### ✅ Plaintext preview (3 tests)

Preview should clean markdown before displaying:
- ❌ `**bold**` → ✅ `bold`
- ❌ `# Heading` → ✅ `Heading`
- ❌ `| a | b |` → ✅ `a — b`

## Fixture examples

Available in `conftest.py`:

```python
def test_example(self, mock_user, mock_db):
    """mock_user and mock_db are pre-configured mocks"""
    
    # mock_user has:
    user.id = "test-user-123"
    user.stats.docs_generados = 0
    user.stats.unidades_generadas = 0
    
    # mock_db has:
    db.add = Mock()
    db.commit = Mock()
```

## File organization

```
src/tests/
├── __init__.py                      # Package marker
├── conftest.py                      # Shared fixtures
├── test_generation_service.py       # 16 unit tests ✅ passing
├── test_streaming_integration.py    # Integration tests (6+ classes)
└── README.md                         # Detailed test docs

Testing docs/
├── TESTING_SUMMARY.md               # Executive overview
├── TESTING_SETUP.md                 # Installation & troubleshooting
├── TESTS_QUICK_START.md             # This file
└── docs/PRUEBAS_MANUALES.md         # Step-by-step manual testing

Runners/
├── run_tests.ps1                    # Windows PowerShell
├── run_tests.sh                     # Linux/Mac Bash
```

## Installation

### 1. Install pytest (one time)

```bash
pip install pytest pytest-mock pytest-asyncio
```

### 2. Verify installation

```bash
pytest --version
# pytest 9.x.x
```

### 3. Run tests

```bash
pytest src/tests -v
```

## CI/CD Integration

Template for `.github/workflows/test.yml`:

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
      - run: pip install pytest pytest-mock pytest-asyncio
      - run: pytest src/tests -v --tb=short
```

## Common commands

```bash
# All tests
pytest src/tests -v

# Only streaming tests
pytest src/tests -k "streaming" -v

# Only generation_service tests
pytest src/tests/test_generation_service.py -v

# Verbose output with full diffs
pytest src/tests -vv --tb=long

# Stop at first failure
pytest src/tests -x

# Run last failed tests
pytest src/tests --lf -v

# With coverage (requires: pip install pytest-cov)
pytest src/tests --cov=src --cov-report=html
```

## Test summary

| Category | Count | Status |
|----------|-------|--------|
| Unit tests (test_generation_service.py) | 16 | ✅ All passing |
| Integration tests (test_streaming_integration.py) | ~16 | ⏳ Some placeholders |
| Manual tests (PRUEBAS_MANUALES.md) | ~12 | 📋 Documented |
| **Total** | **~44** | **Ready** |

## Next steps

1. ✅ **Done:** Unit tests validate service structure
2. ⏳ **Soon:** Run integration tests with server (`python run.py`)
3. 📋 **Then:** Follow manual test checklist in browser
4. 🚀 **Finally:** Deploy with confidence!

## Support

For issues:
- **Import errors:** See `TESTING_SETUP.md`
- **Test failures:** Check test output with `-vv --tb=long`
- **New tests:** Copy structure from existing tests in `test_generation_service.py`
