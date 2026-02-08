# init_db.py - VERSIÓN ACTUALIZADA
import psycopg2
from passlib.context import CryptContext


def inicializar_base_datos():
    """Crear tablas de usuarios si no existen"""

    try:
        # Conexión a PostgreSQL
        conn = psycopg2.connect(
            dbname="contador_cerdos",
            user="postgres",
            password="a1b2c3d4",
            host="localhost",
            port="5432"
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Crear tabla usuarios si no existe
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS usuarios
                       (
                           id
                           SERIAL
                           PRIMARY
                           KEY,
                           username
                           VARCHAR
                       (
                           50
                       ) UNIQUE NOT NULL,
                           email VARCHAR
                       (
                           100
                       ) UNIQUE NOT NULL,
                           hashed_password VARCHAR
                       (
                           255
                       ) NOT NULL,
                           nombre_completo VARCHAR
                       (
                           100
                       ),
                           rol VARCHAR
                       (
                           20
                       ) DEFAULT 'usuario',
                           activo BOOLEAN DEFAULT TRUE,
                           creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );
                       """)

        # Crear tabla token_blacklist si no existe
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS token_blacklist
                       (
                           id
                           SERIAL
                           PRIMARY
                           KEY,
                           token
                           VARCHAR
                       (
                           500
                       ) UNIQUE NOT NULL,
                           expirado_en TIMESTAMP NOT NULL
                           );
                       """)

        # Crear índices
        cursor.execute("""
                       CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);
                       CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
                       CREATE INDEX IF NOT EXISTS idx_token_blacklist_token ON token_blacklist(token);
                       """)

        # Verificar si existe el usuario admin
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        admin_exists = cursor.fetchone()[0]

        if admin_exists == 0:
            # Crear hash de contraseña usando pbkdf2_sha256 (igual que en auth.py)
            pwd_context = CryptContext(
                schemes=["pbkdf2_sha256"],
                deprecated="auto",
                pbkdf2_sha256__default_rounds=30000
            )

            hashed_password = pwd_context.hash("admin123")

            cursor.execute("""
                           INSERT INTO usuarios (username, email, hashed_password, nombre_completo, rol)
                           VALUES (%s, %s, %s, %s, %s)
                           """, ('admin', 'admin@sistema.com', hashed_password, 'Administrador del Sistema', 'admin'))

            print("✅ Usuario admin creado:")
            print("   Usuario: admin")
            print("   Contraseña: admin123")
            print("   Rol: admin")

        print("✅ Base de datos inicializada correctamente")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")


if __name__ == "__main__":
    inicializar_base_datos()