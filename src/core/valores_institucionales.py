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
son el punto de extensión: reciben el perfil institucional (HU-31) y devuelven
los valores propios del docente si los configuró; si no, el default genérico.
El preset católico se ofrece en la pantalla de Institución (ver `listar_presets`),
donde el docente lo elige explícitamente y queda como valores propios de su perfil.
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
# Una institución confesional lo elige explícitamente en la pantalla de Institución.
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

# Textos para mostrar cada preset en la interfaz.
PRESETS_INFO = {
    "cneb": {
        "nombre": "Valores generales (CNEB)",
        "descripcion": "Valores alineados a los enfoques transversales del CNEB, sin contenido confesional. Es lo que se usa si no configuras nada.",
    },
    "catolico": {
        "nombre": "Institución católica",
        "descripcion": "Valores de un colegio católico/parroquial (incluye valores explícitamente confesionales). Úsalo solo si tu institución es confesional.",
    },
}


def listar_presets() -> List[dict]:
    """Presets de valores para ofrecer en la interfaz: [{id, nombre, descripcion, valores}]."""
    return [
        {"id": pid, "nombre": PRESETS_INFO[pid]["nombre"], "descripcion": PRESETS_INFO[pid]["descripcion"],
         "valores": list(valores)}
        for pid, valores in PRESETS_VALORES.items()
    ]


def _lista_limpia(valores: Any) -> List[str]:
    """Solo textos no vacíos y sin espacios sobrantes; cualquier otra cosa se descarta."""
    if not isinstance(valores, (list, tuple)):
        return []
    return [v.strip() for v in valores if isinstance(v, str) and v.strip()]

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

    Con un perfil que tenga valores propios, usa esos; sin perfil (o con una lista
    vacía o en blanco), usa el default genérico del CNEB.
    """
    valores_propios = _lista_limpia(getattr(institution_profile, "valores_institucionales", None))
    if institution_profile and valores_propios:
        return valores_propios
    return list(VALORES_CNEB_DEFAULT)        # copia: nadie debe poder mutar la constante


def resolver_enfoques_transversales(institution_profile: Optional[Any] = None) -> List[str]:
    """Mismo punto de extensión que `resolver_valores_institucionales`, para enfoques."""
    enfoques_propios = _lista_limpia(getattr(institution_profile, "enfoques_transversales", None))
    if institution_profile and enfoques_propios:
        return enfoques_propios
    return list(ENFOQUES_TRANSVERSALES_CNEB_DEFAULT)
