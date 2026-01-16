from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from app.models.student import StudentStatus


class StudentBase(BaseModel):
    al_curp: str = Field(..., min_length=18, max_length=18)
    al_nombre: str
    al_appat: str
    al_apmat: Optional[str] = None


class StudentCreate(StudentBase):
    pass


class Student(StudentBase):
    al_id: int
    al_estatus: StudentStatus
    al_fecing: Optional[date] = None
    al_fecnac: Optional[date] = None

    class Config:
        from_attributes = True


class EnrollmentBase(BaseModel):
    clavecct: str
    nivel: Optional[str] = None
    eg_grado: Optional[str] = None
    eg_grupo: Optional[str] = None
    turno: Optional[str] = None
    ciclo_escolar: Optional[str] = None


class Enrollment(EnrollmentBase):
    matricula_id: int
    al_id: int

    class Config:
        from_attributes = True


class StudentWithEnrollment(Student):
    current_enrollment: Optional[Enrollment] = None


class StudentParentCreate(BaseModel):
    al_curp: str = Field(..., min_length=18, max_length=18)
    relacion: str = Field(..., max_length=20)


class AddStudentRequest(BaseModel):
    """
    Schema for adding a student to parent account
    """
    curp: str = Field(..., min_length=18, max_length=18, description="CURP del estudiante")
    apellido: str = Field(..., max_length=100, description="Apellido paterno del estudiante")
    cct: str = Field(..., max_length=20, description="Clave del centro de trabajo")
    grupo: str = Field(..., max_length=10, description="Grupo del estudiante")
    parentesco: str = Field(..., description="PADRE, MADRE o TUTOR")

    class Config:
        json_schema_extra = {
            "example": {
                "curp": "PEGJ050101HQTRMN00",
                "apellido": "PEREZ",
                "cct": "22DPR0001A",
                "grupo": "A",
                "parentesco": "PADRE"
            }
        }


class AddStudentResponse(BaseModel):
    """
    Response schema for adding student
    """
    success: bool
    message: str
    student: Optional[dict] = None
    siblings: Optional[list] = None

    class Config:
        from_attributes = True
