"""Recuperación estructurada del Programa Curricular: filtra por área/grado/competencia y se integra al RAG."""
import pytest

from src.agents.generator_agent import GeneratorAgent
from src.core.rag_service import RAGEducativoService
from src.core.retrieval_estructurado import CICLO_DE_GRADO, RecuperadorCurricular, grado_a_int


@pytest.fixture(scope="module")
def rec():
    return RecuperadorCurricular.desde_json()


@pytest.fixture
def servicio(monkeypatch):
    monkeypatch.delenv("RAG_ESTRUCTURADO", raising=False)
    return RAGEducativoService()


def _desempenos(chunks):
    return [c for c in chunks if c["tipo"] == "desempenos"]


# ----------------------------------------------------------------------------- utilidades
@pytest.mark.parametrize("entrada,esperado", [(3, 3), ("3", 3), ("3°", 3), ("3° de secundaria", 3), ("0", None),
                                              ("", None), (None, None), (7, None)])
def test_grado_a_int(entrada, esperado):
    assert grado_a_int(entrada) == esperado


def test_area_canonica_acepta_el_slug_que_envia_el_generador(rec):
    assert rec.area_canonica("ciencia_y_tecnología") == "Ciencia y Tecnología"
    assert rec.area_canonica("Educación para el Trabajo") == "Educación para el Trabajo"
    assert rec.area_canonica("area_inexistente") is None


# ----------------------------------------------------------------------------- filtrado
@pytest.mark.parametrize("grado", [1, 2, 3, 4, 5])
def test_nunca_devuelve_desempenos_de_otro_grado_ni_otra_area(rec, grado):
    for area in ("Matemática", "Comunicación", "Ciencia y Tecnología"):
        res = rec.recuperar("proyecto del bimestre", grado, area, k=10)
        assert _desempenos(res), (area, grado)
        assert all(c["grado"] == grado for c in _desempenos(res))
        assert all(c["area"] in (None, area) for c in res)
        assert all(c["ciclo"] in (None, CICLO_DE_GRADO[grado]) for c in res if c["tipo"] in ("competencia", "estandar"))


def test_el_tema_ordena_las_competencias_del_area(rec):
    res = rec.recuperar("método científico, hipótesis y experimentos", 2, "Ciencia y Tecnología", m=1, con_resto=False)
    assert res[0]["tipo"] == "desempenos" and res[0]["competencia"].startswith("Indaga mediante")


def test_los_desempenos_se_devuelven_aunque_el_tema_no_comparta_palabras(rec):
    res = rec.recuperar("xyzzy qwerty", 3, "Matemática", m=2, con_resto=False)
    assert len(_desempenos(res)) == 2 and all(c["area"] == "Matemática" for c in _desempenos(res))


def test_los_vecinos_tipados_se_anexan_despues_de_los_desempenos(rec):
    res = rec.recuperar("energía", 3, "Ciencia y Tecnología", m=2, con_resto=False)
    tipos = [c["tipo"] for c in res]
    assert tipos[:2] == ["desempenos", "desempenos"]
    assert set(tipos[2:]) <= {"competencia", "estandar"} and tipos[2:]


def test_area_desconocida_no_inventa_contexto_de_areas_ajenas(rec):
    res = rec.recuperar("lo que sea", 3, "area_inexistente", k=10)
    assert _desempenos(res) == []
    assert all(c.get("area") is None for c in res)       # solo narrativa, nunca capacidades/estandares de un area cualquiera
    assert rec.recuperar("x", 3, None, k=5, con_resto=False) == []


@pytest.mark.parametrize("grado", ["abc", 0, 6, None, ""])
def test_grado_invalido_no_mezcla_grados(rec, grado):
    assert rec.recuperar("tema", grado, "Matemática", k=10) == []
    assert rec.recuperar("tema", grado, "Matemática", competencias=["Resuelve problemas de cantidad"]) == []


def test_servicio_con_grado_o_area_invalidos_cae_al_contexto_complementario(servicio):
    for grado, area in (("abc", "matemática"), (0, "matemática"), (3, "astrología")):
        res = servicio.buscar_contexto_curricular("programación curricular", grado, area)
        assert res["estructurados"] == 0, (grado, area)


# ----------------------------------------------------------------------------- competencia elegida
def test_competencia_elegida_es_busqueda_exacta(rec):
    res = rec.recuperar("cualquier tema", 4, "Comunicación", competencias=["Escribe diversos tipos de textos en su lengua materna"],
                        con_resto=False)
    assert res[0]["tipo"] == "desempenos"
    assert res[0]["competencia"].startswith("Escribe diversos tipos de textos en lengua materna") and res[0]["grado"] == 4
    assert len(_desempenos(res)) == 1


