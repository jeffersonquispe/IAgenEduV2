# src/validators/structure_validator.py
"""
Valida que el contenido generado tenga la estructura esperada:
secciones requeridas, formato de tabla correcto, orden de columnas, etc.
"""
import re
import logging
import unicodedata
from difflib import SequenceMatcher
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
        # El prompt nunca produjo una sección "INSTRUMENTOS" (pide "Instrumento de evaluación" dentro de los
        # propósitos y una columna "Instrumento"). Exigir el plural hacía fallar TODA Unidad con un error
        # crítico y disparaba siempre el pase de corrección. "INSTRUMENTO" acepta ambas formas.
        "INSTRUMENTO",
        "VALORES",
        "SECUENCIA",
        "MATERIALES",  # HU-40: materiales básicos (docente/estudiante)
    ]

    SECCIONES_SESION = [
        "DATOS INFORMATIVOS",
        "SITUACIÓN SIGNIFICATIVA",
        "RETO",  # HU-41: pregunta-reto explícita, separada de la situación significativa
        "PROPÓSITOS",
        "SECUENCIA DIDÁCTICA",
        "MATERIALES",
    ]

    def validar_unidad_didactica(self, contenido: str, num_sesiones: Optional[int] = None) -> ValidationReport:
        """Valida estructura de una unidad didáctica.

        `num_sesiones`, si se provee, habilita la verificación HU-39 de que
        la cantidad de criterios de evaluación coincida con la cantidad de
        sesiones solicitadas.
        """
        reporte = ValidationReport()

        if not contenido or len(contenido.strip()) < 100:
            reporte.errores.append(ValidationError(
                tipo="CRITICO",
                categoria="ESTRUCTURA",
                mensaje="Contenido vacío o demasiado corto",
            ))
            return reporte

        from ..core.matriz_axiologica import tiene_matriz  # import local: ver _validar_temas_no_repetidos

        # HU-42: la matriz axiológica (tabla Valor | Enfoques | Comportamientos |
        # Instrumento) cumple la sección de valores; el formato de texto anterior
        # (fila "VALORES Y ENFOQUES TRANSVERSALES") sigue siendo válido.
        secciones = self.SECCIONES_UNIDAD
        if tiene_matriz(contenido):
            secciones = [s for s in secciones if s != "VALORES"]

        self._validar_tabla_presente(contenido, reporte)
        self._validar_secciones(contenido, secciones, reporte)
        self._validar_orden_columnas(contenido, reporte)
        self._validar_contenido_fuera_tabla(contenido, reporte)
        self._validar_html_residual(contenido, reporte)
        self._validar_matriz_axiologica(contenido, reporte)
        self._validar_criterios_vs_sesiones(contenido, num_sesiones, reporte)
        self._validar_filas_rubrica_vs_sesiones(contenido, num_sesiones, reporte)
        self._validar_temas_no_repetidos(contenido, reporte)

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

    def validar_contra_plantilla(self, contenido: str, esquema: dict) -> ValidationReport:
        """HU-49: cuando el docente tiene una plantilla institucional activa
        (HU-48), valida contra las tablas/encabezados de ESA plantilla en vez
        de las constantes SECCIONES_UNIDAD/SECCIONES_SESION fijas — la
        plantilla del docente es la fuente de verdad de la estructura."""
        reporte = ValidationReport()
        if not contenido or len(contenido.strip()) < 100:
            reporte.errores.append(ValidationError(
                tipo="CRITICO", categoria="ESTRUCTURA",
                mensaje="Contenido vacío o demasiado corto",
            ))
            return reporte

        self._validar_tabla_presente(contenido, reporte)
        contenido_upper = contenido.upper()
        for tabla in esquema.get("tablas", []):
            for header in tabla.get("headers", []):
                h = (header or "").strip()
                if h and h.upper() not in contenido_upper:
                    reporte.errores.append(ValidationError(
                        tipo="ADVERTENCIA",
                        categoria="ESTRUCTURA",
                        mensaje=f"No se encontró en el contenido la columna de la plantilla: {h}",
                    ))
        self._validar_html_residual(contenido, reporte)
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
        # El prompt pide separar el contenido de una celda con saltos de línea reales. Una fila que
        # empieza con '|' y todavía no cerró con '|' sigue abierta: las líneas que vienen después
        # (hasta la que cierra la fila) son parte de esa celda, no contenido fuera de la tabla.
        celda_abierta = False

        for linea in lineas:
            s = linea.strip()
            if celda_abierta and not s.startswith('|'):
                if s.endswith('|'):
                    celda_abierta = False
                continue
            if '|' in s and s.count('|') >= 2:
                en_tabla = True
                celda_abierta = s.startswith('|') and not s.endswith('|')
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

    def _validar_criterios_vs_sesiones(
        self, contenido: str, num_sesiones: Optional[int], reporte: ValidationReport
    ):
        """HU-39: la cantidad de criterios de evaluación (uno por sesión, marcados
        en el prompt como "Criterio de evaluación:" en singular, dentro de cada
        fila de SECUENCIA DE SESIONES) debe coincidir con num_sesiones. Se
        distingue de "Criterios de evaluación:" (plural, en PROPÓSITOS DE
        APRENDIZAJE) con un lookahead negativo sobre la "s"."""
        if not num_sesiones:
            return
        ocurrencias = len(re.findall(r"Criterio(?!s)\s+de\s+evaluaci[oó]n", contenido, re.IGNORECASE))
        if ocurrencias and ocurrencias != num_sesiones:
            reporte.errores.append(ValidationError(
                tipo="ADVERTENCIA",
                categoria="CONTENIDO",
                mensaje=(
                    f"Se esperaban {num_sesiones} criterios de evaluación (uno por sesión), "
                    f"pero se detectaron {ocurrencias} en el contenido generado."
                ),
                seccion="SECUENCIA DE SESIONES",
            ))

    # Umbral de similitud (0-1) a partir del cual dos títulos de sesión se
    # consideran el mismo tema. 0.85 atrapa variantes menores ("Fracciones
    # equivalentes" / "Las fracciones equivalentes") sin marcar títulos
    # distintos que solo comparten una palabra.
    UMBRAL_TEMA_REPETIDO = 0.85

    @staticmethod
    def _normalizar_titulo(titulo: str) -> str:
        sin_tildes = unicodedata.normalize("NFD", titulo.lower())
        sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
        return " ".join(re.sub(r"[^a-z0-9 ]+", " ", sin_tildes).split())

    def _validar_temas_no_repetidos(self, contenido: str, reporte: ValidationReport):
        """HU-29 (fase 1): dos sesiones de la misma Unidad no deben tratar el
        mismo tema. Compara los títulos de la SECUENCIA DE SESIONES, idénticos
        o muy similares tras normalizar mayúsculas, tildes y signos."""
        from ..utils.table_utils import extraer_sesiones_numeradas

        sesiones = extraer_sesiones_numeradas(contenido)
        if len(sesiones) < 2:
            return
        normalizados = {n: self._normalizar_titulo(t) for n, t in sesiones.items()}
        numeros = sorted(normalizados)
        for i, a in enumerate(numeros):
            for b in numeros[i + 1:]:
                ta, tb = normalizados[a], normalizados[b]
                if not ta or not tb:
                    continue
                if ta == tb or SequenceMatcher(None, ta, tb).ratio() >= self.UMBRAL_TEMA_REPETIDO:
                    reporte.errores.append(ValidationError(
                        tipo="ADVERTENCIA",
                        categoria="CONTENIDO",
                        mensaje=(
                            f"Las sesiones {a} y {b} tratan el mismo tema: "
                            f"\"{sesiones[a]}\" / \"{sesiones[b]}\"."
                        ),
                        seccion="SECUENCIA DE SESIONES",
                    ))

    def _validar_matriz_axiologica(self, contenido: str, reporte: ValidationReport):
        """HU-42: si hay matriz axiológica, debe tener al menos una fila de datos
        y ninguna celda de comportamiento/instrumento sin completar."""
        from ..core.matriz_axiologica import contar_filas_matriz, extraer_matriz

        tabla = extraer_matriz(contenido)
        if not tabla:
            return
        if contar_filas_matriz(contenido) == 0:
            reporte.errores.append(ValidationError(
                tipo="ADVERTENCIA", categoria="CONTENIDO",
                mensaje="La matriz axiológica no tiene filas de valores.",
                seccion="MATRIZ AXIOLÓGICA",
            ))
        elif "[COMPLETAR" in tabla.upper():
            reporte.errores.append(ValidationError(
                tipo="ADVERTENCIA", categoria="CONTENIDO",
                mensaje="La matriz axiológica conserva campos sin completar ([COMPLETAR]).",
                seccion="MATRIZ AXIOLÓGICA",
            ))

    def _validar_filas_rubrica_vs_sesiones(
        self, contenido: str, num_sesiones: Optional[int], reporte: ValidationReport
    ):
        """HU-39: la rúbrica analítica (encabezado "Criterio | C ... | AD ...")
        debe tener exactamente una fila por sesión."""
        if not num_sesiones:
            return
        lineas = contenido.split('\n')
        inicio = None
        for i, linea in enumerate(lineas):
            s = linea.strip().upper()
            if s.startswith('|') and 'CRITERIO' in s and 'INICIO' in s and 'DESTACADO' in s:
                inicio = i
                break
        if inicio is None:
            return
        filas = 0
        for linea in lineas[inicio + 1:]:
            s = linea.strip()
            if not s.startswith('|'):
                if not s:
                    break
                continue
            if re.fullmatch(r'[|\s:\-]+', s):
                continue  # separador de encabezado
            filas += 1
        if filas != num_sesiones:
            reporte.errores.append(ValidationError(
                tipo="ADVERTENCIA",
                categoria="CONTENIDO",
                mensaje=(
                    f"La rúbrica analítica tiene {filas} filas, pero se esperaban "
                    f"{num_sesiones} (una por sesión)."
                ),
                seccion="RÚBRICA ANALÍTICA",
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
