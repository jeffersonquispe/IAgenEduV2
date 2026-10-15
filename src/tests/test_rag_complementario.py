"""Contexto complementario del RAG (orientaciones, metodologías, capacitación): búsqueda BM25 sin tildes ni stopwords."""
import pytest

from src.core.rag_service import RAGEducativoService


@pytest.fixture
def servicio(monkeypatch):
    monkeypatch.delenv("RAG_COMPLEMENTARIO_BM25", raising=False)
    monkeypatch.delenv("RAG_ESTRUCTURADO", raising=False)
    return RAGEducativoService()


def _complementario(servicio, query):
    return servicio._buscar_contexto_complementario(query, 3, "matemática")["documentos"]


@pytest.mark.parametrize("consulta,fragmento_esperado", [
    ("fases del aprendizaje basado en problemas ABP", "Sesión 5 - ABP - Fases"),
    ("gamificación mecánicas dinámicas y componentes en el aula", "Gamificación - Componentes"),
    ("diversificación curricular contextualizar a la realidad local", "Contextualización y diversificación"),
    ("características e intereses del adolescente", "Enfoque en el adolescente"),
    ("estructura de una sesión de Aula Invertida", "Aula Invertida"),
])
def test_consultas_libres_de_pedagogia_encuentran_su_seccion_en_el_top_3(servicio, consulta, fragmento_esperado):
    top3 = [d["fuente"] for d in _complementario(servicio, consulta)[:3]]
    assert any(fragmento_esperado in f for f in top3), top3


def test_no_distingue_tildes_ni_mayusculas(servicio):
    con = _complementario(servicio, "Evaluación formativa: retroalimentación")
    sin = _complementario(servicio, "evaluacion formativa retroalimentacion")
    assert [d["fuente"] for d in con] == [d["fuente"] for d in sin] and con


def test_formato_de_los_documentos(servicio):
    docs = _complementario(servicio, "planificar una unidad didáctica")
    assert 0 < len(docs) <= RAGEducativoService.MAX_DOCUMENTOS
    scores = [d["score"] for d in docs]
    assert scores == sorted(scores, reverse=True) and scores[0] == pytest.approx(1.0) and all(0 < s <= 1 for s in scores)
    for d in docs:
        assert d["contenido"].startswith("[") and d["fuente"] and "section" in d["metadata"]
    assert len({d["contenido"] for d in docs}) == len(docs)


def test_sin_palabras_en_comun_no_devuelve_nada(servicio):
    assert _complementario(servicio, "xyzzy qwerty") == []


def test_la_parte_estructurada_sigue_primero_y_el_complemento_despues(servicio):
    res = servicio.buscar_contexto_curricular("fases del aprendizaje basado en problemas ABP", 3, "matemática")
    marcas = [d["metadata"].get("recuperacion") == "estructurada" for d in res["documentos"]]
    assert marcas[0] and not marcas[-1]
    assert marcas == sorted(marcas, reverse=True)           # primero todos los estructurados
    assert any("ABP" in d["fuente"] for d in res["documentos"])


def test_el_interruptor_vuelve_al_puntaje_por_palabras_clave_anterior(monkeypatch):
    monkeypatch.setenv("RAG_COMPLEMENTARIO_BM25", "0")
    s = RAGEducativoService()
    assert s._indice_complementario is None
    docs = s._buscar_contexto_complementario("planificar una unidad didáctica", 3, "matemática")["documentos"]
    assert docs and all({"contenido", "fuente", "score"} <= set(d) for d in docs)


def test_si_falta_el_indice_se_usa_el_puntaje_anterior(servicio):
    servicio._indice_complementario = None
    assert servicio._buscar_contexto_complementario("planificar una unidad didáctica", 3, "matemática")["documentos"]
    assert servicio._buscar_complementario_bm25("lo que sea") == []


# ----------------------------------------------------------------------------- lo que ya cubre el Programa Curricular
def _fuentes(docs):
    return [d["fuente"] for d in docs]


def test_con_el_corpus_estructurado_no_se_ofrecen_los_resumenes_que_este_reemplaza(servicio):
    for q in ("programación curricular Comunicación 4 grado secundaria textos argumentativos",
              "programación curricular Educación Física 1 grado secundaria coordinación y expresión corporal",
              "área de matemática y ciclos educativos del nivel secundaria"):
        fuentes = " | ".join(_fuentes(_complementario(servicio, q)))
        assert "5.5 Comunicación" not in fuentes and "5.8 Matemática" not in fuentes and "5.3 Educación Física" not in fuentes
        assert "Ciclos Educativos" not in fuentes


def test_sin_el_corpus_estructurado_los_resumenes_siguen_disponibles(monkeypatch):
    monkeypatch.setenv("RAG_ESTRUCTURADO", "0")
    s = RAGEducativoService()
    assert any("5.8 Matemática" in f for f in _fuentes(s._buscar_complementario_bm25("área de matemática")))


def test_sigue_ofreciendo_el_resto_del_curriculo_util_para_pedagogia(servicio):
    assert any("Evaluación Formativa" in f for f in _fuentes(_complementario(servicio, "evaluación formativa del aprendizaje")))
    assert any("Enfoques Transversales" in f for f in _fuentes(_complementario(servicio, "enfoques transversales")))


def test_se_conserva_lo_conceptual_que_los_datos_estructurados_no_explican(servicio):
    docs = _complementario(servicio, "diferencia entre estándares de aprendizaje y desempeños por grado")
    assert any("Estructura de Evaluación y Desempeños" in f for f in _fuentes(docs)[:3])


def test_el_prefijo_generico_de_la_consulta_no_trae_contexto_por_si_solo(servicio):
    assert _complementario(servicio, "programación curricular secundaria 3 grado") == []
    assert _complementario(servicio, "programación curricular Matemática 2 grado secundaria ecuaciones lineales") == []


def test_el_tema_pedagogico_dentro_de_la_consulta_del_pipeline_si_se_encuentra(servicio):
    q = "programación curricular Ciencia y Tecnología 3 grado secundaria indagación con aprendizaje basado en problemas ABP"
    assert any("ABP" in f for f in _fuentes(_complementario(servicio, q))[:3])
