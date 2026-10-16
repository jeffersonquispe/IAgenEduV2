"""Perfil institucional de ejemplo (Colegio Salesiano de Cusco) y su script de carga."""
import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api import models
from src.core.valores_institucionales import resolver_enfoques_transversales, resolver_valores_institucionales

ROOT = Path(__file__).resolve().parents[2]
ARCHIVO = ROOT / "data/perfiles/salesiano_cusco.json"
EMAIL = "docente@x.com"
USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _cargar_modulo_script():
    spec = importlib.util.spec_from_file_location("cargar_perfil", ROOT / "scripts/cargar_perfil_institucional.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


script = _cargar_modulo_script()


# --- El archivo de datos ---

def test_el_json_pasa_el_mismo_esquema_que_usa_la_api():
    datos = script.leer_datos(ARCHIVO)
    assert datos["nombre_institucion"] == "Colegio Salesiano de Cusco"
    assert datos["valores_institucionales"] == ["Fe", "Amor", "Ciudadanía"]


def test_la_matriz_axiologica_tiene_un_comportamiento_por_valor():
    datos = script.leer_datos(ARCHIVO)
    matriz = datos["matriz_axiologica"]
    assert [f["valor"] for f in matriz] == datos["valores_institucionales"]
    assert all(f["comportamiento_observable"].strip() for f in matriz)


def test_no_inventa_lo_que_la_web_no_publica():
    """UGEL, coordinación, enfoques e instrumentos no figuran en la web: quedan vacíos."""
    datos = script.leer_datos(ARCHIVO)
    assert datos["dre_ugel"] is None and datos["coordinacion_pedagogica"] is None
    assert datos["enfoques_transversales"] is None
    assert all(not f["enfoque"] and not f["instrumento"] for f in datos["matriz_axiologica"])


def test_mision_y_vision_son_el_texto_publicado():
    datos = script.leer_datos(ARCHIVO)
    assert datos["mision"].startswith("Educar, evangelizar y acompañar a los jóvenes, especialmente los más pobres")
    assert datos["mision"].endswith("los valores de la fe, el amor y la ciudadanía.")
    assert datos["vision"].startswith("Al 2029 ser el Colegio Salesiano del Cusco")
    assert datos["vision"].endswith("la fe, el amor y la ciudadanía.")


def test_las_claves_de_comentario_no_llegan_al_perfil():
    crudo = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    assert "_fuente" in crudo and "https://www.salesianocusco.edu.pe/" in crudo["_fuente"]
    assert "_fuente" not in script.leer_datos(ARCHIVO)


def test_con_este_perfil_el_generador_usa_los_valores_del_colegio_y_cneb_para_enfoques():
    class Perfil:
        pass
    p = Perfil()
    datos = script.leer_datos(ARCHIVO)
    p.valores_institucionales = datos["valores_institucionales"]
    p.enfoques_transversales = datos["enfoques_transversales"]
    assert resolver_valores_institucionales(p) == ["Fe", "Amor", "Ciudadanía"]
    assert resolver_enfoques_transversales(p) == resolver_enfoques_transversales(None)   # cae al default CNEB


# --- El script de carga ---

@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for t in (models.User.__table__, models.InstitutionProfile.__table__):
        t.create(engine, checkfirst=True)
    s = sessionmaker(bind=engine)()
    s.add(models.User(id=USER, email=EMAIL))
    s.commit()
    yield s
    s.close()


def _perfil(db):
    return db.query(models.InstitutionProfile).filter_by(user_id=USER).first()


def test_crea_el_perfil_del_usuario(db):
    assert script.cargar_perfil(db, EMAIL, script.leer_datos(ARCHIVO)) == "creado"
    p = _perfil(db)
    assert p.nombre_institucion == "Colegio Salesiano de Cusco"
    assert p.valores_institucionales == ["Fe", "Amor", "Ciudadanía"]
    assert len(p.matriz_axiologica) == 3


def test_dry_run_no_escribe_nada(db):
    assert script.cargar_perfil(db, EMAIL, script.leer_datos(ARCHIVO), dry_run=True) == "simulado"
    assert _perfil(db) is None


def test_no_pisa_un_perfil_existente_sin_reemplazar(db):
    db.add(models.InstitutionProfile(user_id=USER, nombre_institucion="Mi colegio"))
    db.commit()
    with pytest.raises(script.PerfilExistente, match="Mi colegio"):
        script.cargar_perfil(db, EMAIL, script.leer_datos(ARCHIVO))
    assert _perfil(db).nombre_institucion == "Mi colegio"


def test_reemplazar_sobrescribe_el_perfil_existente(db):
    db.add(models.InstitutionProfile(user_id=USER, nombre_institucion="Mi colegio", dre_ugel="UGEL Cusco"))
    db.commit()
    assert script.cargar_perfil(db, EMAIL, script.leer_datos(ARCHIVO), reemplazar=True) == "reemplazado"
    p = _perfil(db)
    assert p.nombre_institucion == "Colegio Salesiano de Cusco"
    assert p.dre_ugel is None                      # el JSON no la trae: no se arrastra el valor anterior


def test_usuario_inexistente(db):
    with pytest.raises(LookupError, match="otro@x.com"):
        script.cargar_perfil(db, "otro@x.com", script.leer_datos(ARCHIVO))


def test_un_json_invalido_se_rechaza_antes_de_tocar_la_base(tmp_path):
    malo = tmp_path / "malo.json"
    malo.write_text(json.dumps({"nombre_institucion": "X", "valores_institucionales": "no es una lista"}),
                    encoding="utf-8")
    with pytest.raises(Exception):
        script.leer_datos(malo)
