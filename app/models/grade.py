from sqlalchemy import Column, Integer, String, DECIMAL, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Grade(Base):
    """
    Grade/Calificaciones model representing SCE006 table
    """
    __tablename__ = "SCE006"

    id = Column(Integer, primary_key=True, index=True)
    al_id = Column(Integer, ForeignKey("SCE004.al_id"), nullable=False)
    matricula_id = Column(Integer, ForeignKey("SCE005.matricula_id"), nullable=False)
    materia = Column(String(100))
    periodo = Column(String(50))  # 1er Bimestre, 2do Bimestre, etc.
    calificacion = Column(DECIMAL(5, 2))
    observaciones = Column(Text)

    # Relationships
    student = relationship("Student", foreign_keys=[al_id])
    enrollment = relationship("Enrollment", foreign_keys=[matricula_id])
