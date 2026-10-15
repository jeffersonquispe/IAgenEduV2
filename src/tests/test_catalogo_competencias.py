"""El catálogo de competencias del wizard coincide con el Programa Curricular (fuente de verdad)."""
import re

import pytest

from src.core import competencias_curriculares as cat
from src.core.retrieval_estructurado import RecuperadorCurricular

AREAS_Y_CANTIDAD = {  # competencias propias de cada área (CNEB 2016), sin contar las 2 transversales
    "Desarrollo Personal, Ciudadanía y Cívica": 2, "Ciencias Sociales": 3, "Educación Física": 3, "Arte y Cultura": 2,
    "Comunicación": 3, "Castellano como Segunda Lengua": 3, "Inglés como Lengua Extranjera": 3, "Matemática": 4,
    "Ciencia y Tecnología": 3, "Educación para el Trabajo": 1, "Educación Religiosa": 2,
}


@pytest.fixture(scope="module")
def rec():
    return RecuperadorCurricular.desde_json()


def test_son_31_competencias_con_numero_unico_y_area_valida():
    comps = cat.COMPETENCIAS_CURRICULARES
    assert len(comps) == 31 and len({c["numero"] for c in comps}) == 31
    assert {c["area"] for c in comps} == set(cat.AREAS_CURRICULARES_SECUNDARIA) | {cat.AREA_TRANSVERSAL}


def test_todo_nombre_del_catalogo_se_resuelve_a_una_competencia_del_programa_de_su_area(rec):
    for c in cat.COMPETENCIAS_CURRICULARES:
        area_can = rec.area_canonica(c["area"]) or None
        res = rec.competencias_canonicas([c["nombre"]], area_can)
        assert res, f"no se resuelve: {c['nombre']}"
        assert rec._competencias[res[0]] == c["area"], (c["nombre"], res[0])


def test_cada_competencia_del_programa_esta_en_el_catalogo_exactamente_una_vez(rec):
    resueltas = [rec.competencias_canonicas([c["nombre"]], rec.area_canonica(c["area"]))[0] for c in cat.COMPETENCIAS_CURRICULARES]
    assert sorted(resueltas) == sorted(rec._competencias)


def test_formato_que_envia_el_wizard_se_resuelve_para_todas(rec):
    for c in cat.COMPETENCIAS_CURRICULARES:
        texto = f"COMPETENCIA {c['numero']}. {c['nombre']}"
        assert rec.competencias_canonicas([texto], rec.area_canonica(c["area"])), texto


@pytest.mark.parametrize("area,propias", AREAS_Y_CANTIDAD.items())
def test_cada_area_muestra_sus_competencias_mas_las_transversales(area, propias):
    comps = cat.obtener_competencias_por_area(area)
    areas = [c["area"] for c in comps]
    assert areas.count(area) == propias
    assert areas.count(cat.AREA_TRANSVERSAL) == 2 and len(comps) == propias + 2


def test_no_hay_capacidades_ni_nombres_de_otro_curriculo():
    nombres = " | ".join(c["nombre"] for c in cat.COMPETENCIAS_CURRICULARES)
    for capacidad in ("Se valora a sí mismo", "Autorregula sus emociones", "Vive su sexualidad", "Maneja conflictos"):
        assert capacidad not in nombres
    assert "Interpreta la realidad" not in nombres and "Conoce a Dios" not in nombres


def test_area_desconocida_o_vacia_devuelve_lista_vacia_y_los_alias_funcionan():
    assert cat.obtener_competencias_por_area("Astrología") == [] and cat.obtener_competencias_por_area("") == []
    assert cat.obtener_competencias_por_area("matematica") == cat.obtener_competencias_por_area("Matemática")
    assert cat.obtener_competencias_por_area("Tutoría")


def test_los_numeros_de_entradas_que_eran_capacidades_no_se_reutilizan():
    numeros = {c["numero"] for c in cat.COMPETENCIAS_CURRICULARES}
    assert not (numeros & set(range(22, 30)))


def test_la_lista_formateada_para_el_selector_mantiene_el_formato_del_wizard():
    for linea in cat.obtener_lista_competencias_formateada():
        assert re.match(r"^COMPETENCIA \d+\. \S", linea)


# --------------------------------------------------------------------- integración con la recuperación
def test_una_transversal_elegida_dentro_de_un_area_trae_sus_desempenos_y_vecinos(rec):
    res = rec.recuperar("x", 3, "Matemática", competencias=["COMPETENCIA 16. Se desenvuelve en entornos virtuales generados por las TIC"],
                        k=5, con_resto=False)
    assert res[0]["tipo"] == "desempenos" and res[0]["grado"] == 3 and "TIC" in res[0]["competencia"]
    assert len(res) > 1 and all("TIC" in c["competencia"] for c in res)


def test_elegir_una_competencia_de_otra_area_del_wizard_trae_la_competencia_correcta(rec):
    # antes: en Inglés solo existía una; ahora las tres, con desempeños propios del grado
    for n in (7, 37, 38):
        comp = next(c for c in cat.COMPETENCIAS_CURRICULARES if c["numero"] == n)
        res = rec.recuperar("x", 4, "Inglés como Lengua Extranjera", competencias=[f"COMPETENCIA {n}. {comp['nombre']}"],
                            k=1, con_resto=False)
        assert res[0]["tipo"] == "desempenos" and res[0]["grado"] == 4 and res[0]["area"] == "Inglés como Lengua Extranjera"
