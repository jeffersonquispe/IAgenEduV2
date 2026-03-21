# src/validators/structure_validator.py
"""
Valida que el contenido generado tenga la estructura esperada:
secciones requeridas, formato de tabla correcto, orden de columnas, etc.
"""
import re
import logging
from typing import List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Un error o advertencia de validación."""
    tipo: str       # "CRITICO", "ADVERTENCIA", "INFO"
    categoria: str  # "ESTRUCTURA", "FORMATO", "CONTENIDO"
    mensaje: str
    seccion: str = ""  # Sección donde ocurre el error


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    errores: List[ValidationError] = field(default_factory=list)

    @property
    def tiene_errores_criticos(self) -> bool:
        return any(e.tipo == "CRITICO" for e in self.errores)

    @property
    def tiene_advertencias(self) -> bool:
        return any(e.tipo == "ADVERTENCIA" for e in self.errores)

    @property
    def es_valido(self) -> bool:
        return not self.tiene_errores_criticos

    @property
    def puntaje(self) -> int:
        """Puntaje de 0-100 basado en errores encontrados."""
        base = 100
        for e in self.errores:
            if e.tipo == "CRITICO":
                base -= 25
            elif e.tipo == "ADVERTENCIA":
                base -= 10
            else:
                base -= 2
        return max(0, base)

    def resumen(self) -> str:
        criticos = sum(1 for e in self.errores if e.tipo == "CRITICO")
        advertencias = sum(1 for e in self.errores if e.tipo == "ADVERTENCIA")
        return (
            f"Validación: {self.puntaje}/100 | "
            f"Críticos: {criticos} | Advertencias: {advertencias} | "
            f"{'✅ APROBADO' if self.es_valido else '❌ RECHAZADO'}"
        )


class StructureValidator:
    """Valida la estructura del contenido generado."""

    # Secciones requeridas por tipo de documento
    SECCIONES_UNIDAD = [
        "TÍTULO",
        "SITUACIÓN SIGNIFICATIVA",
        "PROPÓSITOS",
        "EVIDENCIAS",
        "INSTRUMENTOS",
        "VALORES",
        "SECUENCIA",
    ]

    SECCIONES_SESION = [
        "DATOS INFORMATIVOS",
        "SITUACIÓN SIGNIFICATIVA",
        "PROPÓSITOS",
        "SECUENCIA DIDÁCTICA",
        "MATERIALES",
    ]

    def validar_unidad_didactica(self, contenido: str) -> ValidationReport:
        """Valida estructura de una unidad didáctica."""
        reporte = ValidationReport()

        if not contenido or len(contenido.strip()) < 100:
            reporte.errores.append(ValidationError(
                tipo="CRITICO",
                categoria="ESTRUCTURA",
                mensaje="Contenido vacío o demasiado corto",
            ))
            return reporte

        self._validar_tabla_presente(contenido, reporte)
        self._validar_secciones(contenido, self.SECCIONES_UNIDAD, reporte)
        self._validar_orden_columnas(contenido, reporte)
        self._validar_contenido_fuera_tabla(contenido, reporte)
        self._validar_html_residual(contenido, reporte)

        logger.info(f"[Validator] Unidad didáctica: {reporte.resumen()}")
        return reporte

    def validar_sesion_aprendizaje(self, contenido: str) -> ValidationReport:
        """Valida estructura de una sesión de aprendizaje."""
        reporte = ValidationReport()

        if not contenido or len(contenido.strip()) < 100:
            reporte.errores.append(ValidationError(
                tipo="CRITICO",
                categoria="ESTRUCTURA",
                mensaje="Contenido vacío o demasiado corto",
            ))
            return reporte

        self._validar_tabla_presente(contenido, reporte)
        self._validar_secciones(contenido, self.SECCIONES_SESION, reporte)
        self._validar_orden_columnas(contenido, reporte)
        self._validar_contenido_fuera_tabla(contenido, reporte)
        self._validar_html_residual(contenido, reporte)
        self._validar_secuencia_didactica(contenido, reporte)

        logger.info(f"[Validator] Sesión: {reporte.resumen()}")
        return reporte

    # --- Validaciones individuales ---

    def _validar_tabla_presente(self, contenido: str, reporte: ValidationReport):
        """Verifica que hay al menos una tabla Markdown."""
        tiene_tabla = (
            '|' in contenido and
            contenido.count('|') >= 4  # Al menos 2 filas con 2 columnas
        )
        if not tiene_tabla:
            reporte.errores.append(ValidationError(
                tipo="CRITICO",
                categoria="FORMATO",
                mensaje="No se detectó ninguna tabla Markdown en el contenido",
            ))

    def _validar_secciones(
        self, contenido: str, secciones: List[str], reporte: ValidationReport
    ):
        """Verifica que todas las secciones requeridas estén presentes."""
        contenido_upper = contenido.upper()
        for seccion in secciones:
            if seccion.upper() not in contenido_upper:
                reporte.errores.append(ValidationError(
                    tipo="CRITICO",
                    categoria="ESTRUCTURA",
                    mensaje=f"Falta la sección requerida: {seccion}",
                    seccion=seccion,
                ))

    def _validar_orden_columnas(self, contenido: str, reporte: ValidationReport):
        """Verifica que las columnas ITEM | CONTENIDO estén en orden correcto."""
        for linea in contenido.split('\n'):
            s = linea.strip().upper()
            if 'CONTENIDO' in s and 'ITEM' in s and '|' in s:
                partes = [p.strip() for p in s.split('|')]
                if len(partes) >= 3:
                    # Si CONTENIDO aparece antes de ITEM, está invertido
                    pos_contenido = s.index('CONTENIDO')
                    pos_item = s.index('ITEM')
                    if pos_contenido < pos_item:
                        reporte.errores.append(ValidationError(
                            tipo="ADVERTENCIA",
                            categoria="FORMATO",
                            mensaje="Columnas invertidas: CONTENIDO | ITEM (debería ser ITEM | CONTENIDO)",
                        ))
                        break

    def _validar_contenido_fuera_tabla(self, contenido: str, reporte: ValidationReport):
        """Detecta contenido significativo fuera de las tablas."""
        lineas = contenido.split('\n')
        en_tabla = False
        lineas_fuera = 0

        for linea in lineas:
            s = linea.strip()
            if '|' in s and s.count('|') >= 2:
                en_tabla = True
            elif not s:
                continue
            elif en_tabla and s and '|' not in s:
                # Texto fuera de tabla después de haber empezado una tabla
                lineas_fuera += 1

        if lineas_fuera > 3:
            reporte.errores.append(ValidationError(
                tipo="ADVERTENCIA",
                categoria="FORMATO",
                mensaje=f"Se detectaron {lineas_fuera} líneas de contenido fuera de las tablas",
            ))

    def _validar_html_residual(self, contenido: str, reporte: ValidationReport):
        """Detecta etiquetas HTML que no fueron limpiadas."""
        html_tags = re.findall(r'<(?:br|p|div|span|table|tr|td|th)[^>]*/?>', contenido, re.IGNORECASE)
        if html_tags:
            reporte.errores.append(ValidationError(
                tipo="ADVERTENCIA",
                categoria="FORMATO",
                mensaje=f"Se encontraron {len(html_tags)} etiquetas HTML residuales",
            ))

    def _validar_secuencia_didactica(self, contenido: str, reporte: ValidationReport):
        """Verifica que la secuencia didáctica tenga Inicio, Desarrollo, Cierre."""
        contenido_upper = contenido.upper()
        momentos = ["INICIO", "DESARROLLO", "CIERRE"]
        for momento in momentos:
            # Buscar dentro de la sección de secuencia didáctica
            if momento not in contenido_upper:
                reporte.errores.append(ValidationError(
                    tipo="ADVERTENCIA",
                    categoria="CONTENIDO",
                    mensaje=f"Falta el momento '{momento}' en la secuencia didáctica",
                    seccion="SECUENCIA DIDÁCTICA",
                ))
