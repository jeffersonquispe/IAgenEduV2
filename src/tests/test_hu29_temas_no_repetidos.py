"""HU-29 (fase 1): detección de temas repetidos entre las sesiones de una Unidad."""

from src.utils.table_utils import extraer_sesiones_numeradas
from src.validators.structure_validator import StructureValidator

# Todas las secciones obligatorias salvo la secuencia (que arma _unidad): así el
# reporte no trae errores críticos y el puntaje base es 100.
_OTRAS = [x for x in StructureValidator.SECCIONES_UNIDAD if x != "SECUENCIA"]
RELLENO = "| ITEM | CONTENIDO |\n|------|-----------|\n" + "".join(
    f"| **{x}** | contenido de prueba |\n" for x in _OTRAS
)


def _unidad(*titulos: str) -> str:
    sesiones = "\n".join(
        f"Sesión {i}: Título: {t}. Criterio de evaluación: criterio {i}. Principales actividades: x."
        for i, t in enumerate(titulos, 1)
    )
    return RELLENO + f"| **SECUENCIA DE SESIONES** | {sesiones} |\n"


def _repetidos(contenido, n=None):
    rep = StructureValidator().validar_unidad_didactica(contenido, num_sesiones=n)
    return [e for e in rep.errores if "mismo tema" in e.mensaje], rep


# --- extraer_sesiones_numeradas ---

def test_extrae_titulo_sin_prefijo_ni_metadatos():
    r = extraer_sesiones_numeradas(_unidad("La noticia y sus partes", "Fracciones equivalentes"))
    assert r == {1: "La noticia y sus partes", 2: "Fracciones equivalentes"}


def test_corta_antes_de_criterio_aunque_no_haya_punto():
    r = extraer_sesiones_numeradas("Sesión 1: Título: Mi tema Criterio de evaluación: algo")
    assert r == {1: "Mi tema"}


def test_conserva_primera_aparicion_de_cada_numero():
    r = extraer_sesiones_numeradas("Sesión 1: Tema A\nSesión 1: otra mención\nSesión 2: Tema B")
    assert r == {1: "Tema A", 2: "Tema B"}


def test_acepta_negritas_y_guion():
    r = extraer_sesiones_numeradas("**Sesión 1:** Tema uno\nSesión 2 - Tema dos")
    assert r == {1: "Tema uno", 2: "Tema dos"}


def test_contenido_vacio():
    assert extraer_sesiones_numeradas("") == {}


# --- validador ---

def test_titulos_distintos_no_generan_advertencia():
    rep, _ = _repetidos(_unidad("La noticia", "Fracciones equivalentes", "El ciclo del agua"), 3)
    assert rep == []


def test_titulos_identicos_se_marcan():
    rep, _ = _repetidos(_unidad("Fracciones equivalentes", "El agua", "Fracciones equivalentes"))
    assert len(rep) == 1
    assert "sesiones 1 y 3" in rep[0].mensaje


def test_ignora_mayusculas_tildes_y_signos():
    rep, _ = _repetidos(_unidad("Función cuadrática", "FUNCION CUADRATICA!"))
    assert len(rep) == 1


def test_titulos_muy_similares_se_marcan():
    rep, _ = _repetidos(_unidad("Fracciones equivalentes", "Las fracciones equivalentes"))
    assert len(rep) == 1


def test_titulos_que_solo_comparten_una_palabra_no_se_marcan():
    rep, _ = _repetidos(_unidad("Fracciones equivalentes", "Fracciones en la vida diaria"))
    assert rep == []


def test_cada_par_repetido_se_reporta_una_vez():
    rep, _ = _repetidos(_unidad("Tema X", "Tema X", "Tema X"))
    assert len(rep) == 3          # (1,2) (1,3) (2,3)


def test_es_advertencia_y_baja_el_puntaje_sin_rechazar():
    _, reporte = _repetidos(_unidad("Tema X", "Tema X"))
    adv = [e for e in reporte.errores if "mismo tema" in e.mensaje][0]
    assert adv.tipo == "ADVERTENCIA" and adv.categoria == "CONTENIDO"
    sin = StructureValidator().validar_unidad_didactica(_unidad("Tema X", "Tema Y"))
    assert reporte.puntaje == sin.puntaje - 10


def test_una_sola_sesion_no_se_compara():
    rep, _ = _repetidos(_unidad("Solo una"))
    assert rep == []
