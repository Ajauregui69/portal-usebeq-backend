from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class TramiteStatus(str, enum.Enum):
    SOLICITADO = "SOLICITADO"
    SOLICITADO_SIN_RESPONSABLE = "SOLICITADO SIN RESPONSABLE"
    FIRMADO = "firmado"
    REIMPRESION = "REIMPRESION"
    EN_PROCESO = "EN PROCESO"
    RECHAZADO = "RECHAZADO"


class TramiteEntregado(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    ENTREGADO = "ENTREGADO"


class TipoTramite(str, enum.Enum):
    CERTIFICADO_PREESCOLAR = "CERTIFICADO DE PREESCOLAR"
    CERTIFICADO_PRIMARIA = "CERTIFICADO DE PRIMARIA"
    CERTIFICADO_SECUNDARIA = "CERTIFICADO DE SECUNDARIA"


class Certificate(Base):
    """
    Certificate model representing SCE039 table
    """
    __tablename__ = "SCE039"

    id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, ForeignKey("SCE004.al_id"), nullable=False)
    folio = Column(String(50), unique=True, index=True)
    foliosep = Column(String(50), unique=True, index=True)
    clavecct = Column(String(20))
    nivel = Column(String(50))
    ciclo_escolar = Column(String(20))
    promedio = Column(String(10))
    fecha_emision = Column(Date)
    IdEstatus = Column(Integer)  # Status ID

    # Relationships
    student = relationship("Student", foreign_keys=[al_id])


class CertificateDuplicate(Base):
    """
    Certificate duplicate requests model
    """
    __tablename__ = "SCE039_DUPLI"

    id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, ForeignKey("SCE004.al_id"), nullable=False)
    u_id = Column(Integer, ForeignKey("PP_usuarios.u_id"), nullable=False)
    tipo_documento = Column(String(50))  # CERTIFICADO, BOLETA, etc.
    folio_solicitud = Column(String(50), unique=True, index=True)
    fecha_solicitud = Column(Date)
    estatus = Column(String(20))  # PENDIENTE, PROCESADO, ENTREGADO
    nivel = Column(String(50))
    ciclo_escolar = Column(String(20))
    motivo = Column(Text)

    # Relationships
    student = relationship("Student", foreign_keys=[al_id])
    user = relationship("User", foreign_keys=[u_id])


class CertificateRequest(Base):
    """
    Model representing tramites1 table - Certificate requests
    """
    __tablename__ = "tramites1"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(50), unique=True, index=True, nullable=False)
    nombre_alumno = Column(String(100), nullable=False)
    a_paterno = Column(String(100), nullable=False)
    a_materno = Column(String(100))
    telefono = Column(String(20))
    email = Column(String(255))
    curp = Column(String(18), index=True, nullable=False)
    cct = Column(String(20), nullable=False)
    nombre_esc = Column(String(255))
    dom_esc = Column(String(255))
    turno = Column(String(50))
    ciclo_terminacion = Column(String(20), nullable=False)
    tipo_tramite = Column(SQLEnum(TipoTramite), nullable=False)
    usuario = Column(String(100))
    foto = Column(String(255))
    zona = Column(String(50))
    sector = Column(String(50))
    fecha = Column(String(20))  # Formato dd-mm-YYYY
    fecha_elaborado = Column(Date)
    status = Column(SQLEnum(TramiteStatus), default=TramiteStatus.SOLICITADO)
    entregado = Column(SQLEnum(TramiteEntregado), default=TramiteEntregado.PENDIENTE)
    region = Column(String(10))
    correccion = Column(String(5))  # SI/NO
    core = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tramite(Base):
    """
    Administrative procedures model (bajas, revocaciones, etc.)
    """
    __tablename__ = "PP_tramites"

    id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, ForeignKey("SCE004.al_id"), nullable=False)
    u_id = Column(Integer, ForeignKey("PP_usuarios.u_id"), nullable=False)
    tipo_tramite = Column(String(50))  # BAJA, REVOCACION, DUPLICADO
    folio = Column(String(50), unique=True, index=True)
    fecha_solicitud = Column(Date)
    estatus = Column(String(20))  # PENDIENTE, EN_PROCESO, COMPLETADO
    descripcion = Column(Text)
    documentos_adjuntos = Column(Text)  # JSON with document URLs

    # Relationships
    student = relationship("Student", foreign_keys=[al_id])
    user = relationship("User", foreign_keys=[u_id])
