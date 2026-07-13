from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class StudentStatus(str, enum.Enum):
    I = "I"  # Inscrito
    B = "B"  # Baja
    A = "A"  # Inscrito con adeudo
    E = "E"  # Egresado


class StudentParent(Base):
    """
    Student-Parent relationship model representing pp_alumnos table.
    Stores only the link (al_id from the USEBEQ API + user); student data
    is always fetched live from the USEBEQ external API, never persisted.
    """
    __tablename__ = "pp_alumnos"

    id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, nullable=False, index=True)  # IdAlumno from USEBEQ API
    # CURP provided by the parent at registration time (as in the production
    # PHP portal); allows linking by CURP alone once someone registered the
    # student with the full CURP + CCT flow
    al_curp = Column(String(18), nullable=True, index=True)
    u_id = Column(Integer, ForeignKey("PP_usuarios.u_id"), nullable=False)
    relacion = Column(String(20))  # padre, madre, tutor

    # Relationships
    user = relationship("User", back_populates="students")
