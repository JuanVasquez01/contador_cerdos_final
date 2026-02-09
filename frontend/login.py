import streamlit as st
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Configuración de la API
API_URL = os.getenv("API_URL", "http://localhost:8000")


def mostrar_pagina_login():
    """Mostrar página de login"""

    # Estilos CSS para login
    st.markdown("""
    <style>
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-title {
            font-size: 2rem;
            color: #d5dee6;
            font-weight: bold;
        }
        .login-subtitle {
            color: #64748B;
            margin-top: 0.5rem;
        }
        .stButton > button {
            width: 100%;
            margin-top: 1rem;
        }
        .error-message {
            color: #EF4444;
            padding: 10px;
            border-radius: 5px;
            background: #FEE2E2;
            margin: 1rem 0;
        }
        .success-message {
            color: #10B981;
            padding: 10px;
            border-radius: 5px;
            background: #D1FAE5;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Contenedor principal
    #st.markdown('<div class="login-container">', unsafe_allow_html=True)

    # Logo
    try:
        logo_path = r"D:\codigos\contador_cerdos_final\image\logo1sinfondo.png"
        if os.path.exists(logo_path):
            from PIL import Image
            logo = Image.open(logo_path)
            st.image(logo, width=150)
    except:
        pass

    # Título
    st.markdown('<div class="login-header">', unsafe_allow_html=True)
    st.markdown('<h1 class="login-title">🔐 Iniciar Sesión</h1>', unsafe_allow_html=True)
    st.markdown('<p class="login-subtitle">Sistema de Conteo de Cerdos</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Formulario de login
    with st.form("login_form"):
        username = st.text_input("👤 Nombre de usuario", placeholder="Ingrese su usuario")
        password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")

        remember_me = st.checkbox("Recordarme")

        submit_button = st.form_submit_button("🚀 Iniciar Sesión", type="primary")

    # Botón de recuperar contraseña
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("¿Olvidó su contraseña?", type="secondary", use_container_width=True):
            st.info("Contacte al administrador del sistema")

    # Manejar envío del formulario
    if submit_button:
        if not username or not password:
            st.error("⚠️ Por favor complete todos los campos")
        else:
            with st.spinner("🔐 Verificando credenciales..."):
                try:
                    # Llamar a la API de login
                    response = requests.post(
                        f"{API_URL}/login",
                        data={"username": username, "password": password},
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()

                        # Guardar en session_state
                        st.session_state["access_token"] = data["access_token"]
                        st.session_state["token_type"] = data["token_type"]
                        st.session_state["user"] = data["user"]
                        st.session_state["authenticated"] = True

                        # Si se seleccionó "Recordarme", guardar en cookies (simulado)
                        if remember_me:
                            st.session_state["remember_me"] = True

                        st.success("✅ ¡Inicio de sesión exitoso!")
                        #st.balloons()
                        time.sleep(1)

                        # Marcar para redirección y recargar
                        st.session_state["login_complete"] = True
                        st.experimental_rerun()

                    elif response.status_code == 401:
                        st.error("❌ Usuario o contraseña incorrectos")
                    elif response.status_code == 400:
                        error_data = response.json()
                        st.error(f"❌ {error_data.get('detail', 'Usuario inactivo')}")
                    else:
                        st.error("❌ Error en el servidor. Intente más tarde.")

                except requests.exceptions.ConnectionError:
                    st.error("❌ No se puede conectar con el servidor. Verifique que el backend esté ejecutándose.")
                except requests.exceptions.Timeout:
                    st.error("❌ Tiempo de espera agotado. Intente nuevamente.")
                except Exception as e:
                    st.error(f"❌ Error inesperado: {str(e)}")

    # Información del sistema
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #64748B; font-size: 0.9rem;'>
        <p>💻 <strong>Dashboard Analítico v3.0</strong></p>
        <p>Sistema de Conteo Inteligente</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()  # Detener ejecución


def verificar_autenticacion():
    """Verificar si el usuario está autenticado"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        # Mostrar página de login
        mostrar_pagina_login()
        st.stop()  # Detener ejecución si no está autenticado

    # Verificar token con el backend
    try:
        headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        response = requests.get(
            f"{API_URL}/verify-token",
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            st.session_state["authenticated"] = False
            mostrar_pagina_login()
            st.stop()

    except:
        st.session_state["authenticated"] = False
        mostrar_pagina_login()
        st.stop()


def cerrar_sesion():
    """Cerrar sesión del usuario"""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        requests.post(f"{API_URL}/logout", headers=headers, timeout=5)
    except:
        pass

    # Limpiar session_state
    for key in ["authenticated", "access_token", "token_type", "user", "remember_me", "login_complete"]:
        if key in st.session_state:
            del st.session_state[key]

    st.experimental_rerun()


def obtener_usuario_actual():
    """Obtener información del usuario actual"""
    return st.session_state.get("user", {})


def tiene_permiso(rol_requerido="usuario"):
    """Verificar si el usuario tiene el rol requerido"""
    usuario = obtener_usuario_actual()
    roles_hierarquia = {"admin": 3, "supervisor": 2, "usuario": 1}

    rol_usuario = usuario.get("rol", "usuario")

    # Comparar jerarquía de roles
    return roles_hierarquia.get(rol_usuario, 0) >= roles_hierarquia.get(rol_requerido, 0)


if __name__ == "__main__":
    # Cuando se ejecuta directamente, mostrar login
    mostrar_pagina_login()