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

    return [[(f[i] if i < len(f) else "") for i in columnas_utiles] for f in filas]
