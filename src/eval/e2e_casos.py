# eval/e2e_casos.py
"""
Casos de la evaluacion de extremo a extremo (documento generado con y sin RAG).

Cada caso es lo que un docente indicaria en el wizard: area, grado, tema y 0-2 competencias. Se eligieron para cubrir
10 de las 11 areas, los 5 grados, y los tres escenarios de uso: 1 competencia (lo habitual), 2 competencias (el maximo
que permite HU-45) y ninguna (el docente deja que el sistema las seleccione).
"""
from typing import List, NamedTuple, Optional


class Caso(NamedTuple):
    id: str
    area: str
    grado: int
    tema: str
    competencias: List[str]          # nombres tal como los ofrece el wizard (catalogo), sin el prefijo "COMPETENCIA N."
    escenario: str                   # 1comp | 2comp | sin_comp


CASOS: List[Caso] = [
    Caso("c01", "Matemática", 2, "ecuaciones lineales", ["Resuelve problemas de regularidad, equivalencia y cambio"], "1comp"),
    Caso("c02", "Matemática", 4, "medidas de tendencia central y probabilidad",
         ["Resuelve problemas de gestión de datos e incertidumbre", "Resuelve problemas de cantidad"], "2comp"),
    Caso("c03", "Ciencia y Tecnología", 3, "energía y ecosistemas", ["Explica el mundo físico basándose en conocimientos sobre los seres vivos; materia y energía; biodiversidad, Tierra y universo"], "1comp"),
    Caso("c04", "Ciencia y Tecnología", 1, "estructura de la célula y biodiversidad", [], "sin_comp"),
    Caso("c05", "Comunicación", 4, "textos argumentativos", ["Escribe diversos tipos de textos en su lengua materna"], "1comp"),
    Caso("c06", "Comunicación", 5, "debate y exposición oral",
         ["Se comunica oralmente en su lengua materna", "Lee diversos tipos de textos escritos en su lengua materna"], "2comp"),
    Caso("c07", "Ciencias Sociales", 3, "la independencia del Perú", ["Construye interpretaciones históricas"], "1comp"),
    Caso("c08", "Desarrollo Personal, Ciudadanía y Cívica", 1, "autoestima y emociones en la adolescencia", [], "sin_comp"),
    Caso("c09", "Educación Física", 3, "capacidades físicas y condición física", ["Asume una vida saludable"], "1comp"),
    Caso("c10", "Arte y Cultura", 5, "proyecto de teatro o danza", ["Crea proyectos desde los lenguajes artísticos"], "1comp"),
    Caso("c11", "Inglés como Lengua Extranjera", 2, "describir rutinas y hábitos", [], "sin_comp"),
    Caso("c12", "Educación para el Trabajo", 4, "emprendimiento y plan de negocio",
         ["Gestiona proyectos de emprendimiento económico o social", "Gestiona su aprendizaje de manera autónoma"], "2comp"),
]
CASO_POR_ID = {c.id: c for c in CASOS}


def competencias_para_wizard(caso: Caso) -> Optional[str]:
    """Texto que el wizard envia al generador: 'COMPETENCIA N. nombre' por linea (None si no se eligio ninguna)."""
    from ..core.competencias_curriculares import COMPETENCIAS_CURRICULARES
    lineas = []
    for nombre in caso.competencias:
        n = next(c["numero"] for c in COMPETENCIAS_CURRICULARES if c["nombre"] == nombre)
        lineas.append(f"COMPETENCIA {n}. {nombre}")
    return "\n".join(lineas) if lineas else None
