# eval/build_gold_estructurado.py
"""
Genera gold_estructurado.json: consultas de programacion curricular cuya relevancia sale de los METADATOS del
corpus (programa_curricular_secundaria_2016.json), no de una lectura subjetiva de cada chunk.

Lo unico que se decide a mano por consulta es (area, grado, tema, competencia objetivo). Dado eso:
  relevancia 2: chunk de desempenos de esa competencia y ESE grado
  relevancia 1: chunk de la competencia en el ciclo del grado (capacidades) y estandares del ciclo (VI / VII)
Cada consulta se emite en dos variantes: 'estructurado' (formato real de GeneratorAgent._buscar_contexto_rag) y
'tema_solo' (solo el tema; area y grado viajan como parametros).

Uso (desde la raiz del repo):  python -m src.eval.build_gold_estructurado
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "programa_curricular_secundaria_2016.json"
SALIDA = Path(__file__).parent / "gold_estructurado.json"
CICLO = {1: "VI", 2: "VI", 3: "VII", 4: "VII", 5: "VII"}

# (area, grado, tema, clave de competencia objetivo). Criterio: la competencia que el CNEB asocia al tema.
CONSULTAS = [
    ("Ciencia y Tecnología", 3, "energía y ecosistemas", "mundo_fisico"),
    ("Ciencia y Tecnología", 1, "estructura de la célula y biodiversidad", "mundo_fisico"),
    ("Ciencia y Tecnología", 5, "genética y herencia", "mundo_fisico"),
    ("Ciencia y Tecnología", 2, "método científico, hipótesis y experimentos", "indaga"),
    ("Ciencia y Tecnología", 3, "indagación sobre la calidad del agua", "indaga"),
    ("Ciencia y Tecnología", 4, "prototipo de un filtro de agua", "tecnologia"),
    ("Matemática", 1, "números racionales y operaciones", "cantidad"),
    ("Matemática", 2, "ecuaciones lineales", "regularidad"),
    ("Matemática", 5, "funciones y su gráfica", "regularidad"),
    ("Matemática", 3, "volumen de prismas y cilindros", "forma"),
    ("Matemática", 4, "medidas de tendencia central y probabilidad", "datos"),
    ("Comunicación", 1, "comprensión de textos narrativos", "lee_lm"),
    ("Comunicación", 3, "comprensión de textos expositivos", "lee_lm"),
    ("Comunicación", 4, "textos argumentativos", "escribe_lm"),
    ("Comunicación", 5, "debate y exposición oral", "oral_lm"),
    ("Ciencias Sociales", 3, "la independencia del Perú", "historia"),
    ("Ciencias Sociales", 2, "cuencas hidrográficas y gestión del riesgo de desastres", "espacio"),
    ("Ciencias Sociales", 5, "ahorro, inflación y consumo responsable", "economia"),
    ("Desarrollo Personal, Ciudadanía y Cívica", 1, "autoestima y emociones en la adolescencia", "identidad"),
    ("Desarrollo Personal, Ciudadanía y Cívica", 4, "participación ciudadana y democracia", "convive"),
    ("Educación Física", 3, "capacidades físicas y condición física", "saludable"),
    ("Educación Física", 2, "deportes colectivos y cooperación", "sociomotrices"),
    ("Educación Física", 1, "coordinación y expresión corporal", "motricidad"),
    ("Arte y Cultura", 2, "apreciación de manifestaciones artísticas locales", "aprecia"),
    ("Arte y Cultura", 5, "proyecto de teatro o danza", "crea"),
    ("Inglés como Lengua Extranjera", 1, "describir rutinas y hábitos", "ingles_oral"),
    ("Inglés como Lengua Extranjera", 4, "leer textos cortos", "ingles_lee"),
    ("Inglés como Lengua Extranjera", 3, "escribir un correo electrónico", "ingles_escribe"),
    ("Castellano como Segunda Lengua", 2, "escribir textos narrativos", "l2_escribe"),
    ("Educación para el Trabajo", 4, "emprendimiento y plan de negocio", "emprende"),
    ("Educación Religiosa", 3, "dignidad humana y doctrina de la propia religión", "religion_identidad"),
    ("Educación Religiosa", 5, "proyecto de vida y fe", "religion_encuentro"),
    ("Competencias transversales", 3, "entornos virtuales y herramientas digitales", "tic"),
    ("Competencias transversales", 4, "metas de aprendizaje y autorregulación", "autonomo"),
]

# clave -> (modo, texto) con que se localiza la competencia en el corpus
CLAVES = {
    "mundo_fisico": ("sw", "Explica el mundo físico"), "indaga": ("sw", "Indaga mediante"),
    "tecnologia": ("sw", "Diseña y construye soluciones"),
    "cantidad": ("sw", "Resuelve problemas de cantidad"), "regularidad": ("in", "regularidad, equivalencia"),
    "forma": ("in", "forma, movimiento"), "datos": ("in", "gestión de datos"),
    "oral_lm": ("eq", "Se comunica oralmente en su lengua materna"),
    "lee_lm": ("in", "textos escritos en lengua materna"), "escribe_lm": ("in", "textos en lengua materna"),
    "historia": ("in", "interpretaciones históricas"), "espacio": ("in", "el espacio y el ambiente"),
    "economia": ("in", "recursos económicos"),
    "identidad": ("eq", "Construye su identidad"), "convive": ("sw", "Convive y participa"),
    "saludable": ("eq", "Asume una vida saludable"), "sociomotrices": ("in", "habilidades sociomotrices"),
    "motricidad": ("in", "a través de su motricidad"),
    "aprecia": ("sw", "Aprecia de manera crítica"), "crea": ("sw", "Crea proyectos"),
    "ingles_oral": ("sw", "Se comunica oralmente en inglés"), "ingles_lee": ("sw", "Lee diversos tipos de textos en inglés"),
    "ingles_escribe": ("sw", "Escribe diversos tipos de textos en inglés"),
    "l2_escribe": ("sw", "Escribe diversos tipos de textos en castellano"),
    "emprende": ("sw", "Gestiona proyectos"),
    "religion_identidad": ("sw", "Construye su identidad como persona"), "religion_encuentro": ("sw", "Asume la experiencia"),
    "tic": ("in", "entornos virtuales"), "autonomo": ("sw", "Gestiona su aprendizaje"),
}


def localizar(clave, competencias):
    modo, txt = CLAVES[clave]
    f = {"eq": lambda c: c == txt, "sw": lambda c: c.startswith(txt), "in": lambda c: txt in c}[modo]
    hallados = [c for c in competencias if f(c)]
    assert len(hallados) == 1, f"clave {clave!r}: {len(hallados)} coincidencias {hallados}"
    return hallados[0]


def main():
    chunks = json.loads(DATA.read_text(encoding="utf-8"))["chunks"]
    competencias = sorted({c["competencia"] for c in chunks if c.get("competencia")})
    queries = []
    for n, (area, grado, tema, clave) in enumerate(CONSULTAS, 1):
        comp = localizar(clave, competencias)
        ciclo = CICLO[grado]
        rel = {}
        for c in chunks:
            if c.get("competencia") != comp:
                continue
            if c["tipo"] == "desempenos" and c["grado"] == grado:
                rel[f"programa:{c['id']}"] = 2
            elif c["tipo"] == "competencia" and c["ciclo"] == ciclo:
                rel[f"programa:{c['id']}"] = 1
            elif c["tipo"] == "estandar" and c["ciclo"] == ciclo:
                rel[f"programa:{c['id']}"] = 1
        assert any(v == 2 for v in rel.values()), f"sin desempenos relevantes para {area} {grado} {comp}"
        slug = area.replace(" ", "_").lower()
        meta = {"area": area, "area_slug": slug, "grado": grado, "competencia_objetivo": comp}
        queries.append({"id": f"e{n:02d}", "tipo": "estructurado", **meta, "relevantes": rel,
                        "query": f"programación curricular {area} {grado} grado secundaria {tema}"})
        queries.append({"id": f"t{n:02d}", "tipo": "tema_solo", **meta, "relevantes": rel, "query": tema})
    SALIDA.write_text(json.dumps({
        "_nota": "Relevancia derivada de metadatos (area, grado, ciclo, competencia). La competencia objetivo por tema es "
                 "criterio del autor y debe validarse con un docente. 2 = desempenos de la competencia en ESE grado; "
                 "1 = capacidades de la competencia en el ciclo y estandares del ciclo.",
        "queries": queries}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(queries)} consultas ({len(CONSULTAS)} x 2 variantes) -> {SALIDA}")


if __name__ == "__main__":
    main()
