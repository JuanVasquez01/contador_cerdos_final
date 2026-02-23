from database import SessionLocal
from models import Usuario
from auth import get_password_hash


def init_db():
    db = SessionLocal()

    # Verificar si el usuario ya existe para no duplicarlo
    admin = db.query(Usuario).filter(Usuario.username == "juanV").first()

    if not admin:
        # Generar el hash de la contraseña temporal
        hashed_password = get_password_hash("admin123")

        # Crear el objeto del usuario administrador
        db_usuario = Usuario(
            username="juanV",
            email="investigacion.desarrollo@aliar.com.co",
            hashed_password=hashed_password,
            nombre_completo="Juan Vasquez",
            rol="admin",
            activo=True
        )

        # Guardar en la base de datos
        db.add(db_usuario)
        db.commit()

        print("✅ Usuario administrador creado exitosamente.")
        print("👤 Usuario: juanV")
        print("🔑 Contraseña temporal: admin123")
    else:
        print("⚠️ El usuario administrador ya existe en la base de datos.")

    db.close()


if __name__ == "__main__":
    init_db()