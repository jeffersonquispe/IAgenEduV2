"""HU-36: valores y enfoques institucionales configurables (default genérico, perfil y presets)."""
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.agents.generator_agent import GeneratorAgent
from src.api.database import get_db
from src.api.routes import institution
from src.api.routes.auth import get_current_user
from src.core import valores_institucionales as vi

ROOT = Path(__file__).resolve().parents[2]

# Términos confesionales: no deben aparecer en lo que se usa por defecto.
CONFESIONAL = re.compile(r"jesucristo|cristo|caridad|miseric|\bfe\b|dios|oraci[oó]n|sacrament|evangeli", re.IGNORECASE)


def _perfil(valores=None, enfoques=None):
    return SimpleNamespace(valores_institucionales=valores, enfoques_transversales=enfoques)


# --- El default es neutral ---

def test_el_default_de_valores_no_tiene_contenido_confesional():
    for valor in vi.resolver_valores_institucionales(None):
        assert not CONFESIONAL.search(valor), valor


def test_el_default_de_enfoques_no_tiene_contenido_confesional():
    for enfoque in vi.resolver_enfoques_transversales(None):
        assert not CONFESIONAL.search(enfoque), enfoque


@pytest.mark.parametrize("perfil", [None, _perfil(), _perfil([], []), _perfil(None, None)])
def test_sin_valores_propios_se_usa_el_default_del_cneb(perfil):
    assert vi.resolver_valores_institucionales(perfil) == vi.VALORES_CNEB_DEFAULT
    assert vi.resolver_enfoques_transversales(perfil) == vi.ENFOQUES_TRANSVERSALES_CNEB_DEFAULT


def test_el_preset_catolico_no_es_el_default():
    assert vi.resolver_valores_institucionales(None) != vi.VALORES_CATOLICO_PRESET
    assert any(CONFESIONAL.search(v) for v in vi.VALORES_CATOLICO_PRESET)       # sí es confesional


def test_las_constantes_hardcodeadas_antiguas_ya_no_existen():
    codigo = (ROOT / "src/agents/generator_agent.py").read_text(encoding="utf-8")
    assert "VALORES_PERMITIDOS =" not in codigo and "ENFOQUES_TRANSVERSALES_PERMITIDOS =" not in codigo


# --- El perfil manda ---

def test_los_valores_del_perfil_reemplazan_al_default():
    p = _perfil(["Fe", "Amor"], ["Enfoque propio"])
    assert vi.resolver_valores_institucionales(p) == ["Fe", "Amor"]
    assert vi.resolver_enfoques_transversales(p) == ["Enfoque propio"]


def test_una_lista_en_blanco_o_con_basura_no_cuenta_como_valores_propios():
    assert vi.resolver_valores_institucionales(_perfil(["", "   "])) == vi.VALORES_CNEB_DEFAULT
    assert vi.resolver_valores_institucionales(_perfil([None, 3, {}])) == vi.VALORES_CNEB_DEFAULT
    assert vi.resolver_valores_institucionales(_perfil("Fe, Amor")) == vi.VALORES_CNEB_DEFAULT   # no es una lista


def test_los_valores_propios_se_limpian():
    assert vi.resolver_valores_institucionales(_perfil(["  Fe ", "", "Amor", 7])) == ["Fe", "Amor"]


def test_el_resolver_devuelve_copias_y_no_la_constante():
    valores = vi.resolver_valores_institucionales(None)
    valores.append("intruso")
    assert "intruso" not in vi.VALORES_CNEB_DEFAULT and "intruso" not in vi.resolver_valores_institucionales(None)
    enfoques = vi.resolver_enfoques_transversales(None)
    enfoques.clear()
    assert vi.ENFOQUES_TRANSVERSALES_CNEB_DEFAULT


# --- Llega al prompt ---

@pytest.fixture(autouse=True)
def sin_rag():
    with patch.object(GeneratorAgent, "_buscar_contexto_rag", return_value=""):
        yield


def _prompt(perfil):
    return GeneratorAgent().construir_prompt_unidad(
        area_curricular="Arte", grado=1, competencia_referencia="COMPETENCIA 1", temas="t",
        num_sesiones=3, producto_final="p", institution_profile=perfil)


def _linea_de_valores(prompt):
    """Las líneas del prompt que listan los valores y enfoques (no el resto del texto,
    donde palabras como 'oraciones' son gramática y no devoción)."""
    return "\n".join(l for l in prompt.split("\n") if l.startswith("Valores de la institución:"))


def test_el_prompt_por_defecto_no_trae_valores_confesionales():
    linea = _linea_de_valores(_prompt(None))
    assert "Respeto" in linea and not CONFESIONAL.search(linea)


def test_el_prompt_con_el_preset_catolico_si_los_trae_porque_el_docente_lo_eligio():
    assert "Encuentro personal con Jesucristo" in _prompt(_perfil(list(vi.VALORES_CATOLICO_PRESET)))


# --- Presets ---

def test_los_presets_disponibles():
    presets = vi.listar_presets()
    assert [p["id"] for p in presets] == ["cneb", "catolico"]
    for p in presets:
        assert set(p) == {"id", "nombre", "descripcion", "valores"} and p["valores"]


def test_el_preset_confesional_lo_advierte_en_su_descripcion():
    catolico = next(p for p in vi.listar_presets() if p["id"] == "catolico")
    assert "confesional" in catolico["descripcion"].lower()


def test_ningun_valor_de_un_preset_lleva_comas():
    """La pantalla separa los valores por coma: una coma dentro de un valor lo partiría en dos."""
    for p in vi.listar_presets():
        assert all("," not in v for v in p["valores"]), p["id"]


def test_listar_presets_devuelve_copias():
    vi.listar_presets()[0]["valores"].append("intruso")
    assert "intruso" not in vi.VALORES_CNEB_DEFAULT


# --- Endpoint y pantalla ---

def test_el_endpoint_de_presets_requiere_sesion_y_devuelve_los_presets():
    app = FastAPI()
    app.include_router(institution.router)
    assert TestClient(app).get("/institucion/presets-valores").status_code in (401, 403)

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u")
    app.dependency_overrides[get_db] = lambda: None            # no debe usarse
    r = TestClient(app).get("/institucion/presets-valores")
    assert r.status_code == 200 and [p["id"] for p in r.json()] == ["cneb", "catolico"]
    assert "Encuentro personal con Jesucristo" in r.json()[1]["valores"]


def test_la_pantalla_ofrece_los_presets_y_solo_rellena_el_campo():
    src = (ROOT / "frontend/src/pages/Institucion.jsx").read_text(encoding="utf-8")
    assert "/institucion/presets-valores" in src
    assert "valores_institucionales: p.valores.join(', ')" in src          # rellena, no guarda
    assert "api.put" not in src[src.index("presets.map"):src.index("presets.map") + 700]


def test_la_documentacion_ya_no_afirma_que_el_sistema_no_es_neutral():
    doc = (ROOT / "docs/REGLAS_DE_NEGOCIO.md").read_text(encoding="utf-8")
    assert "hoy el sistema no es neutral" not in doc and "No existe ningún perfil institucional" not in doc
    assert "VALORES_CNEB_DEFAULT" in doc and "presets-valores" in doc
