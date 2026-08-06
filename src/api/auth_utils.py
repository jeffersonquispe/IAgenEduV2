from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration
# Sin valor por defecto (HU-21): un fallback hardcodeado quedaría expuesto en
# el historial de git y permitiría firmar tokens JWT válidos para cualquier
# usuario en cualquier despliegue que arranque sin configurar esta variable.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está configurada. Define esta variable de entorno antes de "
        "arrancar la aplicación (ver .env.example). Generar una con: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Recuperación de contraseña (HU-19) ---
# Token independiente del JWT de sesión: nunca debe poder usarse para
# generar un access_token, solo para autorizar un único reset de contraseña.
PASSWORD_RESET_EXPIRE_MINUTES = 30

def generar_token_reseteo() -> str:
    """Token aleatorio de alta entropía para enviar al usuario (URL-safe)."""
    return secrets.token_urlsafe(32)

def hash_token_reseteo(token: str) -> str:
    """Hash rápido (no bcrypt): el token ya es aleatorio de alta entropía,
    no algo que un usuario elige y reutiliza, así que no hace falta un hash
    lento anti-fuerza-bruta como para contraseñas — solo evitar guardarlo
    en texto plano en la base de datos."""
    return hashlib.sha256(token.encode()).hexdigest()
