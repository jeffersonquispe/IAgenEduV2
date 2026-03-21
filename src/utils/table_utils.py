# src/utils/table_utils.py
"""
Utilidades consolidadas para procesamiento de tablas Markdown.
Unifica la lógica que estaba dispersa en bedrock_services.py y app.py.
"""
import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Limpieza de HTML
# ---------------------------------------------------------------------------

def limpiar_html(contenido: str) -> str:
    """
    Elimina etiquetas HTML del contenido preservando estructura de tabla.
    Convierte <br> en saltos de línea reales.
    """
    if not contenido:
        return contenido

    lineas = contenido.split('\n')
    procesadas = []

    for linea in lineas:
        if '|' in linea:
            # Línea de tabla: limpiar HTML preservando la estructura |
            linea = re.sub(r'<br\s*/?>', '\n', linea, flags=re.IGNORECASE)
            linea = re.sub(r'<[^>]+>', '', linea)
            # Eliminar viñetas dentro de celdas
            partes = linea.split('|')
            if len(partes) >= 3:
                for idx in range(1, len(partes)):
                    celda = partes[idx]
                    celda = re.sub(r'^\s*[•\-\*→▪▫○●]\s*', '', celda, flags=re.MULTILINE)
                    celda = re.sub(r'\s+[•\-\*→▪▫○●]\s+', ' ', celda)
                    partes[idx] = celda
                linea = '|'.join(partes)
            if '\n' not in linea:
                linea = re.sub(r' +', ' ', linea)
        else:
            # Línea fuera de tabla
            linea = re.sub(r'<br\s*/?>', '\n', linea, flags=re.IGNORECASE)
            linea = re.sub(r'</p>', '\n', linea, flags=re.IGNORECASE)
            linea = re.sub(r'<p[^>]*>', '\n', linea, flags=re.IGNORECASE)
            linea = re.sub(r'<[^>]+>', '', linea)
            linea = re.sub(r'^\s*[•\-\*→▪▫○●]\s*', '', linea)
            linea = re.sub(r'\s+[•\-\*→▪▫○●]\s+', ' ', linea)

        procesadas.append(linea)

    # Eliminar líneas vacías consecutivas (máximo 1 vacía seguida)
    resultado = []
    for linea in '\n'.join(procesadas).split('\n'):
        if '|' in linea:
            resultado.append(linea)
        elif linea.strip():
            resultado.append(linea.strip())

    return '\n'.join(resultado)


# ---------------------------------------------------------------------------
#  Verificación y corrección de estructura de tabla
# ---------------------------------------------------------------------------

def tiene_tabla(contenido: str) -> bool:
    """Retorna True si el contenido contiene al menos una tabla Markdown válida."""
    if not contenido:
        return False
    s = contenido.strip()
    return (
        '| ITEM | CONTENIDO |' in s
        or '|------|-----------|' in s
        or (s.startswith('|') and '|' in s[1:])
    )


def asegurar_tabla(contenido: str) -> str:
    """Si el contenido no tiene tabla, envuelve todo en una tabla | ITEM | CONTENIDO |."""
    if not contenido:
        return contenido
    if tiene_tabla(contenido):
        return contenido

    # Intentar detectar items estructurados
    lineas = [l.strip() for l in contenido.strip().split('\n') if l.strip()]
    filas: List[Tuple[str, str]] = []
    item_actual = None
    buffer: List[str] = []

    for linea in lineas:
        es_encabezado = (
            (linea.startswith('**') and linea.endswith('**'))
            or (linea.isupper() and len(linea.split()) <= 5)
            or (':' in linea and len(linea.split(':')[0].split()) <= 4)
        )
        if es_encabezado:
            if item_actual is not None:
                filas.append((item_actual, ' '.join(buffer)))
            item_actual = linea.replace('**', '').replace(':', '').strip()
            buffer = []
        else:
            buffer.append(linea)

    if item_actual is not None:
        filas.append((item_actual, ' '.join(buffer)))

    if not filas:
        return f"| ITEM | CONTENIDO |\n|------|-----------|\n| CONTENIDO | {contenido.strip()} |"

    tabla = "| ITEM | CONTENIDO |\n|------|-----------|\n"
    for item, cont in filas:
        tabla += f"| **{item}** | {cont} |\n"
    return tabla.strip()


