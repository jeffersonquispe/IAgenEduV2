# src/core/prompt_manager.py
"""
Gestor centralizado de prompts.
Los prompts se almacenan en archivos .md en src/prompts/ con variables {placeholder}.
"""
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptManager:
    """
    Carga y renderiza prompts desde archivos .md en la carpeta prompts/.

    Uso:
        pm = PromptManager()
        prompt = pm.cargar("unidad_didactica",
                           area_curricular="Ciencia y Tecnología",
                           grado=3)
    """

    def __init__(self, directorio: Path = None):
        self.directorio = directorio or PROMPTS_DIR
        self._cache: Dict[str, str] = {}

    def cargar(self, nombre: str, **variables) -> str:
        """
        Carga un prompt por nombre y sustituye las variables.

        Args:
            nombre: Nombre base del archivo (sin extensión .md)
            **variables: Variables a sustituir en el template

        Returns:
            Prompt renderizado con las variables sustituidas
        """
        template = self._leer_template(nombre)
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Variable faltante en prompt '{nombre}': {e}")
            # Sustituir parcialmente: las variables no encontradas se dejan como {nombre}
            for key, value in variables.items():
                template = template.replace('{' + key + '}', str(value))
            return template

    def cargar_seccion(self, nombre: str, seccion: str, **variables) -> str:
        """
        Carga solo una sección específica del prompt (delimitada por ## headers).

        Args:
            nombre: Nombre base del archivo
            seccion: Título de la sección a extraer (case-insensitive)
            **variables: Variables a sustituir

        Returns:
            Contenido de la sección, renderizado
        """
        template = self._leer_template(nombre)
        secciones = self._parsear_secciones(template)

        seccion_upper = seccion.upper()
        for titulo, contenido in secciones.items():
            if seccion_upper in titulo.upper():
                try:
                    return contenido.format(**variables)
                except KeyError:
                    for key, value in variables.items():
                        contenido = contenido.replace('{' + key + '}', str(value))
                    return contenido

        logger.warning(f"Sección '{seccion}' no encontrada en prompt '{nombre}'")
        return ""

    def listar_prompts(self) -> list:
        """Lista todos los prompts disponibles."""
        if not self.directorio.exists():
            return []
        return [f.stem for f in self.directorio.glob("*.md")]

    def _leer_template(self, nombre: str) -> str:
        """Lee y cachea un template de prompt."""
        if nombre in self._cache:
            return self._cache[nombre]

        path = self.directorio / f"{nombre}.md"
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt '{nombre}' no encontrado en {self.directorio}"
            )

        template = path.read_text(encoding='utf-8')
        self._cache[nombre] = template
        return template

    def _parsear_secciones(self, template: str) -> Dict[str, str]:
        """Parsea un template en secciones por ## headers."""
        secciones = {}
        seccion_actual = "_intro"
        buffer = []

        for linea in template.split('\n'):
            if linea.startswith('## '):
                if buffer:
                    secciones[seccion_actual] = '\n'.join(buffer).strip()
                seccion_actual = linea[3:].strip()
                buffer = []
            else:
                buffer.append(linea)

        if buffer:
            secciones[seccion_actual] = '\n'.join(buffer).strip()

        return secciones

    def invalidar_cache(self):
        """Limpia la caché de templates (útil durante desarrollo)."""
        self._cache.clear()


# Singleton
_default_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Obtiene la instancia singleton del PromptManager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = PromptManager()
    return _default_manager
