from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# User Schemas — el registro/login ahora los maneja Supabase Auth
# directamente desde el frontend; estos schemas solo describen el perfil
# de aplicación (public.profiles), no crean cuentas.
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class User(UserBase):
    id: str  # UUID de Supabase (auth.users.id)
    is_active: bool
    created_at: datetime
    # HU-20: no es una columna; lo calcula get_current_user desde auth.users
    # (email_confirmed_at), que es la fuente de verdad en Supabase.
    email_verified: bool = True

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
    user_id: str
    ultima_conexion: datetime

    class Config:
        from_attributes = True

# Document Schemas
class DocumentBase(BaseModel):
    title: str
    type: str
    content: Dict[str, Any]

class DocumentCreate(DocumentBase):
    id: str

class Document(DocumentBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# HU-47: encabezado de control documentario (los largos coinciden con core/control_documentario.py)
class ControlDocumentario(BaseModel):
    red: Optional[str] = Field(None, max_length=80)
    version: Optional[str] = Field(None, max_length=20)
    aprobado_por: Optional[str] = Field(None, max_length=80)
    fecha_aprobacion: Optional[str] = Field(None, max_length=40)
    revisado_por: Optional[str] = Field(None, max_length=80)
    fecha_revision: Optional[str] = Field(None, max_length=40)

# Institution Profile Schemas (HU-31)
class InstitutionProfileBase(BaseModel):
    control_documentario: Optional[ControlDocumentario] = None
    nombre_institucion: Optional[str] = None
    nivel_modalidad: Optional[str] = None
    dre_ugel: Optional[str] = None
    coordinacion_pedagogica: Optional[str] = None
    vision: Optional[str] = None
    mision: Optional[str] = None
    contexto_relevante: Optional[str] = None
    valores_institucionales: Optional[List[str]] = None
    enfoques_transversales: Optional[List[str]] = None
    matriz_axiologica: Optional[List[Dict[str, Any]]] = None

class InstitutionProfileUpdate(InstitutionProfileBase):
    pass

class InstitutionProfile(InstitutionProfileBase):
    id: int
    user_id: str

    class Config:
        from_attributes = True

# Document Template Schemas (HU-48)
class DocumentTemplateSummary(BaseModel):
    id: int
    tipo: str
    nombre_archivo: str
    activa: bool
    esquema: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
