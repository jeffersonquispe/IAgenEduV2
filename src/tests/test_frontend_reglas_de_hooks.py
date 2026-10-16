"""Reglas de los hooks de React, verificadas sin ejecutar el navegador.

Regla: todos los hooks de un componente deben ejecutarse en CADA render, siempre en el mismo
orden. Un hook declarado después de un `return` anticipado (`if (!isOpen) return null`) solo
se ejecuta cuando el componente no sale antes; al pasar de cerrado a abierto, React cuenta un
hook de más y lanza "Rendered more hooks than during the previous render" (así dejó de abrirse
el wizard de generación). El build de Vite no lo detecta: solo falla al renderizar.
"""
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"

_COMPONENTE = re.compile(r"^(?:export (?:default )?)?function ([A-Z]\w*)\(")
# `return` anticipado al nivel de la función del componente (2 espacios de sangría).
_RETORNO_ANTICIPADO = re.compile(r"^  if \(.*\) return\b")
# Hook llamado al nivel de la función del componente.
_HOOK = re.compile(r"^  (?:(?:const|let|var)\s+.*?=\s*)?(use[A-Z]\w*)\(")


def hooks_despues_de_un_retorno_anticipado(codigo: str):
    """[(componente, linea_del_return, linea_del_hook, hook)] de los hooks mal ubicados."""
    lineas = codigo.splitlines()
    inicios = [(i, m.group(1)) for i, l in enumerate(lineas) if (m := _COMPONENTE.match(l))]
    problemas = []
    for k, (inicio, nombre) in enumerate(inicios):
        fin = inicios[k + 1][0] if k + 1 < len(inicios) else len(lineas)
        retorno = None
        for i in range(inicio + 1, fin):
            if retorno is None:
                if _RETORNO_ANTICIPADO.match(lineas[i]):
                    retorno = i
            elif (m := _HOOK.match(lineas[i])):
                problemas.append((nombre, retorno + 1, i + 1, m.group(1)))
    return problemas


ARCHIVOS = sorted(SRC.rglob("*.jsx"))


def test_se_encuentran_los_componentes_del_frontend():
    assert len(ARCHIVOS) >= 8, "no se encontraron los archivos .jsx (¿cambió la ruta del frontend?)"


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.relative_to(SRC).as_posix())
def test_ningun_hook_va_despues_de_un_return_anticipado(archivo):
    problemas = hooks_despues_de_un_retorno_anticipado(archivo.read_text(encoding="utf-8"))
    assert not problemas, "; ".join(
        f"{c}: el hook {h} (línea {lh}) va después del return anticipado de la línea {lr}; "
        f"muévelo antes de ese return" for c, lr, lh, h in problemas)


# --- El detector detecta lo que debe (no pasa en vacío) ---

CODIGO_ROTO = """\
export default function Wizard({ isOpen }) {
  const [a, setA] = useState(1)
  useEffect(() => {}, [])

  if (!isOpen) return null

  useEffect(() => () => {}, [])
  return <div />
}
"""

CODIGO_CORRECTO = """\
export default function Wizard({ isOpen }) {
  const [a, setA] = useState(1)
  useEffect(() => {}, [])
  useEffect(() => () => {}, [])

  if (!isOpen) return null

  const alCerrar = () => setA(2)
  return <div onClick={alCerrar} />
}
"""


def test_el_detector_encuentra_un_hook_despues_del_return_anticipado():
    assert hooks_despues_de_un_retorno_anticipado(CODIGO_ROTO) == [("Wizard", 5, 7, "useEffect")]


def test_el_detector_acepta_los_hooks_antes_del_return_anticipado():
    assert hooks_despues_de_un_retorno_anticipado(CODIGO_CORRECTO) == []


def test_el_detector_no_confunde_componentes_ni_funciones_internas():
    codigo = CODIGO_CORRECTO + """
function Auxiliar({ x }) {
  if (!x) return null
  return <span />
}
function Otro() {
  const [b, setB] = useState(0)
  return <p />
}
"""
    assert hooks_despues_de_un_retorno_anticipado(codigo) == []


def test_el_wizard_real_tiene_su_hook_de_limpieza_antes_del_return_anticipado():
    codigo = (SRC / "components" / "GenerationWizard.jsx").read_text(encoding="utf-8")
    assert codigo.index("useEffect(() => () => { ejecucion.current++ }, [])") < codigo.index("if (!isOpen) return null")
