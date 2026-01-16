from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from app.models.certificate import TipoTramite, TramiteStatus, TramiteEntregado


# Request schemas
class CertificateRequestCreate(BaseModel):
    """
    Schema for creating a new certificate request
    """
    nombre_alumno: str = Field(..., max_length=100)
    a_paterno: str = Field(..., max_length=100)
    a_materno: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    email: str = Field(..., max_length=255)
    curp: str = Field(..., min_length=18, max_length=18)
    cct: str = Field(..., max_length=20)
    nombre_esc: str = Field(..., max_length=255)
    dom_esc: Optional[str] = Field(None, max_length=255)
    turno: str = Field(..., max_length=50)
    ciclo_terminacion: str = Field(..., max_length=20)
    tipo_tramite: TipoTramite
    core: Optional[str] = Field(None, max_length=255)
    correccion: Optional[str] = Field("NO", max_length=5)  # SI/NO

    @validator('curp')
    def curp_must_be_valid(cls, v):
        v = v.strip().upper()
        if len(v) != 18:
            raise ValueError('CURP debe tener 18 caracteres')
        return v

    @validator('cct')
    def cct_must_be_valid(cls, v):
        v = v.strip().upper()
        if not v.startswith('22'):
            raise ValueError('La CCT debe comenzar con 22 (Queretaro)')
        return v

    @validator('correccion')
    def correccion_must_be_valid(cls, v):
        if v not in ['SI', 'NO']:
            raise ValueError('Correccion debe ser SI o NO')
        return v


# Response schemas
class CertificateRequestResponse(BaseModel):
    """
    Response schema for certificate request
    """
    success: bool
    message: str
    folio: Optional[str] = None
    status: Optional[TramiteStatus] = None
    requires_payment: bool = False
    payment_url: Optional[str] = None
    data: Optional[dict] = None

    class Config:
        from_attributes = True


class CertificateStatusResponse(BaseModel):
    """
    Response schema for certificate status query
    """
    folio: str
    nombre_alumno: str
    a_paterno: str
    a_materno: Optional[str]
    curp: str
    tipo_tramite: TipoTramite
    status: TramiteStatus
    entregado: TramiteEntregado
    fecha: str
    fecha_elaborado: Optional[date]
    region: Optional[str]
    requires_payment: bool

    class Config:
        from_attributes = True


class CertificateListResponse(BaseModel):
    """
    Response schema for listing certificates by CURP
    """
    curp: str
    certificates: list[CertificateStatusResponse]
    total: int

    class Config:
        from_attributes = True
