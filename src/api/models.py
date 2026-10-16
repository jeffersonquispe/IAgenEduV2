from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Boolean, Float, LargeBinary, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, deferred
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
    # HU-24: área y grado en el propio documento, para filtrar sin depender de
    # pipeline_runs (que no existe para los generados en modo "solo_generador").
    area_curricular = Column(String, nullable=True)
    grado = Column(String, nullable=True)
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


class InstitutionProfile(Base):
    """HU-31: perfil institucional del docente, 1:1 con User (mismo patrón que
    UserStats). Persiste datos que hoy se repetirían en cada generación
    (nombre de la institución, visión, contexto) y sirve de fuente para
    HU-32/HU-36/HU-42 (contexto institucional, valores y matriz axiológica
    inyectados en el pipeline de generación).
    """
    __tablename__ = "institution_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UserUUID, ForeignKey("profiles.id"), unique=True)

    nombre_institucion = Column(String, nullable=True)
    nivel_modalidad = Column(String, nullable=True)
    dre_ugel = Column(String, nullable=True)
    coordinacion_pedagogica = Column(String, nullable=True)
    vision = Column(String, nullable=True)
    mision = Column(String, nullable=True)
    contexto_relevante = Column(String, nullable=True)
    # Lista de nombres (compatibilidad con VALORES_CNEB_DEFAULT/resolver_valores_institucionales).
    valores_institucionales = Column(JSON, nullable=True)
    enfoques_transversales = Column(JSON, nullable=True)
    # HU-42: matriz axiológica estructurada opcional — lista de objetos
    # {valor, enfoque, comportamiento_observable, instrumento}. Si está vacía,
    # el generador arma la matriz emparejando valores_institucionales /
    # enfoques_transversales de forma genérica.
    matriz_axiologica = Column(JSON, nullable=True)
    # HU-47: datos del encabezado de control documentario (red, version, aprobado_por,
    # fecha_aprobacion, revisado_por, fecha_revision). `deferred`: no se incluye en los
    # SELECT del perfil salvo que se lea, así una base a la que todavía no se le aplicó
    # supabase/migrations/20261009_institution_control_documentario.sql sigue funcionando.
    control_documentario = deferred(Column(JSON, nullable=True))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")


class DocumentTemplate(Base):
    """HU-48: plantilla institucional (.docx) subida por el docente para
    Unidad o Sesión, ya parseada en un esquema reutilizable (ver
    src/core/template_parser.py). Solo una plantilla "activa" por
    (usuario, tipo) a la vez — subir una nueva desactiva la anterior en vez
    de reemplazarla, para no perder el archivo original de versiones previas.
    """
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UserUUID, ForeignKey("profiles.id"), index=True)
    tipo = Column(String)  # 'unidad' | 'sesion'
    nombre_archivo = Column(String)
    archivo_original = Column(LargeBinary)  # bytes del .docx tal como se subió (HU-50 lo reutiliza para exportar)
    esquema = Column(JSON)  # TemplateSchema.to_dict() — ver template_parser.py
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")


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


class GenerationJob(Base):
    """HU-33: generación de un documento ejecutada en segundo plano.

    El cliente recibe el job_id de inmediato (202) y consulta el estado por
    polling; así el trabajo sobrevive a que se cierre la pestaña. Ver
    services/job_service.py.
    """
    __tablename__ = "generation_jobs"

    id = Column(String, primary_key=True, index=True)          # UUID de aplicación
    user_id = Column(UserUUID, ForeignKey("profiles.id"), index=True)
    tipo = Column(String)                                      # 'unidad' | 'sesion'
    status = Column(String, default="pending", index=True)     # pending|running|done|failed
    params = Column(JSON)
    result_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
