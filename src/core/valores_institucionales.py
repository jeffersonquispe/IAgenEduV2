# src/core/valores_institucionales.py
"""
Valores y enfoques transversales usados en la sección "Valores y Enfoques
Transversales" de las Unidades Didácticas generadas.

HU-36: antes `VALORES_PERMITIDOS` era una constante hardcodeada con los
valores de un colegio católico específico (incluía "Encuentro personal con
Jesucristo", "Caridad", "Experiencia comunitaria de la fe"), aplicada a TODO
documento generado sin importar la institución real del docente. El sistema
no era institucionalmente neutral.

Ahora el default es una lista genérica alineada a los enfoques transversales
del CNEB/MINEDU, sin contenido confesional. El listado católico anterior
queda disponible como preset explícito para instituciones confesionales que
lo elijan, no como comportamiento por defecto.

`resolver_valores_institucionales()` / `resolver_enfoques_transversales()`
son el punto de extensión: hoy siempre devuelven el default porque no existe
un perfil institucional persistente (HU-31). Cuando exista, deben recibir ese
perfil y devolver sus valores propios si el docente los configuró.
"""
from typing import Any, List, Optional

# Default del sistema: valores genéricos alineados a los enfoques
# transversales del CNEB, sin contenido confesional.
VALORES_CNEB_DEFAULT = [
    "Respeto", "Solidaridad", "Empatía", "Justicia",
    "Libertad y responsabilidad", "Diálogo y concertación",
    "Conciencia crítica", "Compromiso ambiental",
    "Equidad de género", "Respeto por las diferencias",
]

# Preset opcional — comportamiento anterior del sistema, ya no es el default.
# Una institución confesional puede elegirlo explícitamente cuando exista
# selección de perfil institucional (HU-31/HU-32).
VALORES_CATOLICO_PRESET = [
    "Participación", "Respeto", "Solidaridad", "Conciencia crítica",
    "Compromiso ambiental", "Apertura y acogida", "Gratitud y donación",
    "Compasión y misericordia", "Cuidado y promoción de la vida",
    "Discernimiento y compromiso", "Encuentro personal con Jesucristo",
    "Caridad", "Experiencia comunitaria de la fe",
]

PRESETS_VALORES = {
    "cneb": VALORES_CNEB_DEFAULT,
    "catolico": VALORES_CATOLICO_PRESET,
}

# Los enfoques transversales del CNEB no fueron señalados como confesionales
# en la revisión (docs/REGLAS_DE_NEGOCIO.md §1.7) — se mantienen como único
# default, pero pasan por el mismo punto de extensión para consistencia.
ENFOQUES_TRANSVERSALES_CNEB_DEFAULT = [
    "Búsqueda de la excelencia: Superación personal.",
    "Enfoque ambiental: justicia y solidaridad.",
    "Enfoque de derecho: conciencia de derechos.",
    "Atención a la diversidad: respeto por las diferencias.",
    "Enfoque orientación al bien común: empatía y solidaridad.",
    "Enfoque de derecho: libertad y responsabilidad.",
    "Enfoque Ambiental: respeto a toda forma de vida, solidaridad planetaria y equidad intergeneracional.",
    "Enfoque intercultural: respeto a la identidad cultural y diálogo intercultural.",
]


def resolver_valores_institucionales(institution_profile: Optional[Any] = None) -> List[str]:
    """Decide qué lista de valores usar para un documento generado.

    Sin perfil institucional (hoy, siempre — HU-31 no existe todavía), usa el
    default genérico CNEB. Cuando exista un perfil con valores propios
    configurados, este es el único punto que hay que tocar para conectarlo.
    """
    valores_propios = getattr(institution_profile, "valores_institucionales", None)
    if institution_profile and valores_propios:
        return valores_propios
    return VALORES_CNEB_DEFAULT


def resolver_enfoques_transversales(institution_profile: Optional[Any] = None) -> List[str]:
    """Mismo punto de extensión que `resolver_valores_institucionales`, para enfoques."""
    enfoques_propios = getattr(institution_profile, "enfoques_transversales", None)
    if institution_profile and enfoques_propios:
        return enfoques_propios
    return ENFOQUES_TRANSVERSALES_CNEB_DEFAULT