def validar_orden_columnas(contenido: str) -> str:
    """
    Asegura que en tablas | ITEM | CONTENIDO |, ITEM esté siempre a la
    izquierda y CONTENIDO a la derecha.
    """
    if not contenido:
        return contenido

    lineas = contenido.split('\n')
    resultado = []
    invertido = False
    en_tabla_ic = False

    for linea in lineas:
        s = linea.strip()
        if '|' not in s:
            en_tabla_ic = False
            invertido = False
            resultado.append(s)
            continue

        partes = [p.strip() for p in s.split('|')]
        if len(partes) < 3:
            resultado.append(s)
            continue

        c1 = partes[1].upper()
        c2 = partes[2].upper()

        # Detectar encabezado ITEM | CONTENIDO
        if 'ITEM' in c1 and 'CONTENIDO' in c2:
            en_tabla_ic = True
            invertido = False
            resultado.append(s)
            continue
        if 'CONTENIDO' in c1 and 'ITEM' in c2:
            en_tabla_ic = True
            invertido = True
            partes[1], partes[2] = partes[2], partes[1]

        elif en_tabla_ic and invertido:
            partes[1], partes[2] = partes[2], partes[1]

        # Reconstruir
        nueva = '|'.join(f' {p} ' if p else ' ' for p in partes)
        nueva = '|' + nueva.strip('|').strip() + '|'
        # Simplificar reconstrucción
        celdas = [p.strip() for p in partes if p or p == '']
        nueva_linea = '| ' + ' | '.join(celdas[1:]) + ' |' if len(celdas) > 1 else s
        resultado.append(nueva_linea)

    return '\n'.join(resultado)


def forzar_contenido_en_tabla(contenido: str) -> str:
    """
    Pasada final: convierte cualquier línea suelta (sin |) que esté dentro de
    una zona de tabla en una fila | | contenido_suelto |.
    """
    if not contenido:
        return contenido

    lineas = contenido.split('\n')
    resultado = []
    en_tabla = False

    for linea in lineas:
        s = linea.strip()
        if '| ITEM | CONTENIDO |' in s or '|------|-----------|' in s:
            en_tabla = True
            resultado.append(s)
        elif en_tabla and '|' in s:
            resultado.append(s)
        elif en_tabla and s:
            # Contenido suelto dentro de zona de tabla → convertir a fila
            resultado.append(f"|  | {s} |")
        elif not s:
            resultado.append('')
        else:
            resultado.append(s)

    return '\n'.join(resultado)


# ---------------------------------------------------------------------------
#  Pipeline completo de limpieza / normalización
# ---------------------------------------------------------------------------

def pipeline_limpieza(contenido: str) -> str:
    """
    Ejecuta el pipeline completo de limpieza de contenido generado:
    1. Limpiar HTML
    2. Asegurar que haya tablas
    3. Validar orden de columnas
    4. Forzar contenido suelto dentro de tablas
    """
    if not contenido:
        return contenido

    contenido = limpiar_html(contenido)
    contenido = asegurar_tabla(contenido)
    contenido = validar_orden_columnas(contenido)
    contenido = forzar_contenido_en_tabla(contenido)
    return contenido


# ---------------------------------------------------------------------------
#  Extracción de información de tablas
# ---------------------------------------------------------------------------

def extraer_valor_celda(contenido: str, nombre_item: str) -> Optional[str]:
    """
    Extrae el valor de la celda CONTENIDO para un ITEM dado.
    Busca en tablas | ITEM | CONTENIDO | por nombre_item (case-insensitive).
    """
    if not contenido:
        return None

    for linea in contenido.split('\n'):
        if '|' not in linea:
            continue
        partes = linea.split('|')
        if len(partes) >= 3:
            item = partes[1].strip().replace('**', '').strip().upper()
            if nombre_item.upper() in item:
                valor = partes[2].strip()
                valor = re.sub(r'<[^>]+>', '', valor)
                valor = re.sub(r'\*\*', '', valor)
                return valor.strip() if valor.strip() else None
    return None


def extraer_titulos_sesiones(contenido: str) -> List[str]:
    """
    Extrae los títulos de sesiones de aprendizaje del contenido.
    Busca patrones "Sesión N: título" en cualquier parte del contenido.
    """
    if not contenido:
        return []

    matches = re.findall(
        r'Sesi[oó]n\s+\d+[:\-]\s*([^\n\.]+)', contenido, re.IGNORECASE
    )
    titulos = []
    for m in matches:
        t = re.sub(r'<[^>]+>', '', m).replace('**', '').strip()
        # Cortar en separadores de metadatos
        for sep in [', actividades', ', desempeños', ', tiempo', ', recursos',
                    '; actividades', '; desempeños']:
            if sep in t.lower():
                t = t[:t.lower().index(sep)].strip()
                break
        t = t.rstrip('.,;')
        if t and len(t) > 5:
            titulos.append(t)
    return titulos
