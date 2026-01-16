from typing import Optional
from pydantic import BaseModel


class EstudianteUSEBEQ(BaseModel):
    """
    Schema for student data from USEBEQ external API
    """
    IdAlumno: int
    CURP: str
    ApellidoPaterno: str
    ApellidoMaterno: str
    Nombre: str
    CCT: str
    NombreCT: str
    Turno: str
    Grado: str
    Grupo: str
    Estatus: str


class SolicitudBajaRequest(BaseModel):
    """
    Request schema for student withdrawal
    """
    idAlumno: int
    idMotivoBaja: int


class SolicitudBajaResponse(BaseModel):
    """
    Response schema for student withdrawal
    """
    mensaje: str


class TipoBaja(BaseModel):
    """
    Schema for withdrawal type catalog
    """
    Id: int
    Descripcion: str


class SIGALoginRequest(BaseModel):
    """
    Request schema for SIGA authentication
    """
    correo: str
    contrasenia: str


class SIGALoginResponse(BaseModel):
    """
    Response schema for SIGA authentication
    """
    AccessToken: str
    RefreshToken: str


class SIGATokenStatus(BaseModel):
    """
    Schema for current token status
    """
    token_valid: bool
    token_preview: Optional[str] = None
    fecha_registro: Optional[str] = None
    message: str
