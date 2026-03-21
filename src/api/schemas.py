from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Stats Schemas
class UserStatsBase(BaseModel):
    docs_generados: int = 0
    unidades_generadas: int = 0
    sesiones_generadas: int = 0
    mejoras_realizadas: int = 0
    exportaciones_docx: int = 0
    exportaciones_pdf: int = 0
    nivel: int = 1
    puntos: int = 0
    racha_manual: int = 0
    badges_desbloqueados: List[str] = []
    areas_usadas: List[str] = []
    grados_usados: List[str] = []
    dias_uso: List[str] = []
    primera_visita: bool = True

class UserStats(UserStatsBase):
    id: int
    user_id: int
    ultima_conexion: datetime

    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Document Schemas
class DocumentBase(BaseModel):
    title: str
    type: str
    content: Dict[str, Any]

class DocumentCreate(DocumentBase):
    id: str

class Document(DocumentBase):
    id: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
