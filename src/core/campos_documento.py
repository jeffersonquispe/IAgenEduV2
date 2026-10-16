"""Campos de contenido de un documento (Unidad o Sesión): fuente única.

`Document.content` guarda estas secciones más metadatos (validacion, contenido_crudo,
titulo...). Solo estas se editan en el Editor, se exportan a PDF/DOCX y se aceptan al
guardar cambios. Debe coincidir con CONTENT_FIELDS de frontend/src/pages/Editor.jsx
(hay un test que lo comprueba).
"""

CAMPOS_DE_CONTENIDO = frozenset({
    "situacion_significativa", "propositos_de_aprendizaje",
    "valores_y_enfoques_transversales", "secuencia_de_sesiones", "materiales_basicos",
    "rubrica_unidad",
    "datos_informativos", "reto", "secuencia_didactica",
    "reflexion_sobre_la_actividad", "rubrica_sesion",
})


# Orden en que se muestran y exportan las secciones (Unidad y Sesión): los datos informativos van
# primero. El exportador lo aplica sin importar el orden en que las envíe el cliente.
ORDEN_SECCIONES = (
    "datos_informativos", "reto", "situacion_significativa", "propositos_de_aprendizaje",
    "valores_y_enfoques_transversales", "secuencia_de_sesiones", "secuencia_didactica",
    "materiales_basicos", "reflexion_sobre_la_actividad", "rubrica_unidad", "rubrica_sesion",
)

# Títulos legibles (con tildes) para PDF; el DOCX usa su plantilla.
ETIQUETAS_SECCION = {
    "datos_informativos": "Datos informativos",
    "reto": "Reto",
    "situacion_significativa": "Situación significativa",
    "propositos_de_aprendizaje": "Propósitos de aprendizaje",
    "valores_y_enfoques_transversales": "Valores y enfoques transversales",
    "secuencia_de_sesiones": "Secuencia de sesiones",
    "secuencia_didactica": "Secuencia didáctica",
    "materiales_basicos": "Materiales básicos",
    "reflexion_sobre_la_actividad": "Reflexión sobre la actividad",
    "rubrica_unidad": "Rúbrica analítica de la unidad",
    "rubrica_sesion": "Rúbrica de la sesión",
}


def ordenar_secciones(contenido: dict) -> dict:
    """Devuelve `contenido` con sus secciones en el orden canónico (el resto de claves, al final)."""
    ordenado = {k: contenido[k] for k in ORDEN_SECCIONES if k in contenido}
    ordenado.update({k: v for k, v in contenido.items() if k not in ordenado})
    return ordenado
