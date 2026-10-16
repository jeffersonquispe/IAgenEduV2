from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from supabase import create_client, Client
from ..database import get_db
from .. import models, schemas, gamification_logic
from datetime import datetime
from typing import Dict, Any
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

router = APIRouter(prefix="/auth", tags=["auth"])

# Verificación de sesión delegada al SDK de Supabase (auth.get_user), no a
# decodificación local de JWT: los proyectos Supabase nuevos usan claves de
# firma asimétricas por defecto, así que no hay garantía de que exista un
# secreto HS256 compartido para verificar localmente, y esto evita atar el
# backend a la rotación de claves de Supabase. El costo de la llamada de red
# extra es irrelevante a la escala de este proyecto — get_current_user es
# una función sync, FastAPI ya la corre en threadpool.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_URL / SUPABASE_ANON_KEY no configuradas (ver .env.example)."
    )

_supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

_bearer_scheme = HTTPBearer()


def exigir_correo_verificado() -> bool:
    """HU-20: si REQUIRE_VERIFIED_EMAIL está activo, el backend rechaza (403) a quien no
    haya confirmado su correo. Se lee en cada llamada (no al importar) para poder
    cambiarlo sin reiniciar tests.

    Apagado por defecto a propósito: la verificación la hace Supabase Auth (opción
    "Confirm email" del panel), que ya impide iniciar sesión sin confirmar. Este
    control es una segunda barrera; activarlo con "Confirm email" desactivado
    dejaría sin acceso a los usuarios nuevos."""
    return os.getenv("REQUIRE_VERIFIED_EMAIL", "").strip().lower() in ("1", "true", "yes", "si", "sí")


def _bootstrap_profile(db: Session, supa_user) -> models.User:
    """Crea el perfil de aplicación (profiles + user_stats) la primera vez
    que se ve un usuario autenticado por Supabase — no depende de que el
    registro haya llamado a un endpoint aparte (evita que una fila de
    auth.users quede sin su profiles/user_stats correspondiente).

    Dos requests concurrentes (p.ej. Sidebar pidiendo /auth/stats y
    Dashboard pidiendo /data/documents en el primer login del usuario)
    pueden llegar aquí a la vez para el mismo usuario nuevo, cada una con
    su propia sesión de DB (ver get_db) — es una carrera de tipo
    check-then-act. Si perdemos el INSERT, no es un error real: la otra
    request ya creó el perfil, así que lo re-consultamos en vez de fallar.
    """
    full_name = (supa_user.user_metadata or {}).get("full_name")
    user = models.User(id=supa_user.id, email=supa_user.email, full_name=full_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(models.User).filter(models.User.id == supa_user.id).first()
        if existing is None:
            raise
        return existing
    db.refresh(user)

    db.add(models.UserStats(user_id=user.id))
    db.commit()
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        resp = _supabase.auth.get_user(credentials.credentials)
    except Exception:
        raise credentials_exception

    supa_user = resp.user if resp else None
    if not supa_user:
        raise credentials_exception

    verificado = bool(getattr(supa_user, "email_confirmed_at", None))
    if exigir_correo_verificado() and not verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Debes confirmar tu correo electrónico para usar la plataforma.",
            },
        )

    user = db.query(models.User).filter(models.User.id == supa_user.id).first()
    if user is None:
        user = _bootstrap_profile(db, supa_user)
    # Atributo transitorio (no es columna): lo lee GET /auth/me vía schemas.User.
    user.email_verified = verificado
    return user


@router.get("/me", response_model=schemas.User)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/stats", response_model=Dict[str, Any])
def get_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    stats = current_user.stats
    if not stats:
        raise HTTPException(status_code=404, detail="Stats not found")

    # Registro de conexión diaria — antes vivía en login(), que ya no existe
    # (Supabase Auth maneja el login); se registra aquí, en el primer check
    # de stats de la sesión (llamado al cargar el dashboard).
    hoy = datetime.utcnow().strftime("%Y-%m-%d")
    dias = list(stats.dias_uso or [])
    if hoy not in dias:
        dias.append(hoy)
        stats.dias_uso = dias
    stats.ultima_conexion = datetime.utcnow()

    # Check for new badges
    nuevos_badges = gamification_logic.check_new_badges(stats)
    if nuevos_badges:
        current_ids = list(stats.badges_desbloqueados or [])
        stats.badges_desbloqueados = list(set(current_ids + nuevos_badges))

    # HU-38: documentos, mejoras, exportaciones e insignias suman puntos.
    stats.puntos = gamification_logic.calcular_puntos(stats)

    db.commit()
    db.refresh(stats)

    nivel_info = gamification_logic.calcular_nivel(stats.puntos)
    racha = gamification_logic.calcular_racha(stats.dias_uso or [])

    return {
        "stats": schemas.UserStats.from_orm(stats),
        "level": nivel_info,
        "racha": racha,
        "available_badges": gamification_logic.BADGES,
        "new_unlocks": nuevos_badges
    }
