"""HU-42: matriz axiológica estructurada (Valor | Enfoques | Comportamientos | Instrumento)."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.agents.generator_agent import GeneratorAgent
from src.api import models
from src.api.services.content_parsers import SesionContentParser, UnidadContentParser
from src.api.services.generation_service import GenerationService
from src.core.matriz_axiologica import (
    MAX_FILAS_MATRIZ, construir_filas_matriz, contar_filas_matriz, extraer_matriz,
    instrucciones_matriz, tiene_matriz,
)
from src.core.valores_institucionales import resolver_enfoques_transversales
from src.validators.structure_validator import StructureValidator

ROOT = Path(__file__).resolve().parents[2]

MATRIZ = (
    "| Valor | Enfoques transversales | Comportamientos observables | Instrumento |\n"
    "|---|---|---|---|\n"
    "| Fe | Enfoque de orientación al bien común | Practica la oración personal. | Lista de cotejo |\n"
    "| Amor | Enfoque de derechos | Llama por su nombre a los compañeros. | Escala de valoración |\n"
)


def _perfil_salesiano():
    crudo = json.loads((ROOT / "data/perfiles/salesiano_cusco.json").read_text(encoding="utf-8"))
    return SimpleNamespace(**{k: v for k, v in crudo.items() if not k.startswith("_")})


@pytest.fixture(autouse=True)
def sin_rag():
    with patch.object(GeneratorAgent, "_buscar_contexto_rag", return_value=""):
        yield


# --- Filas de la matriz ---

def test_las_filas_del_perfil_se_conservan_tal_cual():
    filas = construir_filas_matriz(_perfil_salesiano())
    assert [f["valor"] for f in filas] == ["Fe", "Amor", "Ciudadanía"]
    assert filas[0]["comportamiento"].startswith("Practica la oración personal")
    assert filas[0]["enfoque"] == "" and filas[0]["instrumento"] == ""        # lo que falta lo completa el modelo


def test_sin_matriz_propia_se_empareja_valores_con_enfoques_del_cneb():
    filas = construir_filas_matriz(None)
    assert 1 <= len(filas) <= MAX_FILAS_MATRIZ
    enfoques = resolver_enfoques_transversales(None)
    assert all(f["enfoque"] in enfoques for f in filas)
    assert all(f["valor"] and not f["comportamiento"] and not f["instrumento"] for f in filas)


def test_con_valores_propios_pero_sin_matriz_se_usan_esos_valores():
    perfil = SimpleNamespace(matriz_axiologica=None, valores_institucionales=["Fe", "Amor"],
                             enfoques_transversales=["E1"])
    assert construir_filas_matriz(perfil) == [
        {"valor": "Fe", "enfoque": "E1", "comportamiento": "", "instrumento": ""},
        {"valor": "Amor", "enfoque": "E1", "comportamiento": "", "instrumento": ""},
    ]


def test_se_limita_el_numero_de_filas():
    perfil = SimpleNamespace(matriz_axiologica=[{"valor": f"V{i}"} for i in range(12)])
    assert len(construir_filas_matriz(perfil)) == MAX_FILAS_MATRIZ


def test_filas_invalidas_se_descartan_y_el_texto_se_sanea():
    perfil = SimpleNamespace(matriz_axiologica=[
        "no es un dict", {"valor": ""}, {"enfoque": "sin valor"},
        {"valor": "Fe | X", "comportamiento_observable": "línea 1\nlínea 2 | otra"},
    ])
    filas = construir_filas_matriz(perfil)
    assert len(filas) == 1
    assert filas[0]["valor"] == "Fe / X"
    assert filas[0]["comportamiento"] == "línea 1 línea 2 / otra"


def test_si_todas_las_filas_del_perfil_son_invalidas_cae_al_emparejamiento_generico():
    perfil = SimpleNamespace(matriz_axiologica=[{"valor": ""}], valores_institucionales=["Fe"],
                             enfoques_transversales=None)
    assert [f["valor"] for f in construir_filas_matriz(perfil)] == ["Fe"]


# --- Instrucciones para el prompt ---

def test_instrucciones_marcan_lo_que_el_modelo_debe_completar():
    texto = instrucciones_matriz(construir_filas_matriz(_perfil_salesiano()), ["Enfoque A", "Enfoque B"])
    assert "1. Valor: Fe" in texto and "Practica la oración personal" in texto   # dato del perfil
    assert "Enfoque: [COMPLETAR" in texto and "Instrumento: [COMPLETAR" in texto  # lo que falta
    assert "Enfoque A; Enfoque B" in texto
    assert "EXACTAMENTE estas filas" in texto


def test_instrucciones_de_sesion_piden_una_o_dos_filas():
    texto = instrucciones_matriz(construir_filas_matriz(None), [], por_sesion=True)
    assert "1 o 2 filas" in texto and "EXACTAMENTE estas filas" not in texto


def test_sin_filas_no_hay_instrucciones():
    assert instrucciones_matriz([], ["E"]) == ""


# --- Extracción ---

CONTENIDO = (
    "| ITEM | CONTENIDO |\n|---|---|\n| **EVIDENCIAS DE APRENDIZAJE** | algo |\n\n"
    + MATRIZ +
    "\n| Criterio | C — Inicio | B — Proceso | A — Logrado | AD — Destacado |\n|---|---|---|---|---|\n| c1 | a | b | c | d |\n"
)


def test_extrae_solo_la_tabla_de_la_matriz():
    tabla = extraer_matriz(CONTENIDO)
    assert tabla.startswith("| Valor |") and "Escala de valoración" in tabla
    assert "Criterio" not in tabla and "EVIDENCIAS" not in tabla
    assert contar_filas_matriz(CONTENIDO) == 2 and tiene_matriz(CONTENIDO)


def test_sin_matriz():
    assert extraer_matriz("| ITEM | CONTENIDO |\n|---|---|\n| a | b |") == ""
    assert extraer_matriz("") == "" and contar_filas_matriz("") == 0 and not tiene_matriz("texto")


def test_una_tabla_con_valor_pero_sin_comportamientos_no_es_la_matriz():
    assert extraer_matriz("| Valor | Otra cosa |\n|---|---|\n| a | b |") == ""


def test_encabezado_con_negritas_tambien_se_reconoce():
    assert tiene_matriz("| **Valor** | Enfoques | Comportamientos observables | Instrumento |\n|---|---|---|---|\n| a | b | c | d |")


# --- Prompts reales ---

def _unidad(perfil):
    return GeneratorAgent().construir_prompt_unidad(
        area_curricular="Comunicación", grado=3, competencia_referencia="COMPETENCIA 1. Se comunica",
        temas="La noticia", num_sesiones=4, producto_final="Un periódico mural", institution_profile=perfil)


def _sesion(perfil):
    return GeneratorAgent().construir_prompt_sesion(
        titulo_unidad="U", titulo_sesion="S", nivel="Secundaria", grado="3", seccion="A",
        duracion="90 min", tema="T", metodologia="ERCA", institution_profile=perfil)


def test_prompt_de_unidad_pide_la_matriz_como_tabla_con_las_filas_del_perfil():
    p = _unidad(_perfil_salesiano())
    assert "| Valor | Enfoques transversales | Comportamientos observables | Instrumento |" in p
    assert "1. Valor: Fe" in p and "2. Valor: Amor" in p and "3. Valor: Ciudadanía" in p
    assert "| **VALORES Y ENFOQUES TRANSVERSALES** |" not in p        # ya no es una celda de texto libre
    assert "{contexto_matriz}" not in p
    assert "SÉPTIMA TABLA — Rúbrica" in p


def test_prompt_de_unidad_sin_perfil_arma_las_filas_genericas():
    p = _unidad(None)
    assert "| Valor | Enfoques transversales | Comportamientos observables | Instrumento |" in p
    assert "1. Valor: " in p and "[COMPLETAR" in p


def test_prompt_de_sesion_incluye_la_matriz_y_ya_no_la_fila_de_enfoque_transversal():
    p = _sesion(_perfil_salesiano())
    assert "| Valor | Enfoques transversales | Comportamientos observables | Instrumento |" in p
    assert "1 o 2 filas" in p and "{contexto_matriz}" not in p
    assert "| **ENFOQUE TRANSVERSAL** |" not in p
    assert "TERCERA TABLA — Rúbrica" in p


# --- Parsers ---

UNIDAD_CON_MATRIZ = (
    "| ITEM | CONTENIDO |\n|---|---|\n"
    "| **II. SITUACIÓN SIGNIFICATIVA** | Una situación significativa suficientemente larga. |\n"
    "| **III. PROPÓSITOS DE APRENDIZAJE** | Competencias: A. Criterios de evaluación: x. |\n\n" + MATRIZ
)


def test_parser_de_unidad_guarda_la_matriz_como_tabla():
    doc = UnidadContentParser().parsear(UNIDAD_CON_MATRIZ, area="Comunicación")
    assert doc["valores_y_enfoques_transversales"].startswith("| Valor |")
    assert "Lista de cotejo" in doc["valores_y_enfoques_transversales"]


def test_parser_de_unidad_conserva_el_formato_anterior_si_no_hay_matriz():
    antiguo = (
        "| ITEM | CONTENIDO |\n|---|---|\n"
        "| **VALORES Y ENFOQUES TRANSVERSALES** | Valores: Respeto. Enfoques: Ambiental. |\n"
    )
    doc = UnidadContentParser().parsear(antiguo, area="Arte")
    assert doc["valores_y_enfoques_transversales"].startswith("Valores:")


SESION_CON_MATRIZ = (
    "| ITEM | CONTENIDO |\n|---|---|\n| **DATOS INFORMATIVOS** | Colegio X |\n| **RETO** | ¿Cómo? |\n"
    "| **PROPÓSITOS DE APRENDIZAJE** | Competencia A |\n| **SECUENCIA DIDÁCTICA** | INICIO DESARROLLO CIERRE |\n\n"
    + MATRIZ
)


def test_parser_de_sesion_guarda_la_matriz_sin_contaminar_otras_secciones():
    doc = SesionContentParser().parsear(SESION_CON_MATRIZ, tema_sesion="T")
    assert doc["valores_y_enfoques_transversales"].startswith("| Valor |")
    for campo in ("datos_informativos", "propositos_de_aprendizaje", "secuencia_didactica"):
        assert "Practica la oración" not in doc[campo]


def test_parser_de_sesion_sin_matriz_no_agrega_la_clave():
    assert "valores_y_enfoques_transversales" not in SesionContentParser().parsear(
        SESION_CON_MATRIZ.replace(MATRIZ, ""), tema_sesion="T")


# --- Validador ---

def _unidad_valida(extra=""):
    otras = [s for s in StructureValidator.SECCIONES_UNIDAD if s != "VALORES"]
    filas = "".join(f"| **{s}** | contenido de prueba |\n" for s in otras)
    return "| ITEM | CONTENIDO |\n|---|---|\n" + filas + "\n" + extra


def _criticos(rep):
    return [e.seccion for e in rep.errores if e.tipo == "CRITICO"]


def test_la_matriz_cumple_la_seccion_de_valores():
    rep = StructureValidator().validar_unidad_didactica(_unidad_valida(MATRIZ))
    assert "VALORES" not in _criticos(rep)


def test_sin_matriz_ni_fila_de_valores_sigue_siendo_critico():
    rep = StructureValidator().validar_unidad_didactica(_unidad_valida())
    assert "VALORES" in _criticos(rep)


def test_el_formato_anterior_de_valores_sigue_siendo_valido():
    rep = StructureValidator().validar_unidad_didactica(
        _unidad_valida() + "| **VALORES Y ENFOQUES TRANSVERSALES** | Valores: Respeto. |\n")
    assert "VALORES" not in _criticos(rep)


def test_matriz_sin_filas_o_sin_completar_genera_advertencia():
    vacia = "| Valor | Enfoques | Comportamientos observables | Instrumento |\n|---|---|---|---|\n"
    sin_completar = vacia + "| Fe | [COMPLETAR: elige UNO] | algo | lista |\n"
    for contenido, texto in ((vacia, "no tiene filas"), (sin_completar, "sin completar")):
        rep = StructureValidator().validar_unidad_didactica(_unidad_valida(contenido))
        adv = [e for e in rep.errores if e.seccion == "MATRIZ AXIOLÓGICA"]
        assert len(adv) == 1 and adv[0].tipo == "ADVERTENCIA" and texto in adv[0].mensaje


def test_matriz_completa_no_genera_advertencia():
    rep = StructureValidator().validar_unidad_didactica(_unidad_valida(MATRIZ))
    assert not [e for e in rep.errores if e.seccion == "MATRIZ AXIOLÓGICA"]


# --- Flujo del servicio y exportación ---

def test_la_unidad_generada_guarda_la_matriz_y_el_pdf_la_incluye(tmp_path):
    from pypdf import PdfReader
    from src.core.pdf_generator import generar_pdf_unidad

    gen = MagicMock()
    gen.construir_prompt_unidad.return_value = "P"
    gen.bedrock.invocar_stream.return_value = iter([UNIDAD_CON_MATRIZ])
    coord = MagicMock()
    coord.validar_y_formatear_unidad.return_value = (UNIDAD_CON_MATRIZ, None)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    svc = GenerationService()
    svc._save_version = MagicMock()
    svc._save_pipeline_run = MagicMock()
    with patch("src.agents.generator_agent.GeneratorAgent", return_value=gen), \
         patch("src.agents.coordinator.get_coordinator", return_value=coord):
        eventos = [json.loads(l[6:]) for l in svc.generar_unidad_stream_events(
            {"area": "Comunicación", "grado": "3°", "competencias": ["A"]},
            SimpleNamespace(id="u", full_name=None, stats=None), db) if l.startswith("data: ")]
    final = eventos[-1]
    assert "error" not in final
    assert final["valores_y_enfoques_transversales"].startswith("| Valor |")

    salida = tmp_path / "u.pdf"
    generar_pdf_unidad({"titulo": "U", "valores_y_enfoques_transversales": final["valores_y_enfoques_transversales"]},
                       str(salida))
    texto = " ".join(p.extract_text() or "" for p in PdfReader(str(salida)).pages)
    assert "Escala de valoración" in texto and "Practica la oración personal" in texto


def test_el_editor_muestra_la_matriz_en_la_seccion_de_valores():
    src = (ROOT / "frontend/src/lib/documento.js").read_text(encoding="utf-8")
    assert "valores_y_enfoques_transversales: " in src
