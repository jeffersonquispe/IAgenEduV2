"""
Módulo para gestionar las competencias del Currículo Nacional de Educación Básica del Perú.
Contiene las 31 competencias del CNEB (29 de área + 2 transversales), cada una con su área, y la malla curricular
de Educación Secundaria. La fuente de verdad es el Programa Curricular (data/programa_curricular_secundaria_2016.json);
src/tests/test_catalogo_competencias.py verifica que este catálogo coincida con él.
"""
import os
import re
import unicodedata

# Áreas curriculares del Programa Curricular de Educación Secundaria – Perú (2016), sección 5
AREAS_CURRICULARES_SECUNDARIA = [
    "Desarrollo Personal, Ciudadanía y Cívica",
    "Ciencias Sociales",
    "Educación Física",
    "Arte y Cultura",
    "Comunicación",
    "Castellano como Segunda Lengua",
    "Inglés como Lengua Extranjera",
    "Matemática",
    "Ciencia y Tecnología",
    "Educación para el Trabajo",
    "Educación Religiosa",
]

# Grados (cursos) de Educación Secundaria según malla curricular – 1° a 5°
GRADOS_SECUNDARIA = ["1°", "2°", "3°", "4°", "5°"]


def obtener_areas_curriculares_secundaria():
    """Devuelve la lista de áreas curriculares de secundaria para menús (malla curricular)."""
    return list(AREAS_CURRICULARES_SECUNDARIA)


def obtener_grados_secundaria():
    """Devuelve la lista de grados/cursos de secundaria para menús (1° a 5°)."""
    return list(GRADOS_SECUNDARIA)


# Competencias transversales: el CNEB las plantea para todas las áreas, no para una sola.
AREA_TRANSVERSAL = "Competencias transversales"

