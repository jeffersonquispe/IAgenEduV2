"""
Parseo de tablas Markdown (`| a | b |\n| -- | -- |\n| 1 | 2 |`) hacia filas de
celdas, para renderizar como tabla real en PDF/DOCX en vez de mostrar el
Markdown crudo. Misma lógica que `parseMarkdownTable` en Editor.jsx —
mantener ambas en sync si se cambia el criterio de detección.
"""
import re
from typing import List, Optional

_SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|$")


def parse_markdown_table(text: str) -> Optional[List[List[str]]]:
    """Devuelve filas de celdas si `text` es mayormente una tabla Markdown, o None."""
    if not text:
        return None

    lineas = [l.strip() for l in text.split("\n") if l.strip()]
    filas_tabla = [l for l in lineas if l.startswith("|") and l.endswith("|")]
    if len(filas_tabla) < 2 or len(filas_tabla) / len(lineas) < 0.5:
        return None

    filas = [
        [c.strip() for c in l[1:-1].split("|")]
        for l in filas_tabla
        if not _SEPARATOR_ROW.match(l)
    ]
    if len(filas) < 2:
        return None

    max_cols = max(len(f) for f in filas)
    columna_vacia = [
        all((f[i] if i < len(f) else "") == "" for f in filas)
        for i in range(max_cols)
    ]
    columnas_utiles = [i for i, vacia in enumerate(columna_vacia) if not vacia]
    if len(columnas_utiles) < 2:
        return None

    # Con el encabezado aparte: si el cuerpo solo tiene datos en una columna (p. ej. `ITEM | CONTENIDO`
    # con todo el texto en la primera celda) no es una tabla real; se muestra como texto.
    cuerpo_con_datos = [i for i in columnas_utiles if any(i < len(f) and f[i] for f in filas[1:])]
    if len(cuerpo_con_datos) < 2:
        return None

    return [[(f[i] if i < len(f) else "") for i in columnas_utiles] for f in filas]


def aplanar_tabla_degenerada(text: str) -> Optional[str]:
    """Si `text` es una tabla Markdown con información en una sola columna, devuelve el texto de esa
    columna (sin la fila de encabezado); si no, None."""
    if not text:
        return None
    lineas = [l.strip() for l in text.split("\n") if l.strip()]
    filas_tabla = [l for l in lineas if l.startswith("|") and l.endswith("|")]
    if len(filas_tabla) < 2 or len(filas_tabla) / len(lineas) < 0.5:
        return None
    filas = [
        [c.strip() for c in l[1:-1].split("|")]
        for l in filas_tabla
        if not _SEPARATOR_ROW.match(l)
    ]
    cuerpo = filas[1:]
    if not cuerpo:
        return None
    max_cols = max(len(f) for f in cuerpo)
    con_datos = [i for i in range(max_cols) if any(i < len(f) and f[i] for f in cuerpo)]
    if len(con_datos) != 1:
        return None
    i = con_datos[0]
    return "\n\n".join(f[i] for f in cuerpo if i < len(f) and f[i])
