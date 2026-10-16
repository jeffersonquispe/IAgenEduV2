from fpdf import FPDF
from fpdf.fonts import FontFace
from datetime import datetime
import math
import os
import re

from .campos_documento import ETIQUETAS_SECCION
from .markdown_table import aplanar_tabla_degenerada, parse_markdown_table

_NEGRITA = re.compile(r"\*\*(.+?)\*\*", re.S)


def _limpiar_inline(texto: str) -> str:
    """El PDF no interpreta Markdown: quita los marcadores de **negrita** (incluso desbalanceados)."""
    return _NEGRITA.sub(r"\1", str(texto)).replace("**", "")

# Helvetica (fpdf2's built-in font) only supports Latin-1 and breaks on
# generated content with accents/ñ. Register a Unicode TTF instead.
_FONT_FAMILY = "helvetica"
_UNICODE_FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\ariali.ttf"),
]


def _registrar_fuente_unicode(pdf: FPDF) -> str:
    for regular, bold, italic in _UNICODE_FONT_CANDIDATES:
        if os.path.exists(regular):
            pdf.add_font("AppFont", "", regular)
            if os.path.exists(bold):
                pdf.add_font("AppFont", "B", bold)
            if os.path.exists(italic):
                pdf.add_font("AppFont", "I", italic)
            return "AppFont"
    return _FONT_FAMILY


