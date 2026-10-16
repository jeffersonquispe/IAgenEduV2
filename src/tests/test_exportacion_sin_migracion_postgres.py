"""Exportar con una base a la que le falta la migración de HU-47, con las reglas de PostgreSQL.

Antes: leer la columna inexistente `control_documentario` daba un error que PostgreSQL convierte en
"transacción abortada"; la siguiente escritura (las estadísticas de exportación) fallaba y la
exportación respondía HTTP 500. Con SQLite eso no ocurre (no aborta la transacción tras un error),
por eso las pruebas anteriores no lo detectaron. Aquí la sesión falsa imita a PostgreSQL.
"""
from types import SimpleNamespace

import pytest

from src.api import models
from src.api.routes.export import export_docx, export_pdf
from src.api.services.perfil_control import proteger_control
from src.core.control_documentario import construir_control


class SesionPostgresFalsa:
    """Un error fuera de un SAVEPOINT aborta la transacción: después, todo falla hasta un rollback."""

    def __init__(self, respuestas_de_consulta):
        self.abortada = False
        self.savepoints_abiertos = 0
        self.savepoints_usados = 0
        self.confirmaciones = 0
        self._respuestas = list(respuestas_de_consulta)

    # -- API de Session que usan las rutas --
    def query(self, *_):
        sesion = self
        class _Consulta:
            def filter(self, *a, **k): return self
            def first(self):
                sesion._exigir_sana()
                return sesion._respuestas.pop(0)
        return _Consulta()

    def begin_nested(self):
        sesion = self
        class _Savepoint:
            def __enter__(self):
                sesion._exigir_sana()
                sesion.savepoints_abiertos += 1
                sesion.savepoints_usados += 1
            def __exit__(self, tipo, valor, tb):
                sesion.savepoints_abiertos -= 1
                return False                      # un fallo dentro del savepoint se propaga, pero NO aborta lo exterior
        return _Savepoint()

    def commit(self):
        self._exigir_sana()
        self.confirmaciones += 1

    def rollback(self):
        self.abortada = False

    # -- reglas de PostgreSQL --
    def _exigir_sana(self):
        if self.abortada:
            raise RuntimeError("(psycopg.errors.InFailedSqlTransaction) current transaction is aborted, "
                               "commands ignored until end of transaction block")

    def error_de_base_de_datos(self):
        """Un statement falló: fuera de un SAVEPOINT aborta la transacción entera."""
        if self.savepoints_abiertos == 0:
            self.abortada = True
        raise RuntimeError("(psycopg.errors.UndefinedColumn) column institution_profiles.control_documentario does not exist")


class _ColumnaInexistente:
    """Descriptor que imita la carga de una columna diferida que no existe: dispara el error de PostgreSQL.
    Es un descriptor "no de datos": una vez que `set_committed_value` guarda un valor en la instancia,
    ese valor tiene prioridad y ya no se vuelve a consultar la base."""

    def __init__(self, db):
        self.db = db

    def __get__(self, instancia, clase):
        if instancia is None:
            return self
        self.db.error_de_base_de_datos()


def _perfil(db, monkeypatch):
    """Un InstitutionProfile real (mapeado por SQLAlchemy) cuya columna `control_documentario` no existe en la base."""
    monkeypatch.setattr(models.InstitutionProfile, "control_documentario", _ColumnaInexistente(db))
    return models.InstitutionProfile(nombre_institucion="Colegio Salesiano de Cusco", dre_ugel="UGEL Cusco")


CONTENIDO = {"titulo": "Unidad Didáctica - Comunicación", "situacion_significativa": "Una situación."}


# --- La lectura segura ---

def test_sin_proteccion_leer_la_columna_inexistente_aborta_la_transaccion(monkeypatch):
    """Documenta el defecto original: con este comportamiento la exportación terminaba en 500."""
    db = SesionPostgresFalsa([])
    assert construir_control(_perfil(db, monkeypatch), "unidad") is None          # la excepción se tragaba...
    assert db.abortada is True                                         # ...pero la transacción quedaba rota


def test_con_proteccion_la_transaccion_sigue_sana(monkeypatch):
    db = SesionPostgresFalsa([])
    perfil = _perfil(db, monkeypatch)
    proteger_control(db, perfil)
    assert db.savepoints_usados == 1 and db.abortada is False
    assert construir_control(perfil, "unidad") is None                # y no hay encabezado de control
    db.commit()                                                        # la escritura posterior funciona


def test_proteger_un_perfil_inexistente_no_hace_nada():
    db = SesionPostgresFalsa([])
    proteger_control(db, None)
    assert db.savepoints_usados == 0


def test_con_la_columna_presente_se_conserva_el_control():
    class Perfil:
        nombre_institucion = "X"
        control_documentario = {"version": "02", "aprobado_por": "Dirección"}

    db = SesionPostgresFalsa([])
    proteger_control(db, Perfil())
    assert construir_control(Perfil(), "unidad")["version"] == "02"


# --- Las rutas de exportación ---

@pytest.mark.asyncio
async def test_exportar_pdf_funciona_aunque_falte_la_migracion_y_cuenta_la_exportacion(monkeypatch):
    db = SesionPostgresFalsa([])
    db._respuestas = [_perfil(db, monkeypatch)]
    usuario = SimpleNamespace(id="u1", stats=SimpleNamespace(exportaciones_pdf=0))
    resp = await export_pdf(data=CONTENIDO, db=db, current_user=usuario)
    assert resp.path.endswith(".pdf")
    assert usuario.stats.exportaciones_pdf == 1 and db.confirmaciones == 1 and db.abortada is False


@pytest.mark.asyncio
async def test_exportar_docx_funciona_aunque_falte_la_migracion_y_cuenta_la_exportacion(monkeypatch):
    db = SesionPostgresFalsa([])
    db._respuestas = [None, _perfil(db, monkeypatch)]                     # 1.ª consulta: plantilla activa; 2.ª: perfil
    usuario = SimpleNamespace(id="u1", stats=SimpleNamespace(exportaciones_docx=0))
    resp = await export_docx(data=CONTENIDO, db=db, current_user=usuario)
    assert resp.path.endswith(".docx")
    assert usuario.stats.exportaciones_docx == 1 and db.confirmaciones == 1 and db.abortada is False


@pytest.mark.asyncio
async def test_las_exportaciones_sin_perfil_siguen_funcionando():
    db = SesionPostgresFalsa([None])
    resp = await export_pdf(data=CONTENIDO, db=db, current_user=SimpleNamespace(id="u1", stats=None))
    assert resp.path.endswith(".pdf")
