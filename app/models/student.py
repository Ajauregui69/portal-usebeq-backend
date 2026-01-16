from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class StudentStatus(str, enum.Enum):
    I = "I"  # Inscrito
    B = "B"  # Baja
    A = "A"  # Inscrito con adeudo
    E = "E"  # Egresado


class Student(Base):
    """
    Student model representing SCE004 table
    """
    __tablename__ = "SCE004"

    al_id = Column(Integer, primary_key=True, index=True)
    al_curp = Column(String(18), unique=True, index=True, nullable=False)
    al_nombre = Column(String(100), nullable=False)
    al_appat = Column(String(100), nullable=False)
    al_apmat = Column(String(100))
    al_estatus = Column(SQLEnum(StudentStatus), default=StudentStatus.I)
    al_fecing = Column(Date, nullable=True)  # Fecha de ingreso
    al_fecnac = Column(Date, nullable=True)  # Fecha de nacimiento

    # Relationships
    enrollments = relationship("Enrollment", back_populates="student")
    parents = relationship("StudentParent", back_populates="student")


class Enrollment(Base):
    """
    Enrollment model representing SCE005 table
    """
    __tablename__ = "SCE005"

    matricula_id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, ForeignKey("SCE004.al_id"), nullable=False)
    clavecct = Column(String(20), nullable=False)  # School key
    nivel = Column(String(50))  # Education level
    eg_grado = Column(String(10))  # Grade
    eg_grupo = Column(String(10))  # Group
    turno = Column(String(20))  # Shift
    ciclo_escolar = Column(String(20))  # School cycle

    # Relationships
    student = relationship("Student", back_populates="enrollments")


class StudentParent(Base):
    """
    Student-Parent relationship model representing pp_alumnos table
    """
    __tablename__ = "pp_alumnos"

    id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, ForeignKey("SCE004.al_id"), nullable=False)
    u_id = Column(Integer, ForeignKey("PP_usuarios.u_id"), nullable=False)
    relacion = Column(String(20))  # padre, madre, tutor

    # Relationships
    student = relationship("Student", back_populates="parents")
    user = relationship("User", back_populates="students")
