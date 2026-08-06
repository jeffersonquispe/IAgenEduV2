from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..database import get_db
from .. import models, schemas, auth_utils, gamification_logic
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth_utils.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Initialize default stats for the user
    new_stats = models.UserStats(user_id=new_user.id)
    db.add(new_stats)
    db.commit()
    
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    
    if not auth_utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    
    # Update last connection and record daily use
    if user.stats:
        hoy = datetime.utcnow().strftime("%Y-%m-%d")
        dias = list(user.stats.dias_uso or [])
        if hoy not in dias:
            dias.append(hoy)
            user.stats.dias_uso = dias
        user.stats.ultima_conexion = datetime.utcnow()
        db.commit()
    
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    HU-19: inicia el reseteo de contraseña. La respuesta es siempre el mismo
    mensaje genérico, exista o no el correo — evita que alguien use este
    endpoint para enumerar cuentas registradas.

    El proyecto no tiene un servicio de envío de email configurado (ver nota
    de implementación en el backlog). Como alternativa mínima para el
    alcance de tesis, el link de reseteo se registra en el log del servidor
    en vez de enviarse por correo real.
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        raw_token = auth_utils.generar_token_reseteo()
        reset_token = models.PasswordResetToken(
            user_id=user.id,
            token_hash=auth_utils.hash_token_reseteo(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=auth_utils.PASSWORD_RESET_EXPIRE_MINUTES),
        )
        db.add(reset_token)
        db.commit()

        # Sin SMTP: se registra en el log en vez de enviarse por correo.
        # En un despliegue real, reemplazar este log por un envío de email real.
        logger.warning(
            f"[PasswordReset] Link de reseteo para {user.email} "
            f"(expira en {auth_utils.PASSWORD_RESET_EXPIRE_MINUTES} min): "
            f"/reset-password?token={raw_token}"
        )

    return {"message": "Si el correo existe en el sistema, se generó un enlace de recuperación."}


@router.post("/reset-password")
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """HU-19: completa el reseteo — token de un solo uso, no reutiliza el JWT de sesión."""
    token_hash = auth_utils.hash_token_reseteo(payload.token)
    reset_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token_hash == token_hash,
        models.PasswordResetToken.used == False,  # noqa: E712
    ).first()

    if not reset_token or reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user.hashed_password = auth_utils.get_password_hash(payload.new_password)
    reset_token.used = True
    db.commit()

    return {"message": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}


@router.get("/me", response_model=schemas.User)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/stats", response_model=Dict[str, Any])
def get_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    stats = current_user.stats
    if not stats:
        raise HTTPException(status_code=404, detail="Stats not found")
    
    # Check for new badges
    nuevos_badges = gamification_logic.check_new_badges(stats)
    if nuevos_badges:
        current_ids = list(stats.badges_desbloqueados or [])
        stats.badges_desbloqueados = list(set(current_ids + nuevos_badges))
        stats.puntos += len(nuevos_badges) * 20
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
