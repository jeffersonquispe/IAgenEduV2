from fpdf import FPDF
from fpdf.fonts import FontFace
from datetime import datetime
import os

from .markdown_table import parse_markdown_table

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_family = _registrar_fuente_unicode(self)

    def header(self):
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


def _render_tabla_con_fallback(pdf: EDUGeneratorPDF, tabla: list):
    """Dibuja la tabla con fpdf2; si una fila no cabe en una página ni con fuente
    reducida (contenido inusualmente largo), cae a texto plano en vez de que
    la exportación entera falle con un 500."""
    tamano_original = int(pdf.font_size_pt)
    for tamano in (10, 8, 7):
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
        pdf.cell(0, 10, section_title.replace("_", " ").upper(), 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(pdf.font_family, '', 10)

        tabla = parse_markdown_table(str(content))
        if tabla:
            _render_tabla_con_fallback(pdf, tabla)
        else:
            pdf.multi_cell(0, 6, str(content))

        pdf.ln(5)
        pdf.set_font(pdf.font_family, 'B', 12)


def generar_pdf_unidad(data: dict, output_path: str):
    pdf = EDUGeneratorPDF()
    _render_documento(pdf, data, "Unidad Didáctica")
    pdf.output(output_path)
    return output_path


def generar_pdf_sesion(data: dict, output_path: str):
    pdf = EDUGeneratorPDF()
    _render_documento(pdf, data, "Sesión de Aprendizaje")
    pdf.output(output_path)
    return output_path