# `numero` es un identificador estable (valor del selector del wizard y prefijo 'COMPETENCIA N.' del texto que viaja
# al generador): no se renumera ni se reutiliza. Los huecos (22-29) eran entradas que no son competencias.
COMPETENCIAS_CURRICULARES = [
    {
        "numero": 1,
        "nombre": "Construye su identidad",
        "descripcion": "Construye su identidad",
        "area": "Desarrollo Personal, Ciudadanía y Cívica"
    },
    {
        "numero": 32,
        "nombre": "Convive y participa democráticamente en la búsqueda del bien común",
        "descripcion": "Convive y participa democráticamente en la búsqueda del bien común",
        "area": "Desarrollo Personal, Ciudadanía y Cívica"
    },
    {
        "numero": 19,
        "nombre": "Construye interpretaciones históricas",
        "descripcion": "Construye interpretaciones históricas",
        "area": "Ciencias Sociales"
    },
    {
        "numero": 20,
        "nombre": "Gestiona responsablemente el espacio y el ambiente",
        "descripcion": "Gestiona responsablemente el espacio y el ambiente",
        "area": "Ciencias Sociales"
    },
    {
        "numero": 21,
        "nombre": "Gestiona responsablemente los recursos económicos",
        "descripcion": "Gestiona responsablemente los recursos económicos",
        "area": "Ciencias Sociales"
    },
    {
        "numero": 3,
        "nombre": "Se desenvuelve de manera autónoma a través de su motricidad",
        "descripcion": "Se desenvuelve de manera autónoma a través de su motricidad",
        "area": "Educación Física"
    },
    {
        "numero": 2,
        "nombre": "Asume una vida saludable",
        "descripcion": "Asume una vida saludable",
        "area": "Educación Física"
    },
    {
        "numero": 33,
        "nombre": "Interactúa a través de sus habilidades sociomotrices",
        "descripcion": "Interactúa a través de sus habilidades sociomotrices",
        "area": "Educación Física"
    },
    {
        "numero": 17,
        "nombre": "Aprecia de manera crítica manifestaciones artístico-culturales",
        "descripcion": "Aprecia de manera crítica manifestaciones artístico-culturales",
        "area": "Arte y Cultura"
    },
    {
        "numero": 18,
        "nombre": "Crea proyectos desde los lenguajes artísticos",
        "descripcion": "Crea proyectos desde los lenguajes artísticos",
        "area": "Arte y Cultura"
    },
    {
        "numero": 4,
        "nombre": "Se comunica oralmente en su lengua materna",
        "descripcion": "Se comunica oralmente en su lengua materna",
        "area": "Comunicación"
    },
    {
        "numero": 5,
        "nombre": "Lee diversos tipos de textos escritos en su lengua materna",
        "descripcion": "Lee diversos tipos de textos escritos en su lengua materna",
        "area": "Comunicación"
    },
    {
        "numero": 6,
        "nombre": "Escribe diversos tipos de textos en su lengua materna",
        "descripcion": "Escribe diversos tipos de textos en su lengua materna",
        "area": "Comunicación"
    },
    {
        "numero": 34,
        "nombre": "Se comunica oralmente en castellano como segunda lengua",
        "descripcion": "Se comunica oralmente en castellano como segunda lengua",
        "area": "Castellano como Segunda Lengua"
    },
    {
        "numero": 35,
        "nombre": "Lee diversos tipos de textos escritos en castellano como segunda lengua",
        "descripcion": "Lee diversos tipos de textos escritos en castellano como segunda lengua",
        "area": "Castellano como Segunda Lengua"
    },
    {
        "numero": 36,
        "nombre": "Escribe diversos tipos de textos en castellano como segunda lengua",
        "descripcion": "Escribe diversos tipos de textos en castellano como segunda lengua",
        "area": "Castellano como Segunda Lengua"
    },
    {
        "numero": 7,
        "nombre": "Se comunica oralmente en inglés como lengua extranjera",
        "descripcion": "Se comunica oralmente en inglés como lengua extranjera",
        "area": "Inglés como Lengua Extranjera"
    },
    {
        "numero": 37,
        "nombre": "Lee diversos tipos de textos en inglés como lengua extranjera",
        "descripcion": "Lee diversos tipos de textos en inglés como lengua extranjera",
        "area": "Inglés como Lengua Extranjera"
    },
    {
        "numero": 38,
        "nombre": "Escribe diversos tipos de textos en inglés como lengua extranjera",
        "descripcion": "Escribe diversos tipos de textos en inglés como lengua extranjera",
        "area": "Inglés como Lengua Extranjera"
    },
    {
        "numero": 8,
        "nombre": "Resuelve problemas de cantidad",
        "descripcion": "Resuelve problemas de cantidad",
        "area": "Matemática"
    },
    {
        "numero": 9,
        "nombre": "Resuelve problemas de regularidad, equivalencia y cambio",
        "descripcion": "Resuelve problemas de regularidad, equivalencia y cambio",
        "area": "Matemática"
    },
    {
        "numero": 10,
        "nombre": "Resuelve problemas de forma, movimiento y localización",
        "descripcion": "Resuelve problemas de forma, movimiento y localización",
        "area": "Matemática"
    },
    {
        "numero": 11,
        "nombre": "Resuelve problemas de gestión de datos e incertidumbre",
        "descripcion": "Resuelve problemas de gestión de datos e incertidumbre",
        "area": "Matemática"
    },
    {
        "numero": 12,
        "nombre": "Indaga mediante métodos científicos para construir conocimientos",
        "descripcion": "Indaga mediante métodos científicos para construir conocimientos",
        "area": "Ciencia y Tecnología"
    },
    {
        "numero": 13,
        "nombre": "Explica el mundo físico basándose en conocimientos sobre los seres vivos; materia y energía; biodiversidad, Tierra y universo",
        "descripcion": "Explica el mundo físico basándose en conocimientos sobre los seres vivos; materia y energía; biodiversidad, Tierra y universo",
        "area": "Ciencia y Tecnología"
    },
    {
        "numero": 14,
        "nombre": "Diseña y construye soluciones tecnológicas para resolver problemas de su entorno",
        "descripcion": "Diseña y construye soluciones tecnológicas para resolver problemas de su entorno",
        "area": "Ciencia y Tecnología"
    },
    {
        "numero": 15,
        "nombre": "Gestiona proyectos de emprendimiento económico o social",
        "descripcion": "Gestiona proyectos de emprendimiento económico o social",
        "area": "Educación para el Trabajo"
    },
    {
        "numero": 31,
        "nombre": "Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente, comprendiendo la doctrina de su propia religión, abierto al diálogo con las que le son cercanas",
        "descripcion": "Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente, comprendiendo la doctrina de su propia religión, abierto al diálogo con las que le son cercanas",
        "area": "Educación Religiosa"
    },
    {
        "numero": 30,
        "nombre": "Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida en coherencia con su creencia religiosa",
        "descripcion": "Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida en coherencia con su creencia religiosa",
        "area": "Educación Religiosa"
    },
    {
        "numero": 16,
        "nombre": "Se desenvuelve en entornos virtuales generados por las TIC",
        "descripcion": "Se desenvuelve en entornos virtuales generados por las TIC",
        "area": "Competencias transversales"
    },
    {
        "numero": 39,
        "nombre": "Gestiona su aprendizaje de manera autónoma",
        "descripcion": "Gestiona su aprendizaje de manera autónoma",
        "area": "Competencias transversales"
    }
]


