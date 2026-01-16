from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class UserStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    VALIDADO = "VALIDADO"
    INACTIVO = "INACTIVO"


class User(Base):
    """
    User model representing PP_usuarios table
    """
    __tablename__ = "PP_usuarios"

    u_id = Column(Integer, primary_key=True, index=True)
    u_correo = Column(String(255), unique=True, index=True, nullable=False)
    u_pass = Column(String(255), nullable=False)
    estatus = Column(SQLEnum(UserStatus), default=UserStatus.PENDIENTE)
    u_nombre = Column(String(100), nullable=False)
    u_appat = Column(String(100), nullable=False)
    u_apmat = Column(String(100))
    u_tel = Column(String(20))
    domicilio = Column(String(255))
    sexo = Column(String(1))
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    fecha_validacion = Column(DateTime, nullable=True)
    token_activacion = Column(String(255), nullable=True)

    # Relationships
    students = relationship("StudentParent", back_populates="user")