class EDUGeneratorPDF(FPDF):
    def __init__(self, *args, control=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_family = _registrar_fuente_unicode(self)
        # HU-47: datos del encabezado de control documentario (ver core/control_documentario.py).
        self.control = control
        if control:
            self.alias_nb_pages("{nb}")      # para "Páginas: N de M"

    def _texto_que_cabe(self, texto: str, ancho: float) -> str:
        """Recorta el texto con '…' para que no se desborde de su celda."""
        if self.get_string_width(texto) <= ancho:
            return texto
        while texto and self.get_string_width(texto + "…") > ancho:
            texto = texto[:-1]
        return texto.rstrip() + "…"

    def _header_control_documentario(self):
        c = self.control
        ancho_total = self.w - self.l_margin - self.r_margin
        alto = 6
        filas = [
            [("Documento", c["documento"], 0.36), ("Institución", c["institucion"], 0.34),
             ("Versión", c["version"], 0.12), ("Páginas", f"{self.page_no()} de {{nb}}", 0.18)],
            [("Aprobado por", c["aprobado_por"], 0.32), ("Fecha", c["fecha_aprobacion"], 0.18),
             ("Revisado por", c["revisado_por"], 0.32), ("Fecha", c["fecha_revision"], 0.18)],
        ]
        for fila in filas:
            x, y = self.l_margin, self.get_y()
            for etiqueta, valor, proporcion in fila:
                w = ancho_total * proporcion
                self.set_xy(x, y)
                self.cell(w, alto, "", border=1)                      # marco de la celda
                self.set_xy(x + 1, y)
                self.set_font(self.font_family, 'B', 7)
                et = f"{etiqueta}: "
                ancho_et = self.get_string_width(et)
                self.cell(ancho_et, alto, et)
                self.set_font(self.font_family, '', 7)
                self.cell(w - ancho_et - 2, alto, self._texto_que_cabe(str(valor or ""), w - ancho_et - 2))
                x += w
            self.set_xy(self.l_margin, y + alto)
        self.ln(4)

    def header(self):
        if self.control:
            self._header_control_documentario()
            return
        self.set_font(self.font_family, 'B', 12)
        self.cell(0, 10, 'PLANIFICACIÓN EDUCATIVA AI - MINEDU', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} - Generado el {datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')


def _render_tabla_como_texto(pdf: EDUGeneratorPDF, tabla: list):
    """Fallback cuando la tabla no cabe ni siquiera en fuente reducida: una entrada por fila."""
    header = tabla[0]
    for fila in tabla[1:]:
        partes = [f"{header[i]}: {celda}" for i, celda in enumerate(fila) if celda]
        pdf.multi_cell(0, 6, " | ".join(partes))
        pdf.ln(2)


_MARGEN_VERTICAL_RESERVADO = 30   # mm: encabezado y pie de cada página


def _altura_fila(pdf: EDUGeneratorPDF, fila: list, ancho_col: float, tamano: int) -> float:
    """Estima (mm) lo que ocupa una fila con el texto de sus celdas ajustado al ancho de columna."""
    pdf.set_font(pdf.font_family, '', tamano)
    ancho_texto = max(ancho_col - 2, 1)
    lineas = 1
    for celda in fila:
        n = sum(max(1, math.ceil(pdf.get_string_width(p) / ancho_texto)) for p in str(celda).split("\n"))
        lineas = max(lineas, n)
    return lineas * tamano * 0.3528 * 1.25 + 2


def _tabla_cabe(pdf: EDUGeneratorPDF, tabla: list, tamano: int) -> bool:
    """False si alguna fila es más alta que una página: fpdf2 no parte filas, y el intento dejaría
    páginas en blanco (con solo el encabezado) antes de fallar."""
    ancho_col = pdf.epw / max(len(f) for f in tabla)
    limite = pdf.eph - _MARGEN_VERTICAL_RESERVADO
    return all(_altura_fila(pdf, fila, ancho_col, tamano) <= limite for fila in tabla)


def _revertir_paginas(pdf: EDUGeneratorPDF, pagina: int, y: float):
    """Descarta las páginas que un intento fallido de dibujar la tabla haya agregado."""
    pages = getattr(pdf, "pages", None)
    if isinstance(pages, dict):
        for n in sorted((n for n in pages if n > pagina), reverse=True):
            del pages[n]
        pdf.page = pagina
        pdf.set_y(y)


def _render_tabla_con_fallback(pdf: EDUGeneratorPDF, tabla: list):
    """Dibuja la tabla con fpdf2; si una fila no cabe en una página ni con fuente
    reducida (contenido inusualmente largo), cae a texto plano en vez de que
    la exportación entera falle con un 500."""
    tamano_original = int(pdf.font_size_pt)
    pagina, y = pdf.page, pdf.get_y()
    for tamano in (10, 8, 7):
        if not _tabla_cabe(pdf, tabla, tamano):
            continue
        try:
            pdf.set_font(pdf.font_family, '', tamano)
            # pdf.table() es un context manager: sin `with` no dibuja nada (no lanza error).
            with pdf.table(
                rows=tabla,
                headings_style=FontFace(family=pdf.font_family, emphasis="B", fill_color=(99, 102, 241)),
                text_align="LEFT",
            ):
                pass
            pdf.set_font(pdf.font_family, '', tamano_original)
            return
        except Exception:
            _revertir_paginas(pdf, pagina, y)
            continue
    pdf.set_font(pdf.font_family, '', tamano_original)
    _render_tabla_como_texto(pdf, tabla)


def _render_documento(pdf: EDUGeneratorPDF, data: dict, titulo_default: str):
    pdf.add_page()
    pdf.set_font(pdf.font_family, 'B', 16)

    titulo = data.get("titulo", titulo_default)
    pdf.multi_cell(0, 10, titulo.upper(), 0, 'C')
    pdf.ln(10)

    pdf.set_font(pdf.font_family, 'B', 12)
    for section_title, content in data.items():
        if section_title == "titulo":
            continue

        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 10, ETIQUETAS_SECCION.get(section_title, section_title.replace("_", " ").capitalize()).upper(), 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(pdf.font_family, '', 10)

        tabla = parse_markdown_table(str(content))
        if tabla:
            _render_tabla_con_fallback(pdf, [[_limpiar_inline(c) for c in fila] for fila in tabla])
        else:
            plano = aplanar_tabla_degenerada(str(content))
            pdf.multi_cell(0, 6, _limpiar_inline(plano if plano is not None else content))

        pdf.ln(5)
        pdf.set_font(pdf.font_family, 'B', 12)


def generar_pdf_unidad(data: dict, output_path: str, control=None):
    pdf = EDUGeneratorPDF(control=control)
    _render_documento(pdf, data, "Unidad Didáctica")
    pdf.output(output_path)
    return output_path


def generar_pdf_sesion(data: dict, output_path: str, control=None):
    pdf = EDUGeneratorPDF(control=control)
    _render_documento(pdf, data, "Sesión de Aprendizaje")
    pdf.output(output_path)
    return output_path