def obtener_competencia_por_numero(numero):
    """
    Obtiene una competencia por su número.
    
    Args:
        numero: Número de la competencia (1-31)
        
    Returns:
        Diccionario con la información de la competencia o None si no existe
    """
    try:
        for competencia in COMPETENCIAS_CURRICULARES:
            if competencia["numero"] == numero:
                return competencia
        return None
    except Exception:
        return None


def obtener_competencia_por_nombre(nombre):
    """
    Busca una competencia por su nombre (búsqueda parcial).
    
    Args:
        nombre: Nombre o parte del nombre de la competencia
        
    Returns:
        Lista de competencias que coinciden con el nombre
    """
    try:
        if not nombre:
            return []
        nombre_lower = nombre.lower()
        return [
            competencia for competencia in COMPETENCIAS_CURRICULARES
            if nombre_lower in str(competencia["nombre"]).lower()
        ]
    except Exception:
        return []


def obtener_todas_las_competencias():
    """
    Obtiene todas las competencias curriculares.
    
    Returns:
        Lista con todas las competencias
    """
    try:
        return COMPETENCIAS_CURRICULARES.copy()
    except Exception:
        return []


_ALIAS_AREAS = {
    "ciencia": "Ciencia y Tecnología", "tecnologia": "Ciencia y Tecnología",
    "arte": "Arte y Cultura", "cultura": "Arte y Cultura",
    "tutoria": "Desarrollo Personal, Ciudadanía y Cívica",
    "historia": "Ciencias Sociales", "geografia": "Ciencias Sociales", "economia": "Ciencias Sociales",
}


def _sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "").lower()) if unicodedata.category(c) != "Mn").strip()


def _area_canonica(area_curricular):
    """Nombre canónico del área ('Matemática', 'ciencia y tecnologia'...), o None si no se reconoce."""
    clave = _sin_tildes(area_curricular)
    for area in AREAS_CURRICULARES_SECUNDARIA:
        if _sin_tildes(area) == clave:
            return area
    return _ALIAS_AREAS.get(clave)


def obtener_competencias_por_area(area_curricular):
    """
    Competencias de un área curricular: las propias del área más las 2 transversales (aplican a todas).
    El área sale del campo `area` de cada competencia (fuente: Programa Curricular), no de un mapeo aparte.

    Args:
        area_curricular: Nombre del área curricular (ej: "Ciencia y Tecnología", "Matemática")

    Returns:
        Lista de competencias; vacía si el área no se reconoce.
    """
    try:
        area = _area_canonica(area_curricular)
        if not area:
            return []
        return [c for c in COMPETENCIAS_CURRICULARES if c["area"] in (area, AREA_TRANSVERSAL)]
    except Exception:
        return []


