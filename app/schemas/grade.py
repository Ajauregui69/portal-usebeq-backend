from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class GradeBase(BaseModel):
    materia: str
    periodo: str
    calificacion: Decimal
    observaciones: Optional[str] = None


class Grade(GradeBase):
    id: int
    al_id: int
    matricula_id: int

    class Config:
        from_attributes = True


class GradesByPeriod(BaseModel):
    periodo: str
    calificaciones: list[Grade]
