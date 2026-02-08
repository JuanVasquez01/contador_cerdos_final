#D:\codigos\contador_cerdos_final\backend\main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import uvicorn
import os

from database import engine, get_db
from models import Base, Usuario, TokenBlacklist
from schemas import (
    UsuarioCreate, UsuarioResponse, UsuarioUpdate,
    Token, LoginRequest, CambioPassword
)
from auth import (
    verify_password, create_access_token,
    get_current_user, get_password_hash,
    agregar_token_blacklist, verificar_rol
)
from crud import (
    get_usuario_by_username, create_usuario,
    get_usuarios, update_usuario, delete_usuario,
    cambiar_estado_usuario
)

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Autenticación - Sistema de Conteo",
    description="API para gestión de usuarios y autenticación",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== ENDPOINTS DE AUTENTICACIÓN ====================

@app.post("/login", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    usuario = get_usuario_by_username(db, username=form_data.username)

    if not usuario or not verify_password(form_data.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )

    # Crear token de acceso
    access_token_expires = timedelta(minutes=60 * 24)  # 24 horas
    access_token = create_access_token(
        data={"sub": usuario.username, "rol": usuario.rol},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": usuario
    }


@app.post("/logout")
async def logout(
        token: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Invalidar token actual"""
    agregar_token_blacklist(token, db)
    return {"message": "Sesión cerrada correctamente"}


@app.post("/cambiar-password")
async def cambiar_password(
        cambio_password: CambioPassword,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Cambiar contraseña del usuario actual"""
    # Verificar contraseña actual
    if not verify_password(cambio_password.password_actual, usuario_actual.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )

    # Actualizar contraseña
    usuario_actual.hashed_password = get_password_hash(cambio_password.password_nuevo)
    db.commit()

    return {"message": "Contraseña cambiada correctamente"}


# ==================== ENDPOINTS DE USUARIOS ====================

@app.post("/usuarios/", response_model=UsuarioResponse)
async def crear_usuario(
        usuario: UsuarioCreate,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Crear nuevo usuario (solo admin)"""
    verificar_rol(usuario_actual, "admin")
    return create_usuario(db=db, usuario=usuario)


@app.get("/usuarios/", response_model=list[UsuarioResponse])
async def leer_usuarios(
        skip: int = 0,
        limit: int = 100,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Obtener lista de usuarios (solo admin)"""
    verificar_rol(usuario_actual, "admin")
    usuarios = get_usuarios(db, skip=skip, limit=limit)
    return usuarios


@app.get("/usuarios/me", response_model=UsuarioResponse)
async def leer_usuario_actual(usuario_actual: Usuario = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    return usuario_actual


@app.put("/usuarios/{usuario_id}", response_model=UsuarioResponse)
async def actualizar_usuario(
        usuario_id: int,
        usuario_update: UsuarioUpdate,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Actualizar usuario"""
    return update_usuario(db, usuario_id, usuario_update, usuario_actual)


@app.delete("/usuarios/{usuario_id}")
async def eliminar_usuario(
        usuario_id: int,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Eliminar usuario (solo admin)"""
    return delete_usuario(db, usuario_id, usuario_actual)


@app.patch("/usuarios/{usuario_id}/activar")
async def activar_usuario(
        usuario_id: int,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Activar/desactivar usuario (solo admin)"""
    return cambiar_estado_usuario(db, usuario_id, True, usuario_actual)


@app.patch("/usuarios/{usuario_id}/desactivar")
async def desactivar_usuario(
        usuario_id: int,
        usuario_actual: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Activar/desactivar usuario (solo admin)"""
    return cambiar_estado_usuario(db, usuario_id, False, usuario_actual)


# ==================== ENDPOINTS DE VERIFICACIÓN ====================

@app.get("/verify-token")
async def verify_token_endpoint(usuario_actual: Usuario = Depends(get_current_user)):
    """Verificar si el token es válido"""
    return {"valid": True, "user": usuario_actual}


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Endpoint para verificar estado del servidor"""
    return {"status": "healthy", "service": "auth-api"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)