def formatear_competencia_para_tabla(competencia):
    """
    Formatea una competencia para mostrarla en formato de tabla.
    
    Args:
        competencia: Diccionario con la información de la competencia
        
    Returns:
        String formateado: "COMPETENCIA X. Nombre"
    """
    try:
        if not competencia or "numero" not in competencia or "nombre" not in competencia:
            return ""
        return f"COMPETENCIA {competencia['numero']}. {competencia['nombre']}"
    except Exception:
        return ""


# Mapeo de temas sugeridos por competencia y grado
TEMAS_POR_COMPETENCIA_Y_GRADO = {
    # Matemática
    8: {
        "1°": ["Números enteros", "Fracciones y decimales"],
        "2°": ["Potenciación y radicación"],
        "3°": ["Interés simple y compuesto"],
        "4°": ["Sistemas de numeración", "Modelos financieros"],
        "5°": ["Números reales", "Programación lineal"]
    },
    9: {
        "1°": ["Proporcionalidad", "Ecuaciones lineales simples"],
        "2°": ["Polinomios", "Ecuaciones lineales"],
        "3°": ["Ecuaciones cuadráticas", "Funciones lineales"],
        "4°": ["Funciones cuadráticas", "Logaritmos"],
        "5°": ["Límites y derivadas básicas", "Sucesiones y series"]
    },
    10: {
        "1°": ["Geometría plana", "Ángulos y triángulos"],
        "2°": ["Áreas y perímetros", "Transformaciones geométricas"],
        "3°": ["Trigonometría básica", "Geometría del espacio"],
        "4°": ["Geometría analítica", "Razones trigonométricas"],
        "5°": ["Vectores", "Secciones cónicas"]
    },
    11: {
        "1°": ["Estadística básica", "Gráficos de barras"],
        "2°": ["Probabilidades", "Medidas de posición"],
        "3°": ["Medidas de tendencia central", "Dispersión"],
        "4°": ["Inferencia estadística", "Probabilidad condicional"],
        "5°": ["Distribuciones de probabilidad", "Correlación y regresión"]
    },
    # Comunicación
    4: {
        "1°": ["Técnicas de expresión oral", "El debate"],
        "2°": ["Exposición académica", "La mesa redonda"],
        "3°": ["Discurso oral", "El foro"],
        "4°": ["Retórica y elocuencia", "Simposio"],
        "5°": ["Discurso público", "La conferencia"]
    },
    5: {
        "1°": ["Comprensión de textos narrativos", "Idea principal"],
        "2°": ["Textos expositivos", "Inferencia de significados"],
        "3°": ["Contenido implícito", "Análisis de ensayos"],
        "4°": ["Análisis crítico de textos", "Intertextualidad"],
        "5°": ["Investigación académica", "Fuentes bibliográficas"]
    },
    6: {
        "1°": ["Gramática y ortografía", "Cohesión textual"],
        "2°": ["Coherencia y cohesión", "Tipología textual"],
        "3°": ["Textos argumentativos", "Propiedades del texto"],
        "4°": ["Ensayos literarios", "Estilo y registro"],
        "5°": ["Redacción de artículos", "Normas APA"]
    },
    # Ciencia y Tecnología
    12: {
        "1°": ["Método científico", "La observación"],
        "2°": ["Indagación científica", "Variables"],
        "3°": ["Experimentación", "Hipótesis"],
        "4°": ["Diseño de investigaciones", "Análisis de datos"],
        "5°": ["Proyectos de investigación", "Validación científica"]
    },
    13: {
        "1°": ["La célula", "Reinos biológicos"],
        "2°": ["Funciones vitales", "Genética"],
        "3°": ["Bioquímica", "Microbiología"],
        "4°": ["Anatomía y fisiología", "Química orgánica"],
        "5°": ["Biotecnología", "Evolución", "Física moderna"]
    },
    14: {
        "1°": ["Diseño de prototipos", "Soluciones tecnológicas"],
        "2°": ["Construcción de modelos", "Evaluación tecnológica"],
        "3°": ["Impacto ambiental", "Sostenibilidad"],
        "4°": ["Tecnología sustentable", "Energías limpias"],
        "5°": ["Innovación tecnológica", "Robótica básica"]
    },
    # Ciencias Sociales
    19: {
        "1°": ["Civilizaciones antiguas", "Edad Media"],
        "2°": ["Perú prehispánico", "Incario"],
        "3°": ["Virreinato del Perú", "Emancipación"],
        "4°": ["República del Perú", "Guerras mundiales"],
        "5°": ["Historia contemporánea", "Conflicto armado interno"]
    },
    20: {
        "1°": ["Geografía física", "Relieve terrestre"],
        "2°": ["Geografía del Perú", "8 regiones"],
        "3°": ["Geografía mundial", "Continentes"],
        "4°": ["Problemas ambientales", "Gestión de riesgos"],
        "5°": ["Desarrollo sostenible", "Cambio climático"]
    },
    21: {
        "1°": ["Economía familiar", "Ahorro"],
        "2°": ["Mercado y precios", "Consumo responsable"],
        "3°": ["Sistema financiero", "Tributación"],
        "4°": ["Estado y economía", "Comercio internacional"],
        "5°": ["Globalización", "Modelos económicos"]
    },
    # Desarrollo Personal, Ciudadanía y Cívica
    1: {
        "1°": ["Identidad y autoestima", "Emociones y sentimientos"],
        "2°": ["Autoconocimiento", "Valores éticos"],
        "3°": ["Proyecto de vida", "Ética y moral"],
        "4°": ["Dilemas morales", "Sentido de pertenencia"],
        "5°": ["Ética en la sociedad", "Derechos y responsabilidades"]
    },
    2: {
        "1°": ["Cultura y diversidad", "Convivencia democrática"],
        "2°": ["Presión de grupo", "Conflictos interpersonales"],
        "3°": ["Derechos Humanos", "Participación ciudadana"],
        "4°": ["Identidad cultural", "Participación estudiantil"],
        "5°": ["Ciudadanía global", "Democracia y justicia"]
    },
    25: {
        "1°": ["Cambios físicos y psicológicos"],
        "2°": ["Relaciones interpersonales"],
        "3°": ["Sexualidad responsable", "Prevención de riesgos"],
        "4°": ["Dilemas éticos en la sexualidad"],
        "5°": ["Salud reproductiva", "Proyecto de vida"]
    },
    # Educación para el Trabajo
    15: {
        "1°": ["Creatividad e innovación", "Diseño de prototipos"],
        "2°": ["Modelos de negocio (Lean Canvas)", "Marketing digital"],
        "3°": ["Plan de negocios", "Programación básica"],
        "4°": ["Gestión de proyectos (PMBOK)", "Administración de empresas"],
        "5°": ["Liderazgo y trabajo en equipo", "Inserción laboral"]
    },
    # Arte y Cultura
    17: {
        "1°": ["Expresión corporal", "Apreciación artística"],
        "2°": ["Gimnasia básica", "Elementos del arte"],
        "3°": ["Ritmo y danza", "Historia del arte"],
        "4°": ["Actividades en la naturaleza", "Gestión cultural"],
        "5°": ["Expresión rítmica avanzada", "Proyectos artísticos"]
    },
    # Educación Religiosa
    30: {
        "1°": ["La Biblia", "Historia de la salvación"],
        "2°": ["Vida de Jesús", "Los mandamientos"],
        "3°": ["La Iglesia", "Sacramentos"],
        "4°": ["Moral cristiana", "Doctrina social"],
        "5°": ["Proyecto de vida", "Testimonio de fe"]
    }
}


