"""El modelo de validación con IA: debe existir en AWS y poder cambiarse sin tocar código.

AWS retiró claude-3-haiku-20240307; la validación empezó a fallar con "end of its life" y el
validador, por diseño, devuelve un resultado neutro (APROBADO, 70) en lugar de propagar el error,
de modo que nadie lo notó. Estas pruebas evitan volver a fijar un modelo retirado.
"""
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.bedrock_client import BedrockClient

RAIZ = Path(__file__).resolve().parents[2]
MODELO_RETIRADO = "claude-3-haiku-20240307"


def test_el_modelo_de_validacion_por_defecto_no_es_el_retirado():
    assert MODELO_RETIRADO not in BedrockClient.CLAUDE_HAIKU


def test_el_modelo_de_validacion_es_un_perfil_de_inferencia_de_haiku():
    assert BedrockClient.CLAUDE_HAIKU.startswith("us.anthropic.claude-haiku")


def _modelo_en_otro_proceso(valor):
    """Importa el módulo en un proceso nuevo (la constante se lee al importar), con o sin la variable."""
    entorno = {k: v for k, v in os.environ.items() if k != "BEDROCK_VALIDATION_MODEL_ID"}
    if valor is not None:
        entorno["BEDROCK_VALIDATION_MODEL_ID"] = valor
    r = subprocess.run(
        [sys.executable, "-c", "from src.core.bedrock_client import BedrockClient; print(BedrockClient.CLAUDE_HAIKU)"],
        cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr[-300:]
    return r.stdout.strip().splitlines()[-1]


def test_se_puede_cambiar_por_variable_de_entorno():
    assert _modelo_en_otro_proceso("us.anthropic.claude-haiku-9-9") == "us.anthropic.claude-haiku-9-9"


def test_sin_la_variable_se_usa_el_valor_por_defecto():
    assert _modelo_en_otro_proceso(None) == "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_invocar_validacion_usa_ese_modelo_y_parametros_de_validacion():
    cliente = BedrockClient(max_reintentos=1)
    with patch.object(BedrockClient, "invocar", return_value="{}") as invocar:
        cliente.invocar_validacion("prompt", max_tokens=123)
    kwargs = invocar.call_args.kwargs
    assert kwargs["modelo"] == BedrockClient.CLAUDE_HAIKU
    assert kwargs["max_tokens"] == 123 and kwargs["temperature"] == 0.2


def test_el_validador_de_contenido_lee_la_respuesta_en_bloque_json():
    """Haiku 4.5 responde con el JSON dentro de un bloque ```json; debe interpretarse como resultado real."""
    from src.validators.content_validator import ContentValidator
    validador = ContentValidator.__new__(ContentValidator)
    r = validador._parsear_respuesta(
        '```json\n{"calificacion_general": "REQUIERE_CAMBIOS", "puntaje": 55, '
        '"errores": ["Falta alineación"], "sugerencias": ["Revisar criterios"]}\n```')
    assert r["calificacion_general"] == "REQUIERE_CAMBIOS" and r["puntaje"] == 55 and r["errores"] == ["Falta alineación"]


def test_la_variable_esta_documentada():
    env = (RAIZ / ".env.example").read_text(encoding="utf-8")
    assert "BEDROCK_VALIDATION_MODEL_ID" in env


# --- El validador de contenido lee y limita bien lo que recibe del modelo ---

def _validador():
    from src.validators.content_validator import ContentValidator
    return ContentValidator.__new__(ContentValidator)


def test_acepta_un_bloque_json_sin_el_cierre_de_las_comillas_invertidas():
    r = _validador()._parsear_respuesta('```json\n{"calificacion_general": "APROBADO", "puntaje": 90, "errores": [], "sugerencias": []}')
    assert r["puntaje"] == 90 and r["errores"] == []


def test_acepta_json_sin_bloque_de_codigo():
    r = _validador()._parsear_respuesta('{"calificacion_general": "RECHAZADO", "puntaje": 30, "errores": [], "sugerencias": []}')
    assert r["calificacion_general"] == "RECHAZADO"


def test_una_respuesta_cortada_a_la_mitad_cae_al_resultado_neutro():
    r = _validador()._parsear_respuesta('```json\n{"calificacion_general": "RECHAZADO", "puntaje": 45, "errores": [{"criterio": "ESTR')
    assert r["calificacion_general"] == "APROBADO" and r["puntaje"] == 70 and "no fue JSON válido" in r["sugerencias"][0]


def test_el_validador_pide_suficientes_tokens_y_muestra_el_documento_completo():
    from src.validators import content_validator as cv

    assert cv.MAX_TOKENS_RESPUESTA >= 2000                 # con 800 la respuesta de Haiku 4.5 se cortaba
    assert cv.MAX_CARACTERES_VALIDACION >= 30000           # una Unidad real llega a ~30 mil caracteres

    validador = _validador()
    validador.prompt_manager = MagicMock()
    validador.prompt_manager.cargar.return_value = "PROMPT"
    validador.bedrock = MagicMock()
    validador.bedrock.invocar_validacion.return_value = '{"calificacion_general": "APROBADO", "puntaje": 88, "errores": [], "sugerencias": []}'

    texto = "x" * (cv.MAX_CARACTERES_VALIDACION + 5000)
    resultado = validador.validar(texto, area_curricular="Arte", grado="1")
    enviado = validador.prompt_manager.cargar.call_args.kwargs["contenido"]
    assert len(enviado) == cv.MAX_CARACTERES_VALIDACION     # se recorta solo lo que excede el tope
    assert validador.bedrock.invocar_validacion.call_args.kwargs["max_tokens"] == cv.MAX_TOKENS_RESPUESTA
    assert resultado["puntaje"] == 88


def test_el_prompt_de_validacion_pide_respuestas_breves():
    from src.core.prompt_manager import get_prompt_manager
    prompt = get_prompt_manager().cargar("validacion", tipo_documento="unidad", contenido="x", area_curricular="Arte",
                                        grado="1", secciones_requeridas="A, B")
    assert "Sé conciso" in prompt and "máximo 5 errores" in prompt
    assert '"calificacion_general"' in prompt               # las llaves del ejemplo JSON siguen bien escapadas
