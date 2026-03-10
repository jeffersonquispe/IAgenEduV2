import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.app import crear_documento_profesional, DOCX_OK

if not DOCX_OK:
    print("DOCX IS NOT OK")
else:
    print("DOCX is ready. Generating test document...")
    contenido = """
# Unidad Didáctica de Prueba

Esta es una prueba de exportación.

| ITEM | CONTENIDO |
|---|---|
| SITUACIÓN SIGNIFICATIVA | Esta es una situación significativa larga que se pondrá en la tabla para probar si el wrap o el parser funcionan bien. |
| COMPETENCIA | Resuelve problemas de cantidad |

| Valores Priorizados | Valores Operativos | Enfoques Transversales | Comportamientos Observables |
|---|---|---|---|
| Respeto | Escuchar | Enfoque de derechos | Escucha a sus compañeros |
| Responsabilidad | Cumplir tareas | Orientación al bien común | Entrega trabajos a tiempo |

## Secuencia de Sesiones
1. Sesión 1
2. Sesión 2
"""
    doc_bytes = crear_documento_profesional(contenido, "Unidad Didáctica de Prueba", "Secundaria")
    
    with open('/tmp/test_export.docx', 'wb') as f:
        f.write(doc_bytes)
        print("Document generated at /tmp/test_export.docx")