def obtener_temas_por_competencias_y_grado(competencias_seleccionadas, grado):
    """
    Obtiene temas sugeridos basados en una lista de competencias y el grado.
    
    Args:
        competencias_seleccionadas: Lista de strings de competencias (ej: "COMPETENCIA 8. ...")
                                   o lista de números de competencias.
        grado: Grado de secundaria (1° a 5°)
        
    Returns:
        Lista de temas únicos relacionados con las competencias y grado.
    """
    try:
        if not competencias_seleccionadas or not grado:
            return []
            
        numeros_competencias = []
        for comp in competencias_seleccionadas:
            if isinstance(comp, int):
                numeros_competencias.append(comp)
            elif isinstance(comp, str):
                # Extraer número de "COMPETENCIA X. ..."
                match = re.search(r'COMPETENCIA (\d+)', comp)
                if match:
                    numeros_competencias.append(int(match.group(1)))
                else:
                    # Intentar buscar el nombre de la competencia para obtener su número
                    comp_lower = comp.lower()
                    for c_dict in COMPETENCIAS_CURRICULARES:
                        nombre_comp = str(c_dict.get("nombre", "")).lower()
                        if nombre_comp and (nombre_comp in comp_lower or comp_lower in nombre_comp):
                            numeros_competencias.append(int(c_dict.get("numero", 0)))
                            break
        
        temas = set()
        for num in numeros_competencias:
            if num in TEMAS_POR_COMPETENCIA_Y_GRADO:
                temas_comp = TEMAS_POR_COMPETENCIA_Y_GRADO[num].get(grado, [])
                for t in temas_comp:
                    temas.add(t)
        
        return sorted(list(temas))
    except Exception:
        return []



