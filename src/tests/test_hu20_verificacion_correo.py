"""HU-20: estado de verificación de correo (Supabase Auth) en el backend y el frontend."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api import models
from src.api.database import get_db
from src.api.routes import auth

ROOT = Path(__file__).resolve().parents[2]
USER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CABECERA = {"Authorization": "Bearer token-de-prueba"}


class SupabaseFalso:
    """Imita supabase.auth.get_user: devuelve el usuario que se le configure."""

    def __init__(self, usuario=None, falla=False):
        self.usuario, self.falla = usuario, falla
        self.auth = self

    def get_user(self, token):
        if self.falla:
            raise RuntimeError("token inválido")
        return SimpleNamespace(user=self.usuario)


def _usuario(confirmado):
    return SimpleNamespace(
        id=USER, email="docente@x.com", user_metadata={"full_name": "Ana"},
        email_confirmed_at=datetime(2026, 10, 1) if confirmado else None,
    )


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for t in (models.User.__table__, models.UserStats.__table__):
        t.create(engine, checkfirst=True)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def cliente(db, monkeypatch):
    monkeypatch.delenv("REQUIRE_VERIFIED_EMAIL", raising=False)
    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[get_db] = lambda: db

    def configurar(usuario=None, falla=False, exigir=None):
        monkeypatch.setattr(auth, "_supabase", SupabaseFalso(usuario, falla))
        if exigir is not None:
            monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", exigir)
        return TestClient(app)
    return configurar


# --- La bandera de configuración ---

@pytest.mark.parametrize("valor,esperado", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False), ("cualquier cosa", False),
    ("true", True), ("TRUE", True), (" 1 ", True), ("yes", True), ("sí", True),
])
def test_lectura_de_require_verified_email(monkeypatch, valor, esperado):
    if valor is None:
        monkeypatch.delenv("REQUIRE_VERIFIED_EMAIL", raising=False)
    else:
        monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", valor)
    assert auth.exigir_correo_verificado() is esperado


# --- GET /auth/me ---

def test_usuario_verificado_ve_email_verified_true(cliente):
    r = cliente(_usuario(confirmado=True)).get("/auth/me", headers=CABECERA)
    assert r.status_code == 200
    assert r.json()["email_verified"] is True and r.json()["email"] == "docente@x.com"


def test_usuario_sin_verificar_puede_entrar_por_defecto_pero_se_le_avisa(cliente):
    """Política recomendada por la historia: sin bloqueo, con aviso persistente."""
    r = cliente(_usuario(confirmado=False)).get("/auth/me", headers=CABECERA)
    assert r.status_code == 200 and r.json()["email_verified"] is False


def test_con_el_bloqueo_activo_un_usuario_sin_verificar_recibe_403_con_codigo(cliente):
    r = cliente(_usuario(confirmado=False), exigir="true").get("/auth/me", headers=CABECERA)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "email_not_verified"
    assert "confirmar tu correo" in r.json()["detail"]["message"]


def test_con_el_bloqueo_activo_un_usuario_verificado_sigue_entrando(cliente):
    r = cliente(_usuario(confirmado=True), exigir="true").get("/auth/me", headers=CABECERA)
    assert r.status_code == 200 and r.json()["email_verified"] is True


def test_el_bloqueo_tambien_protege_otros_endpoints(cliente):
    r = cliente(_usuario(confirmado=False), exigir="true").get("/auth/stats", headers=CABECERA)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "email_not_verified"


def test_un_usuario_bloqueado_no_crea_su_perfil(cliente, db):
    cliente(_usuario(confirmado=False), exigir="true").get("/auth/me", headers=CABECERA)
    assert db.query(models.User).count() == 0 and db.query(models.UserStats).count() == 0


def test_sin_bloqueo_el_primer_acceso_crea_el_perfil(cliente, db):
    cliente(_usuario(confirmado=False)).get("/auth/me", headers=CABECERA)
    assert db.query(models.User).count() == 1 and db.query(models.UserStats).count() == 1


def test_un_token_invalido_sigue_dando_401(cliente):
    r = cliente(falla=True, exigir="true").get("/auth/me", headers=CABECERA)
    assert r.status_code == 401


def test_sin_token_no_hay_acceso(cliente):
    assert cliente(_usuario(True)).get("/auth/me").status_code in (401, 403)


def test_si_el_sdk_no_informa_el_campo_se_trata_como_sin_verificar(cliente):
    sin_campo = SimpleNamespace(id=USER, email="docente@x.com", user_metadata={})
    r = cliente(sin_campo).get("/auth/me", headers=CABECERA)
    assert r.json()["email_verified"] is False


# --- Frontend (verificación estática) ---

def _leer(ruta):
    return (ROOT / ruta).read_text(encoding="utf-8")


def test_el_registro_ya_no_usa_alert_y_muestra_la_pantalla_de_confirmacion():
    src = _leer("frontend/src/pages/Login.jsx")
    assert "Registro exitoso" not in src and "alert(" not in src
    assert "setPendienteConfirmar(email)" in src
    assert "Revisa tu correo" in src and "<ReenviarCorreo" in src


def test_el_login_reconoce_el_error_de_correo_sin_confirmar_y_ofrece_reenviar():
    src = _leer("frontend/src/pages/Login.jsx")
    assert "esErrorCorreoSinConfirmar(err)" in src
    assert "{correoSinConfirmar && <ReenviarCorreo" in src


def test_las_utilidades_de_verificacion():
    src = _leer("frontend/src/lib/verificacionCorreo.js")
    assert "email_not_confirmed" in src and "Email not confirmed".lower() in src.lower()
    assert "supabase.auth.resend" in src and "type: 'signup'" in src
    assert "email_not_verified" in src and "SEGUNDOS_ENTRE_REENVIOS = 60" in src


def test_el_reenvio_tiene_enfriamiento():
    src = _leer("frontend/src/components/ReenviarCorreo.jsx")
    assert "disabled={enviando || segundos > 0 || !email}" in src


def test_el_dashboard_muestra_el_aviso_persistente():
    assert "<VerificarCorreoBanner />" in _leer("frontend/src/pages/Dashboard.jsx")
    banner = _leer("frontend/src/components/VerificarCorreoBanner.jsx")
    assert "email_verified === false" in banner and "esErrorCorreoNoVerificado(err)" in banner
    assert 'role="alert"' in banner


def test_la_variable_de_entorno_esta_documentada_y_apagada_por_defecto():
    env = _leer(".env.example")
    assert "# REQUIRE_VERIFIED_EMAIL=true" in env and "Confirm email" in env
