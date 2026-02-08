#D:\codigos\contador_cerdos_final\backend\schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Schemas para Usuarios
class UsuarioBase(BaseModel):
    username: str
    email: str  # Cambiado de EmailStr a str para simplificar
    nombre_completo: Optional[str] = None
    rol: Optional[str] = "usuario"


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[str] = None  # Cambiado de EmailStr
    password: Optional[str] = None


class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    creado_en: datetime

    class Config:
        from_attributes = True


# Schemas para Autenticación
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UsuarioResponse


class TokenData(BaseModel):
    username: Optional[str] = None
    rol: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CambioPassword(BaseModel):
    password_actual: str
    password_nuevo: str