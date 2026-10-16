"""
Tests de integración del flujo de generación (HU-35, HU-37, HU-45).

Ejercitan GenerationService.generar_*_stream_events de punta a punta con
Bedrock y el coordinador reemplazados por dobles, y una sesión de BD simulada.
No requieren servidor, red ni credenciales.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.api.services.generation_service import GenerationService

UNIDAD_MD = """| ITEM | CONTENIDO |
|------|-----------|
| **TÍTULO DE LA UNIDAD DIDÁCTICA** | Unidad de prueba |
| **II. SITUACIÓN SIGNIFICATIVA** | Una situación significativa de prueba suficientemente larga. |
| **III. PROPÓSITOS DE APRENDIZAJE** | Competencias: A. Criterios de evaluación: x. |
| **SECUENCIA DE SESIONES** | Sesión 1: Tema uno. Criterio de evaluación: c1. |
"""

SESION_MD = """| ITEM | CONTENIDO |
|------|-----------|
| **DATOS INFORMATIVOS** | Colegio X |
| **SITUACIÓN SIGNIFICATIVA** | Situación de prueba. |
| **RETO** | ¿Cómo podemos resolverlo? |
| **PROPÓSITOS DE APRENDIZAJE** | Competencia A |
| **SECUENCIA DIDÁCTICA** | INICIO 10 min. DESARROLLO 60 min. CIERRE 20 min. |
| **MATERIALES Y RECURSOS** | Pizarra |
"""


def _eventos(generador):
    return [json.loads(l[len("data: "):]) for l in generador if l.startswith("data: ")]


@pytest.fixture
def user():
    stats = SimpleNamespace(
        docs_generados=0, unidades_generadas=0, sesiones_generadas=0,
        areas_usadas=[], grados_usados=[],
    )
    return SimpleNamespace(id="user-1", stats=stats)


@pytest.fixture
def db():
    sesion = MagicMock()
    # _plantilla_activa y búsqueda de unidad padre: sin resultados
    sesion.query.return_value.filter.return_value.first.return_value = None
    return sesion


@pytest.fixture
def service():
    svc = GenerationService()
    svc._save_version = MagicMock()
    svc._save_pipeline_run = MagicMock()
    return svc


@pytest.fixture
def fake_agents():
    """Reemplaza GeneratorAgent y el coordinador; devuelve el generador falso."""
    def _montar(texto):
        gen = MagicMock()
        gen.construir_prompt_unidad.return_value = "PROMPT"
        gen.construir_prompt_sesion.return_value = "PROMPT"
        gen.bedrock.invocar_stream.return_value = iter([texto[:50], texto[50:]])
        coord = MagicMock()
        coord.validar_y_formatear_unidad.return_value = (texto, None)
        coord.validar_y_formatear_sesion.return_value = (texto, None)
        return gen, coord
    return _montar


def _parchear(gen, coord):
    return (
        patch("src.agents.generator_agent.GeneratorAgent", return_value=gen),
        patch("src.agents.coordinator.get_coordinator", return_value=coord),
    )


def test_unidad_flujo_completo_actualiza_stats_y_emite_evento_final(service, db, user, fake_agents):
    gen, coord = fake_agents(UNIDAD_MD)
    p1, p2 = _parchear(gen, coord)
    params = {"area": "Matemática", "grado": 2, "competencias": ["Comp A", "Comp B"],
              "num_sesiones": 4, "temas": "t"}
    with p1, p2:
        eventos = _eventos(service.generar_unidad_stream_events(params, user, db))

    assert any("chunk" in e for e in eventos)
    final = eventos[-1]
    assert final["done"] is True and "error" not in final and final["id"]
    db.add.assert_called_once()
    db.commit.assert_called()
    assert user.stats.docs_generados == 1 and user.stats.unidades_generadas == 1
    # HU-37
    assert user.stats.areas_usadas == ["Matemática"]
    assert user.stats.grados_usados == ["2"]


def test_unidad_hu35_competencias_se_pasan_separadas_por_salto_de_linea(service, db, user, fake_agents):
    gen, coord = fake_agents(UNIDAD_MD)
    p1, p2 = _parchear(gen, coord)
    params = {"area": "Matemática", "grado": 1, "competencias": ["Comp A", "Comp B"]}
    with p1, p2:
        list(service.generar_unidad_stream_events(params, user, db))
    kwargs = gen.construir_prompt_unidad.call_args.kwargs
    assert kwargs["competencia_referencia"] == "Comp A\nComp B"


def test_unidad_hu45_rechaza_mas_de_2_competencias_sin_llamar_a_bedrock(service, db, user, fake_agents):
    gen, coord = fake_agents(UNIDAD_MD)
    p1, p2 = _parchear(gen, coord)
    params = {"area": "Matemática", "grado": 1, "competencias": ["A", "B", "C"]}
    with p1, p2:
        eventos = _eventos(service.generar_unidad_stream_events(params, user, db))
    assert len(eventos) == 1 and "Máximo 2" in eventos[0]["error"]
    gen.bedrock.invocar_stream.assert_not_called()
    db.add.assert_not_called()
    assert user.stats.docs_generados == 0


def test_sesion_flujo_completo_actualiza_stats(service, db, user, fake_agents):
    gen, coord = fake_agents(SESION_MD)
    p1, p2 = _parchear(gen, coord)
    params = {"area": "Comunicación", "grado": 3, "tema": "La noticia", "metodologia": "ERCA"}
    with p1, p2:
        eventos = _eventos(service.generar_sesion_stream_events(params, user, db))
    final = eventos[-1]
    assert final["done"] is True and "error" not in final
    assert user.stats.sesiones_generadas == 1 and user.stats.docs_generados == 1
    assert user.stats.areas_usadas == ["Comunicación"]
    assert user.stats.grados_usados == ["3"]


def test_hu37_tres_areas_y_grados_distintos_desbloquean_insignias(service, db, user, fake_agents):
    """Integración servicio -> gamificación: generar en 3 áreas/grados desbloquea
    'explorador' y 'multi_grado' con la lógica real de check_new_badges."""
    from src.api.gamification_logic import check_new_badges

    user.stats.mejoras_realizadas = 0
    user.stats.exportaciones_docx = 0
    user.stats.exportaciones_pdf = 0
    user.stats.badges_desbloqueados = []
    user.stats.dias_uso = []

    casos = [("Matemática", 1), ("Comunicación", 2), ("Ciencia y Tecnología", 3)]
    for area, grado in casos:
        gen, coord = fake_agents(SESION_MD)
        p1, p2 = _parchear(gen, coord)
        with p1, p2:
            list(service.generar_sesion_stream_events(
                {"area": area, "grado": grado, "tema": "Tema", "metodologia": "ERCA"}, user, db))

    nuevos = check_new_badges(user.stats)
    assert "explorador" in nuevos and "multi_grado" in nuevos


def test_hu37_repetir_area_y_grado_no_desbloquea_insignias(service, db, user, fake_agents):
    from src.api.gamification_logic import check_new_badges

    user.stats.mejoras_realizadas = 0
    user.stats.exportaciones_docx = 0
    user.stats.exportaciones_pdf = 0
    user.stats.badges_desbloqueados = []
    user.stats.dias_uso = []
    for _ in range(3):
        gen, coord = fake_agents(SESION_MD)
        p1, p2 = _parchear(gen, coord)
        with p1, p2:
            list(service.generar_sesion_stream_events(
                {"area": "Matemática", "grado": 1, "tema": "Tema"}, user, db))
    nuevos = check_new_badges(user.stats)
    assert "explorador" not in nuevos and "multi_grado" not in nuevos
    assert user.stats.areas_usadas == ["Matemática"]


def test_hu45_endpoint_unidad_responde_422_con_mas_de_2_competencias():
    """Integración ruta -> servicio: el límite se valida antes de abrir el stream."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.api.database import get_db
    from src.api.routes import generation
    from src.api.routes.auth import get_current_user

    app = FastAPI()
    app.include_router(generation.router)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u", stats=None)

    r = TestClient(app).post(
        "/generate/unidad/stream",
        json={"area": "Matemática", "grado": 1, "competencias": ["A", "B", "C"]},
    )
    assert r.status_code == 422
    assert "Máximo 2" in r.json()["detail"]


@pytest.mark.parametrize("tipo,params", [
    ("unidad", {"area": "Matemática", "grado": "2°", "competencias": ["A"]}),
    ("sesion", {"area": "Comunicación", "grado": "3°", "tema": "T", "metodologia": "ERCA"}),
])
def test_hu24_el_documento_guarda_area_y_grado(service, db, user, fake_agents, tipo, params):
    """El filtro del Dashboard depende de que el documento lleve su área y grado."""
    gen, coord = fake_agents(UNIDAD_MD if tipo == "unidad" else SESION_MD)
    p1, p2 = _parchear(gen, coord)
    with p1, p2:
        metodo = service.generar_unidad_stream_events if tipo == "unidad" else service.generar_sesion_stream_events
        list(metodo(params, user, db))
    guardado = db.add.call_args.args[0]
    assert guardado.area_curricular == params["area"] and guardado.grado == params["grado"]
