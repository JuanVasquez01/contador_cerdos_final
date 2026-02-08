# auth.py - VERSIÓN CORREGIDA COMPLETA
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db
from models import Usuario, TokenBlacklist
from schemas import TokenData

load_dotenv()

# Configuración
SECRET_KEY = os.getenv("SECRET_KEY", "123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

# USAR pbkdf2_sha256 EN LUGAR DE bcrypt TEMPORALMENTE
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],  # Cambiado de ["bcrypt"]
    deprecated="auto",
    pbkdf2_sha256__default_rounds=30000
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Funciones de contraseña CORREGIDAS
def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


def get_password_hash(password):
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Error hashing password: {e}")
        # Fallback simple
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


# Funciones JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, db: Session):
    try:
        # Verificar si el token está en la lista negra
        token_blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
        if token_blacklisted:
            return None

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        rol: str = payload.get("rol")
        if username is None:
            return None

        token_data = TokenData(username=username, rol=rol)
        return token_data
    except JWTError:
        return None


# Obtener usuario actual
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(token, db)
    if token_data is None:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.username == token_data.username).first()
    if user is None or not user.activo:
        raise credentials_exception

    return user


# Verificar roles
def verificar_rol(usuario: Usuario, rol_requerido: str):
    if usuario.rol != rol_requerido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para realizar esta acción"
        )
    return True


# Agregar token a lista negra
def agregar_token_blacklist(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            token_blacklist = TokenBlacklist(token=token, expirado_en=exp_datetime)
            db.add(token_blacklist)
            db.commit()
    except JWTError:
        pass