# Mapeo de temas sugeridos por área y grado (Programa Curricular Secundaria) - Mantener para compatibilidad
TEMAS_POR_AREA_Y_GRADO = {
    "Matemática": {
        "1°": ["Números enteros", "Fracciones y decimales", "Proporcionalidad", "Geometría plana", "Estadística básica"],
        "2°": ["Potenciación y radicación", "Polinomios", "Ecuaciones lineales", "Áreas y perímetros", "Probabilidades"],
        "3°": ["Ecuaciones cuadráticas", "Funciones lineales", "Trigonometría básica", "Geometría del espacio", "Medidas de tendencia central"],
        "4°": ["Sistemas de ecuaciones", "Funciones cuadráticas", "Logaritmos", "Geometría analítica", "Inferencia estadística"],
        "5°": ["Programación lineal", "Límites y derivadas básicas", "Vectores", "Secciones cónicas", "Distribuciones de probabilidad"]
    },
    "Comunicación": {
        "1°": ["Comprensión de textos narrativos", "Gramática y ortografía", "Técnicas de expresión oral", "Literatura infantil y juvenil"],
        "2°": ["Textos expositivos", "Coherencia y cohesión textual", "Argumentación inicial", "Géneros literarios"],
        "3°": ["Textos argumentativos", "Análisis literario", "Debate y foro", "Literatura peruana"],
        "4°": ["Ensayos literarios", "Retórica y estilo", "Periodismo escolar", "Literatura latinoamericana"],
        "5°": ["Análisis crítico de textos", "Investigación académica", "Discurso público", "Literatura universal"]
    },
    "Ciencia y Tecnología": {
        "1°": ["La célula", "Reinos de los seres vivos", "Ecosistemas", "Materia y energía", "El sistema solar"],
        "2°": ["Funciones vitales", "Genética básica", "Química inorgánica", "Fenómenos físicos", "Cuidado del ambiente"],
        "3°": ["Bioquímica", "Microbiología", "Mecánica clásica", "Electricidad y magnetismo", "Recursos naturales"],
        "4°": ["Anatomía humana", "Fisiología", "Química orgánica", "Termodinámica", "Tecnología sustentable"],
        "5°": ["Biotecnología", "Física moderna", "Evolución", "Ecología de poblaciones", "Proyectos de innovación tecnológica"]
    },
    "Ciencias Sociales": {
        "1°": ["Historia personal y familiar", "Primeras civilizaciones", "Geografía física", "Derechos y responsabilidades"],
        "2°": ["Historia del Perú prehispánico", "Geografía del Perú", "Economía doméstica", "Convivencia democrática"],
        "3°": ["Historia del Perú colonial", "Geografía mundial", "Mercado y consumo", "Participación ciudadana"],
        "4°": ["Historia del Perú republicano", "Problemas ambientales", "Sistema financiero", "Estado y constitución"],
        "5°": ["Historia contemporánea", "Geopolítica", "Desarrollo sostenible", "Seguridad y defensa nacional"]
    },
    "Educación Física": {
        "1°": ["Habilidades motrices básicas", "Hábitos de higiene", "Juegos tradicionales", "Expresión corporal corporal"],
        "2°": ["Capacidades físicas", "Nutrición saludable", "Iniciación deportiva", "Gimnasia básica"],
        "3°": ["Técnicas deportivas", "Primeros auxilios", "Deportes colectivos", "Ritmo y danza"],
        "4°": ["Estrategias de juego", "Fisiología del ejercicio", "Atletismo", "Actividades en la naturaleza"],
        "5°": ["Entrenamiento personal", "Gestión deportiva", "Vida activa y salud", "Expresión rítmica avanzada"]
    },
    "Desarrollo Personal, Ciudadanía y Cívica": {
        "1°": ["Identidad y autoestima", "Emociones y sentimientos", "Vínculos familiares", "Cultura y diversidad"],
        "2°": ["Autoconocimiento", "Presión de grupo", "Conflictos interpersonales", "Valores éticos"],
        "3°": ["Proyecto de vida", " sexualidad responsable", "Ética y moral", "Derechos Humanos"],
        "4°": ["Identidad cultural", "Dilemas morales", "Participación estudiantil", "Poderes del Estado"],
        "5°": ["Ética en la sociedad", "Ciudadanía global", "Democracia y justicia", "Retos de la convivencia"]
    },
    "Educación para el Trabajo": {
        "1°": ["Diseño de prototipos", "Herramientas digitales básicas", "Seguridad en el trabajo", "Creatividad e innovación"],
        "2°": ["Modelos de negocio (Lean Canvas)", "Marketing digital", "Presupuestos y costos", "Gestión de recursos"],
        "3°": ["Plan de negocios", "Programación básica", "Dibujo técnico", "Emprendimiento social"],
        "4°": ["Gestión de proyectos (PMBOK)", "Administración de empresas", "Electrónica básica", "E-commerce"],
        "5°": ["Liderazgo y trabajo en equipo", "Inserción laboral", "Diseño industrial", "Planificación estratégica empresarial"]
    }
}


def obtener_temas_por_area_y_grado(area, grado):
    """
    Obtiene una lista de temas sugeridos según el área y el grado.
    
    Args:
        area: Nombre del área curricular
        grado: Grado de secundaria (1° a 5°)
        
    Returns:
        Lista de strings con los temas o lista vacía si no se encuentran
    """
    try:
        if not area or not grado:
            return []
            
        area_lower = area.lower()
        # Buscar el área en el mapeo (manejo de tildes y variaciones)
        for area_key, grados_dict in TEMAS_POR_AREA_Y_GRADO.items():
            if area_key.lower() in area_lower or area_lower in area_key.lower():
                # Si encontramos el área, buscar los temas para el grado exacto
                return grados_dict.get(grado, [])
        
        return []
    except Exception:
        return []


def obtener_lista_competencias_formateada():
    """
    Obtiene todas las competencias formateadas para mostrar en una lista.
    
    Returns:
        Lista de strings con formato "COMPETENCIA X. Nombre"
    """
    try:
        return [formatear_competencia_para_tabla(comp) for comp in COMPETENCIAS_CURRICULARES]
    except Exception:
        return []
