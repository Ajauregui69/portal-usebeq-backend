from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserStatus


# Shared properties
class UserBase(BaseModel):
    u_correo: EmailStr
    u_nombre: str = Field(..., min_length=1, max_length=100)
    u_appat: str = Field(..., min_length=1, max_length=100)
    u_apmat: Optional[str] = Field(None, max_length=100)
    u_tel: Optional[str] = Field(None, max_length=20)
    domicilio: Optional[str] = Field(None, max_length=255)
    sexo: Optional[str] = Field(None, max_length=1)


# Properties to receive on user creation
class UserCreate(UserBase):
    u_pass: str = Field(..., min_length=6)


# Properties to receive on user update
class UserUpdate(BaseModel):
    u_nombre: Optional[str] = None
    u_appat: Optional[str] = None
    u_apmat: Optional[str] = None
    u_tel: Optional[str] = None
    domicilio: Optional[str] = None
    sexo: Optional[str] = None


# Properties stored in DB
class UserInDB(UserBase):
    u_id: int
    estatus: UserStatus
    fecha_registro: datetime
    fecha_validacion: Optional[datetime] = None

    class Config:
        from_attributes = True


# Properties to return to client
class User(UserInDB):
    pass


# Login schemas
class UserLogin(BaseModel):
    u_correo: EmailStr
    u_pass: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None
