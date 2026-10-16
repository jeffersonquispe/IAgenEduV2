"""HU-30 (criterio 3): la validación se actualiza tras editar o refinar una sección."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.agents.coordinator import PipelineMetrics
from src.api.routes import generation
from src.api.routes.auth import get_current_user
from src.api.services.generation_service import GenerationService
from src.validators.revalidacion import MAX_ERRORES_PREVIOS, MAX_LARGO_MENSAJE, revalidar_contenido
from src.validators.structure_validator import StructureValidator

ROOT = Path(__file__).resolve().parents[2]

MATRIZ = ("| Valor | Enfoques | Comportamientos observables | Instrumento |\n|---|---|---|---|\n"
          "| Fe | Bien común | Practica la oración. | Lista de cotejo |\n")
RUBRICA = ("| Criterio | C — Inicio | B — Proceso | A — Logrado | AD — Destacado |\n|---|---|---|---|---|\n"
           "| c1 | a | b | c | d |\n| c2 | a | b | c | d |\n")
SECUENCIA = ("Sesión 1: La noticia\nCriterio: Identifica ideas\nActividades: Leer\n\n"
             "Sesión 2: Fracciones equivalentes\nCriterio: Compara\nActividades: Practicar")

UNIDAD = {
    "situacion_significativa": "Una situación.", "propositos_de_aprendizaje": "Competencia A.",
    "valores_y_enfoques_transversales": MATRIZ, "secuencia_de_sesiones": SECUENCIA,
    "materiales_basicos": "Para el docente: proyector.", "rubrica_unidad": RUBRICA,
}
SESION = {
    "datos_informativos": "Colegio X", "reto": "¿Cómo?", "propositos_de_aprendizaje": "Competencia A",
    "secuencia_didactica": "INICIO 10 min. DESARROLLO 60 min. CIERRE 20 min.",
    "valores_y_enfoques_transversales": MATRIZ,
}


def _msgs(reporte, tipo=None):
    return [e.mensaje for e in reporte.errores if tipo is None or e.tipo == tipo]


def _previo(*entradas):
    return [{"tipo": t, "categoria": "ESTRUCTURA", "mensaje": m, "seccion": s} for t, m, s in entradas]


# --- Un documento completo no tiene errores ---

def test_unidad_completa_sin_errores():
    r = revalidar_contenido(UNIDAD, "unidad")
    assert r.errores == [] and r.puntaje == 100


def test_sesion_completa_sin_errores():
    assert revalidar_contenido(SESION, "sesion").errores == []


# --- Secciones obligatorias ---

@pytest.mark.parametrize("campo,seccion", [
    ("situacion_significativa", "SITUACIÓN SIGNIFICATIVA"), ("propositos_de_aprendizaje", "PROPÓSITOS"),
    ("valores_y_enfoques_transversales", "VALORES"), ("secuencia_de_sesiones", "SECUENCIA"),
    ("materiales_basicos", "MATERIALES"),
])
def test_unidad_con_una_seccion_vacia_es_critica(campo, seccion):
    r = revalidar_contenido({**UNIDAD, campo: "   "}, "unidad")
    assert f"Falta la sección requerida: {seccion}" in _msgs(r, "CRITICO")


@pytest.mark.parametrize("campo,seccion", [
    ("datos_informativos", "DATOS INFORMATIVOS"), ("reto", "RETO"),
    ("propositos_de_aprendizaje", "PROPÓSITOS"), ("secuencia_didactica", "SECUENCIA DIDÁCTICA"),
])
def test_sesion_con_una_seccion_ausente_es_critica(campo, seccion):
    sin = {k: v for k, v in SESION.items() if k != campo}
    assert f"Falta la sección requerida: {seccion}" in _msgs(revalidar_contenido(sin, "sesion"), "CRITICO")


def test_los_mensajes_coinciden_con_los_de_la_validacion_de_la_generacion():
    """Para que un error de la generación se 'resuelva' al corregir la sección, deben llamarse igual."""
    original = StructureValidator().validar_sesion_aprendizaje(
        "| ITEM | CONTENIDO |\n|---|---|\n| **DATOS INFORMATIVOS** | x |\n" + "relleno " * 20)
    ahora = revalidar_contenido({k: v for k, v in SESION.items() if k != "reto"}, "sesion")
    assert "Falta la sección requerida: RETO" in _msgs(original) and "Falta la sección requerida: RETO" in _msgs(ahora)


# --- Controles de contenido (Unidad) ---

def test_criterios_distintos_de_las_sesiones_generan_advertencia():
    sec = SECUENCIA.replace("Criterio: Compara\n", "")
    r = revalidar_contenido({**UNIDAD, "secuencia_de_sesiones": sec}, "unidad")
    adv = [e for e in r.errores if e.seccion == "SECUENCIA DE SESIONES" and "criterios" in e.mensaje]
    assert len(adv) == 1 and adv[0].tipo == "ADVERTENCIA" and "2 criterios" in adv[0].mensaje


def test_temas_repetidos():
    sec = SECUENCIA.replace("Fracciones equivalentes", "La noticia")
    r = revalidar_contenido({**UNIDAD, "secuencia_de_sesiones": sec}, "unidad")
    assert any("mismo tema" in m for m in _msgs(r, "ADVERTENCIA"))


def test_filas_de_rubrica_distintas_de_las_sesiones():
    r = revalidar_contenido({**UNIDAD, "rubrica_unidad": RUBRICA + "| c3 | a | b | c | d |\n"}, "unidad")
    assert any("3 filas" in m for m in _msgs(r, "ADVERTENCIA"))


def test_matriz_con_campos_sin_completar():
    sin_completar = MATRIZ.replace("Lista de cotejo", "[COMPLETAR: instrumento]")
    r = revalidar_contenido({**UNIDAD, "valores_y_enfoques_transversales": sin_completar}, "unidad")
    assert any("sin completar" in m for m in _msgs(r, "ADVERTENCIA"))


def test_html_residual():
    r = revalidar_contenido({**UNIDAD, "situacion_significativa": "Texto<br>con salto"}, "unidad")
    assert any("HTML" in m for m in _msgs(r, "ADVERTENCIA"))


def test_secuencia_didactica_sin_los_tres_momentos():
    r = revalidar_contenido({**SESION, "secuencia_didactica": "INICIO 10 min. DESARROLLO 60 min."}, "sesion")
    assert any("CIERRE" in m for m in _msgs(r, "ADVERTENCIA"))


# --- El escenario de la historia: refinar corrige el problema y el aviso se actualiza ---

def test_corregir_una_seccion_limpia_el_error_critico_de_la_generacion():
    # Texto de la generación al que solo le falta el RETO (tiene las demás secciones obligatorias).
    raw_sin_reto = ("| ITEM | CONTENIDO |\n|---|---|\n| **DATOS INFORMATIVOS** | Colegio X |\n"
                    "| **SITUACIÓN SIGNIFICATIVA** | Una situación. |\n"
                    "| **PROPÓSITOS DE APRENDIZAJE** | A |\n| **SECUENCIA DIDÁCTICA** | INICIO DESARROLLO CIERRE |\n"
                    "| **MATERIALES Y RECURSOS** | Pizarra |\n")
    m = PipelineMetrics()
    m.aplicar_reporte(StructureValidator().validar_sesion_aprendizaje(raw_sin_reto))
    assert m.errores_criticos >= 1 and m.resumen_validacion()["es_valido"] is False        # estado inicial

    sin_reto = {k: v for k, v in SESION.items() if k != "reto"}
    # el docente aún no escribe el reto: sigue en rojo
    assert revalidar_contenido(sin_reto, "sesion", m.detalle_validacion).tiene_errores_criticos
    # lo escribe (a mano o con el asistente de IA): el error desaparece
    despues = revalidar_contenido(SESION, "sesion", m.detalle_validacion)
    assert not despues.tiene_errores_criticos and "Falta la sección requerida: RETO" not in _msgs(despues)


def test_vaciar_una_seccion_vuelve_a_marcar_el_error():
    r1 = revalidar_contenido({**UNIDAD, "materiales_basicos": ""}, "unidad")
    r2 = revalidar_contenido(UNIDAD, "unidad", [vars(e) for e in r1.errores])
    assert not r2.tiene_errores_criticos                                   # lo arregló
    r3 = revalidar_contenido({**UNIDAD, "materiales_basicos": ""}, "unidad", [vars(e) for e in r2.errores])
    assert r3.tiene_errores_criticos                                       # lo volvió a romper


# --- Lo que no se puede reevaluar se conserva ---

def test_se_conservan_los_errores_que_no_se_pueden_recalcular_desde_las_secciones():
    previo = _previo(
        ("CRITICO", "Falta la sección requerida: EVIDENCIAS", "EVIDENCIAS"),
        ("ADVERTENCIA", "Calidad pedagógica baja según el revisor", "CONTENIDO"),
        ("CRITICO", "Falta la sección requerida: MATERIALES", "MATERIALES"),
    )
    r = revalidar_contenido(UNIDAD, "unidad", previo)
    msgs = _msgs(r)
    assert "Falta la sección requerida: EVIDENCIAS" in msgs and "Calidad pedagógica baja según el revisor" in msgs
    assert "Falta la sección requerida: MATERIALES" not in msgs             # ese sí se recalculó
    assert r.tiene_errores_criticos                                          # EVIDENCIAS sigue pendiente


def test_el_html_ya_corregido_desaparece_pero_otros_avisos_de_formato_se_conservan():
    previo = _previo(
        ("ADVERTENCIA", "Se encontraron 2 etiquetas HTML residuales", ""),
        ("ADVERTENCIA", "Columnas invertidas: CONTENIDO | ITEM", ""),
    )
    msgs = _msgs(revalidar_contenido(UNIDAD, "unidad", previo))
    assert not any("HTML" in m for m in msgs) and any("Columnas invertidas" in m for m in msgs)


def test_es_idempotente_y_no_duplica_errores():
    previo = _previo(("CRITICO", "Falta la sección requerida: EVIDENCIAS", "EVIDENCIAS"))
    una = revalidar_contenido({**UNIDAD, "reto": ""}, "unidad", previo)
    dos = revalidar_contenido({**UNIDAD, "reto": ""}, "unidad", [vars(e) for e in una.errores])
    assert _msgs(una) == _msgs(dos) and una.puntaje == dos.puntaje
    repetido = revalidar_contenido(UNIDAD, "unidad", previo + previo)
    assert _msgs(repetido).count("Falta la sección requerida: EVIDENCIAS") == 1


def test_un_detalle_previo_malformado_no_rompe_la_revalidacion():
    basura = [None, "texto", 7, {}, {"tipo": "INFO", "mensaje": "x"}, {"tipo": "CRITICO"},
              {"tipo": "CRITICO", "mensaje": "   "}, {"tipo": "CRITICO", "mensaje": "Válido", "seccion": "OTRA"}]
    assert _msgs(revalidar_contenido(UNIDAD, "unidad", basura)) == ["Válido"]


def test_el_detalle_previo_tiene_limites():
    muchos = [{"tipo": "ADVERTENCIA", "mensaje": f"aviso {i}", "seccion": "X"} for i in range(MAX_ERRORES_PREVIOS + 50)]
    assert len(revalidar_contenido(UNIDAD, "unidad", muchos).errores) == MAX_ERRORES_PREVIOS
    largo = [{"tipo": "ADVERTENCIA", "mensaje": "m" * 5000, "seccion": "X"}]
    assert len(revalidar_contenido(UNIDAD, "unidad", largo).errores[0].mensaje) == MAX_LARGO_MENSAJE


def test_tipo_no_soportado():
    with pytest.raises(ValueError):
        revalidar_contenido(UNIDAD, "examen")


def test_ignora_valores_que_no_son_texto():
    r = revalidar_contenido({**UNIDAD, "materiales_basicos": None, "extra": 5}, "unidad")
    assert "Falta la sección requerida: MATERIALES" in _msgs(r)


# --- Servicio ---

def test_el_servicio_devuelve_el_resumen_con_la_forma_de_la_generacion():
    r = GenerationService.revalidar({"tipo": "unidad", "content": UNIDAD, "detalle_previo": []})
    assert set(r) == {"es_valido", "puntaje_validacion", "errores_criticos", "errores_advertencia",
                      "detalle", "revalidado"}
    assert r["es_valido"] is True and r["puntaje_validacion"] == 100 and r["revalidado"] is True


def test_el_servicio_marca_invalido_si_queda_un_critico():
    r = GenerationService.revalidar({"tipo": "sesion", "content": {k: v for k, v in SESION.items() if k != "reto"}})
    assert r["es_valido"] is False and r["errores_criticos"] == 1 and r["detalle"][0]["seccion"] == "RETO"


@pytest.mark.parametrize("params", [
    {}, {"tipo": "examen", "content": {}}, {"tipo": "unidad"}, {"tipo": "unidad", "content": "texto"},
    {"tipo": "unidad", "content": {"a": 5}}, {"tipo": "unidad", "content": {"a": "x" * 300_001}},
    {"tipo": "unidad", "content": UNIDAD, "detalle_previo": "no es lista"},
])
def test_el_servicio_rechaza_entradas_invalidas(params):
    with pytest.raises(ValueError):
        GenerationService.revalidar(params)


# --- Endpoint ---

@pytest.fixture
def cliente():
    app = FastAPI()
    app.include_router(generation.router)
    app.dependency_overrides[get_current_user] = lambda: object()
    return TestClient(app)


def test_el_endpoint_revalida(cliente):
    r = cliente.post("/generate/validar", json={"tipo": "unidad", "content": UNIDAD, "detalle_previo": []})
    assert r.status_code == 200 and r.json()["es_valido"] is True and r.json()["revalidado"] is True


def test_el_endpoint_responde_422_con_entradas_invalidas(cliente):
    assert cliente.post("/generate/validar", json={"tipo": "x", "content": {}}).status_code == 422
    assert cliente.post("/generate/validar", json={"tipo": "unidad", "content": {"a": 1}}).status_code == 422


def test_el_endpoint_requiere_sesion():
    app = FastAPI()
    app.include_router(generation.router)
    assert TestClient(app).post("/generate/validar", json={}).status_code in (401, 403)


# --- Frontend (verificación estática) ---

def test_el_editor_revalida_con_espera_y_descarta_respuestas_viejas():
    src = (ROOT / "frontend/src/pages/Editor.jsx").read_text(encoding="utf-8")
    assert "api.post('/generate/validar'" in src and "detalle_previo:" in src
    assert "}, 1200)" in src and "clearTimeout(temporizador)" in src                  # espera a que deje de escribir
    assert "id !== peticionValidacion.current" in src                                  # respuestas fuera de orden
    assert "ultimaFirmaValidada" in src and "[firmaContenido]" in src                  # no se dispara en bucle


def test_el_aviso_ya_no_dice_que_editar_no_actualiza_la_validacion():
    src = (ROOT / "frontend/src/pages/Editor.jsx").read_text(encoding="utf-8")
    assert "no la vuelve a ejecutar" not in src
    assert "Actualizado con tus cambios" in src