def test_varias_competencias_conservan_el_orden_pedido(rec):
    pedidas = ["Resuelve problemas de cantidad", "Resuelve problemas de gestión de datos e incertidumbre"]
    res = rec.recuperar("x", 2, "Matemática", competencias=pedidas, con_resto=False)
    assert [c["competencia"] for c in _desempenos(res)] == pedidas


def test_construye_su_identidad_se_desambigua_por_area(rec):
    dpcc = rec.competencias_canonicas(["Construye su identidad"], "Desarrollo Personal, Ciudadanía y Cívica")
    assert dpcc == ["Construye su identidad"]
    rel = rec.competencias_canonicas(["Construye su identidad como persona humana"], "Educación Religiosa")
    assert rel and rel[0].startswith("Construye su identidad como persona humana")


def test_viñetas_y_numeracion_del_texto_del_wizard_se_ignoran(rec):
    assert rec.competencias_canonicas(["- Resuelve problemas de cantidad"], "Matemática") == ["Resuelve problemas de cantidad"]
    assert rec.competencias_canonicas(["1) Resuelve problemas de cantidad"], "Matemática") == ["Resuelve problemas de cantidad"]


def test_competencia_que_no_existe_cae_al_ordenamiento_por_tema(rec):
    res = rec.recuperar("energía", 3, "Ciencia y Tecnología", competencias=["Competencia inventada que no existe en el CNEB"],
                        m=2, con_resto=False)
    assert len(_desempenos(res)) == 2


# ----------------------------------------------------------------------------- integración con el servicio
def test_servicio_se_construye_sin_credenciales_aws(servicio):
    assert servicio._bedrock_runtime is None and servicio._bedrock_agent is None


def test_servicio_pone_primero_los_desempenos_estructurados(servicio):
    res = servicio.buscar_contexto_curricular("programación curricular Matemática 2 grado secundaria ecuaciones lineales",
                                              2, "matemática")
    assert res["estructurados"] >= 1 and res["total_encontrados"] == len(res["documentos"]) <= 10
    primero = res["documentos"][0]
    assert primero["metadata"]["recuperacion"] == "estructurada"
    assert primero["metadata"]["tipo"] == "desempenos" and primero["metadata"]["grado"] == 2
    assert "Programa Curricular" in primero["fuente"] and "p." in primero["fuente"]
    assert len({d["contenido"] for d in res["documentos"]}) == len(res["documentos"])  # sin duplicados


def test_servicio_usa_la_competencia_elegida(servicio):
    res = servicio.buscar_contexto_curricular("tema", 5, "comunicación", competencia="Lee diversos tipos de textos escritos en su lengua materna")
    d0 = res["documentos"][0]["metadata"]
    assert (d0["tipo"], d0["grado"]) == ("desempenos", 5) and d0["competencia"].startswith("Lee diversos tipos")


def test_servicio_conserva_el_contexto_complementario(servicio):
    res = servicio.buscar_contexto_curricular("estructura de la secuencia didáctica inicio desarrollo cierre", 3, "matemática")
    assert any(d.get("metadata", {}).get("recuperacion") != "estructurada" for d in res["documentos"])
    assert res["estructurados"] <= RAGEducativoService.MAX_ESTRUCTURADOS


def test_interruptor_de_entorno_desactiva_la_recuperacion_estructurada(monkeypatch):
    monkeypatch.setenv("RAG_ESTRUCTURADO", "0")
    s = RAGEducativoService()
    res = s.buscar_contexto_curricular("programación curricular Matemática 2 grado", 2, "matemática")
    assert res["estructurados"] == 0
    assert all(d.get("metadata", {}).get("recuperacion") != "estructurada" for d in res["documentos"])


def test_si_la_recuperacion_estructurada_falla_el_servicio_sigue(servicio, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(servicio._recuperador, "recuperar", falla)
    # con contenido pedagógico en la consulta, el contexto complementario sigue llegando aunque falle la parte estructurada
    res = servicio.buscar_contexto_curricular("programación curricular Matemática 2 grado evaluación formativa", 2, "matemática")
    assert res["estructurados"] == 0 and res["documentos"]


# ----------------------------------------------------------------------------- integración con el generador
def test_el_generador_pasa_la_competencia_elegida_al_rag():
    capturado = {}

    class RagFalso:
        def buscar_contexto_curricular(self, **kw):
            capturado.update(kw)
            return {"documentos": [{"fuente": "F", "contenido": "C"}]}

    agente = GeneratorAgent()
    agente.rag_service = RagFalso()
    salida = agente._buscar_contexto_rag("Ciencia y Tecnología", 3, "energía", "Indaga mediante métodos científicos")
    assert capturado["competencia"] == "Indaga mediante métodos científicos"
    assert capturado["area"] == "ciencia_y_tecnología" and capturado["grado"] == 3
    assert "Documento 1 (F)" in salida
