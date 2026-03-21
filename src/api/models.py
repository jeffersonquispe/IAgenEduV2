from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    stats = relationship("UserStats", back_populates="owner", uselist=False)

class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    docs_generados = Column(Integer, default=0)
    unidades_generadas = Column(Integer, default=0)
    sesiones_generadas = Column(Integer, default=0)
    mejoras_realizadas = Column(Integer, default=0)
    exportaciones_docx = Column(Integer, default=0)
    exportaciones_pdf = Column(Integer, default=0)
    
    nivel = Column(Integer, default=1)
    puntos = Column(Integer, default=0)
    racha_manual = Column(Integer, default=0)
    
    # Almacenamos listas como JSON en SQLite
    badges_desbloqueados = Column(JSON, default=list) # List of badge IDs
    areas_usadas = Column(JSON, default=list)
    grados_usados = Column(JSON, default=list)
    dias_uso = Column(JSON, default=list) # List of date strings YYYY-MM-DD
    
    ultima_conexion = Column(DateTime, default=datetime.utcnow)
    primera_visita = Column(Boolean, default=True)

    owner = relationship("User", back_populates="stats")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String) # 'unidad' or 'sesion'
    title = Column(String)
    content = Column(JSON) # The structured object (Situacion, Propositos, etc.)
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")
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
