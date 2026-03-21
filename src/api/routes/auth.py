from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..database import get_db
from .. import models, schemas, auth_utils, gamification_logic
from datetime import datetime
from typing import Dict, Any

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
