"""Lectura segura de la columna `control_documentario` del perfil institucional (HU-47).

La columna se declara diferida (`deferred`) para que el perfil se pueda leer aunque todavía no se
haya aplicado la migración 20261009_institution_control_documentario.sql. Pero leerla cuando no
existe produce un error de base de datos, y en PostgreSQL un error ABORTA la transacción en curso:
toda operación posterior (p. ej. actualizar las estadísticas de exportación y hacer commit) falla
con "current transaction is aborted" y la petición termina en HTTP 500.

Por eso la lectura se hace dentro de un SAVEPOINT: si falla, solo se deshace ese tramo y la
transacción de la petición sigue sana. (SQLite no aborta la transacción tras un error, así que
una prueba con SQLite no detecta este problema.)
"""
import logging
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

logger = logging.getLogger(__name__)


def proteger_control(db: Session, perfil: Any) -> None:
    """Carga `perfil.control_documentario`; si no se puede leer, lo deja en None sin dañar la sesión."""
    if perfil is None:
        return
    try:
        with db.begin_nested():            # SAVEPOINT: un fallo aquí no aborta la transacción exterior
            perfil.control_documentario    # dispara la carga de la columna diferida
    except Exception as e:
        logger.warning("[Perfil] control_documentario no disponible (¿falta la migración?): %s",
                       str(e).split("\n")[0][:160])
        try:
            set_committed_value(perfil, "control_documentario", None)
        except Exception:
            pass     # no es una instancia mapeada (p. ej. un doble de pruebas): no hay nada que fijar
