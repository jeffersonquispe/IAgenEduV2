from fpdf import FPDF
from datetime import datetime
import os

class EDUGeneratorPDF(FPDF):
    def header(self):
        # Logo placeholder or Institution Title
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'PLANIFICACIÓN EDUCATIVA AI - MINEDU', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()} - Generado el {datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

def generar_pdf_unidad(data: dict, output_path: str):
    pdf = EDUGeneratorPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    
    # Título de la Unidad
    titulo = data.get("titulo", "Unidad Didáctica")
    pdf.multi_cell(0, 10, titulo.upper(), 0, 'C')
    pdf.ln(10)
    
    # Secciones
    pdf.set_font("helvetica", 'B', 12)
    for section_title, content in data.items():
        if section_title == "titulo": continue
        
        pdf.set_text_color(99, 102, 241) # Primary color
        pdf.cell(0, 10, section_title.replace("_", " ").upper(), 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", '', 10)
        pdf.multi_cell(0, 6, str(content))
        pdf.ln(5)
        pdf.set_font("helvetica", 'B', 12)
        
    pdf.output(output_path)
    return output_path

def generar_pdf_sesion(data: dict, output_path: str):
    # Similar structure to unidad but adapted for sessions
    pdf = EDUGeneratorPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    
    titulo = data.get("titulo", "Sesión de Aprendizaje")
    pdf.multi_cell(0, 10, titulo.upper(), 0, 'C')
    pdf.ln(10)
    
    pdf.set_font("helvetica", 'B', 12)
    for section_title, content in data.items():
        if section_title == "titulo": continue
        
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 10, section_title.replace("_", " ").upper(), 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", '', 10)
        pdf.multi_cell(0, 6, str(content))
        pdf.ln(5)
        pdf.set_font("helvetica", 'B', 12)
        
    pdf.output(output_path)
    return output_path
