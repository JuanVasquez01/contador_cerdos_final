#D:\codigos\contador_cerdos_final\backend\models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nombre_completo = Column(String(100))
    rol = Column(String(20), default="usuario")  # admin, supervisor, usuario
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=func.now())
    actualizado_en = Column(DateTime, default=func.now(), onupdate=func.now())


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True)
    expirado_en = Column(DateTime, nullable=False)