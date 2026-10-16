"""HU-38: puntos por acción directa (documento +10, mejora +5, exportación +15, insignia +20)."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api import gamification_logic as gl
from src.api import models
from src.api.routes import auth

ROOT = Path(__file__).resolve().parents[2]
USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _stats(**kw):
    base = dict(docs_generados=0, mejoras_realizadas=0, exportaciones_docx=0, exportaciones_pdf=0,
                badges_desbloqueados=[], areas_usadas=[], grados_usados=[], dias_uso=[], puntos=0)
    base.update(kw)
    return SimpleNamespace(**base)


# --- calcular_puntos (unidad) ---

def test_sin_actividad_cero_puntos():
    assert gl.calcular_puntos(_stats()) == 0


@pytest.mark.parametrize("campo,valor,esperado", [
    ("docs_generados", 1, 10),
    ("mejoras_realizadas", 1, 5),
    ("exportaciones_docx", 1, 15),
    ("exportaciones_pdf", 1, 15),
    ("badges_desbloqueados", ["primer_paso"], 20),
])
def test_cada_accion_suma_lo_documentado(campo, valor, esperado):
    assert gl.calcular_puntos(_stats(**{campo: valor})) == esperado


def test_docx_y_pdf_cuentan_como_exportaciones():
    assert gl.calcular_puntos(_stats(exportaciones_docx=2, exportaciones_pdf=3)) == 5 * 15


def test_formula_combinada():
    s = _stats(docs_generados=3, mejoras_realizadas=4, exportaciones_docx=1, exportaciones_pdf=1,
               badges_desbloqueados=["a", "b"])
    assert gl.calcular_puntos(s) == 3 * 10 + 4 * 5 + 2 * 15 + 2 * 20


def test_tolera_contadores_nulos():
    s = _stats(docs_generados=None, mejoras_realizadas=None, exportaciones_docx=None,
               exportaciones_pdf=None, badges_desbloqueados=None)
    assert gl.calcular_puntos(s) == 0


def test_los_valores_coinciden_con_la_regla_documentada():
    assert (gl.PUNTOS_POR_DOCUMENTO, gl.PUNTOS_POR_MEJORA,
            gl.PUNTOS_POR_EXPORTACION, gl.PUNTOS_POR_INSIGNIA) == (10, 5, 15, 20)
    doc = (ROOT / "docs/DETALLES_TECNICOS.md").read_text(encoding="utf-8")
    assert "+10 por documento generado, +5 por mejora, +15 por exportación" in doc


def test_la_fuente_unica_es_calcular_puntos_y_ya_no_se_suma_por_insignia_suelta():
    src = (ROOT / "src/api/routes/auth.py").read_text(encoding="utf-8")
    assert "gamification_logic.calcular_puntos(stats)" in src
    assert "puntos +=" not in src


# --- GET /auth/stats (integración con la BD real del modelo en SQLite) ---

@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for t in (models.User.__table__, models.UserStats.__table__):
        t.create(engine, checkfirst=True)
    s = sessionmaker(bind=engine)()
    s.add(models.User(id=USER, email="a@x.com"))
    s.add(models.UserStats(user_id=USER, docs_generados=0, mejoras_realizadas=0, exportaciones_docx=0,
                           exportaciones_pdf=0, puntos=0, badges_desbloqueados=[], areas_usadas=[],
                           grados_usados=[], dias_uso=[]))
    s.commit()
    yield s
    s.close()


def _stats_endpoint(db):
    user = db.get(models.User, USER)
    return auth.get_stats(current_user=user, db=db)


def _puntos(db):
    return db.query(models.UserStats).filter_by(user_id=USER).one().puntos


def test_endpoint_persiste_los_puntos_de_las_acciones(db):
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.docs_generados, st.mejoras_realizadas, st.exportaciones_pdf = 1, 2, 1
    db.commit()
    resp = _stats_endpoint(db)
    # 1 doc (10) + 2 mejoras (10) + 1 export (15) + insignia "primer_paso" (20)
    assert "primer_paso" in resp["new_unlocks"]
    assert _puntos(db) == 10 + 10 + 15 + 20


def test_llamar_dos_veces_no_duplica_los_puntos(db):
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.docs_generados = 1
    db.commit()
    _stats_endpoint(db)
    primero = _puntos(db)
    _stats_endpoint(db)
    _stats_endpoint(db)
    assert _puntos(db) == primero == 10 + 20


def test_una_accion_nueva_entre_consultas_suma_solo_su_parte(db):
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.docs_generados = 1
    db.commit()
    _stats_endpoint(db)
    base = _puntos(db)
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.exportaciones_docx += 1
    db.commit()
    _stats_endpoint(db)
    assert _puntos(db) == base + 15


def test_una_insignia_nueva_suma_20_una_sola_vez(db):
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.docs_generados = 1
    db.commit()
    _stats_endpoint(db)
    sin_insignias_nuevas = _puntos(db)
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.mejoras_realizadas = 5            # desbloquea "maestro_detalle" (+20) además de 5 mejoras (+25)
    db.commit()
    resp = _stats_endpoint(db)
    assert "maestro_detalle" in resp["new_unlocks"]
    assert _puntos(db) == sin_insignias_nuevas + 25 + 20
    assert _stats_endpoint(db)["new_unlocks"] == []


def test_el_nivel_sale_de_los_puntos_derivados(db):
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.docs_generados = 8                # 80 pts + insignia "primer_paso" 20 = 100 -> Intermedio
    db.commit()
    resp = _stats_endpoint(db)
    assert _puntos(db) == 100
    assert resp["level"]["nombre"] == "Intermedio"


def test_los_puntos_previos_por_insignias_se_conservan_o_aumentan(db):
    """Un usuario que ya tenía puntos solo por insignias (modelo anterior) no pierde puntos."""
    st = db.query(models.UserStats).filter_by(user_id=USER).one()
    st.docs_generados = 1
    st.badges_desbloqueados = ["primer_paso"]
    st.puntos = 20                       # lo que el modelo anterior le habría dado
    db.commit()
    _stats_endpoint(db)
    assert _puntos(db) >= 20
