from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# as_uuid=False: el valor en Python queda como str plano (no uuid.UUID),
# igual que lo que ya devuelve supabase-py — minimiza fricción en el resto
# del código (f-strings con current_user.id, comparaciones, JSON, etc).
UserUUID = UUID(as_uuid=False)


class User(Base):
    """Perfil de aplicación, 1:1 con auth.users de Supabase (id compartido).

    __tablename__ = "profiles" (no "users") para no confundirse con la tabla
    interna de Supabase Auth. id/email/full_name reflejan lo que ya existe en
    auth.users; hashed_password ya no aplica — Supabase es dueño de las
    credenciales.
    """
    __tablename__ = "profiles"

    id = Column(UserUUID, primary_key=True, index=True)  # UUID de auth.users.id
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    stats = relationship("UserStats", back_populates="owner", uselist=False)

class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UserUUID, ForeignKey("profiles.id"), unique=True)

    docs_generados = Column(Integer, default=0)
    unidades_generadas = Column(Integer, default=0)
    sesiones_generadas = Column(Integer, default=0)
    mejoras_realizadas = Column(Integer, default=0)
    exportaciones_docx = Column(Integer, default=0)
    exportaciones_pdf = Column(Integer, default=0)

    nivel = Column(Integer, default=1)
    puntos = Column(Integer, default=0)
    racha_manual = Column(Integer, default=0)

    badges_desbloqueados = Column(JSON, default=list) # List of badge IDs
    areas_usadas = Column(JSON, default=list)
    grados_usados = Column(JSON, default=list)
    dias_uso = Column(JSON, default=list) # List of date strings YYYY-MM-DD

    ultima_conexion = Column(DateTime, default=datetime.utcnow)
    primera_visita = Column(Boolean, default=True)

    owner = relationship("User", back_populates="stats")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True) # UUID de aplicación (no de auth)
    user_id = Column(UserUUID, ForeignKey("profiles.id"))
    type = Column(String) # 'unidad' or 'sesion'
    title = Column(String)
    content = Column(JSON) # The structured object (Situacion, Propositos, etc.)
    current_version = Column(Integer, default=1)
    # HU-22: vínculo explícito de una Sesión con la Unidad Didáctica de la que
    # proviene, elegida por el docente en el wizard (en vez de retipear el
    # título a mano). Nulo si la Sesión se creó sin unidad asociada.
    parent_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")
    parent_document = relationship("Document", remote_side=[id])
    versions = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_num")
    pipeline_run = relationship("PipelineRun", back_populates="document", uselist=False)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"))
    version_num = Column(Integer, nullable=False)       # 1, 2, 3...
    content = Column(JSON, nullable=False)              # Full snapshot
    change_label = Column(String, default="Edición")   # e.g. "Refinado: situacion_significativa"
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="versions")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(String, primary_key=True, index=True)   # UUID
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    tipo = Column(String)                               # 'unidad' | 'sesion'
    area_curricular = Column(String, nullable=True)
    grado = Column(String, nullable=True)
    metodologia = Column(String, nullable=True)
    puntaje_validacion = Column(Integer, default=0)     # 0-100
    errores_criticos = Column(Integer, default=0)
    errores_advertencia = Column(Integer, default=0)
    correcciones_aplicadas = Column(Integer, default=0)
    tokens_aprox = Column(Integer, default=0)
    duracion_ms = Column(Integer, default=0)
    llm_model = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="pipeline_run")
