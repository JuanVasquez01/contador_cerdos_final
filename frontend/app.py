# app.py - DASHBOARD COMPLETO CON GESTIÓN DE USUARIOS
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import psycopg2
import calendar
from dateutil.relativedelta import relativedelta
import warnings
import io
import base64
from io import BytesIO
import xlsxwriter
from fpdf import FPDF
import tempfile
import os
import time
from PIL import Image
from dotenv import load_dotenv
from login import verificar_autenticacion, cerrar_sesion, obtener_usuario_actual

load_dotenv()
warnings.filterwarnings('ignore')

# ==================== CONFIGURACIÓN ====================
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ==================== VERIFICAR AUTENTICACIÓN PRIMERO ====================
# Si viene del login con flag, limpiarlo
if "login_complete" in st.session_state:
    del st.session_state["login_complete"]

# Verificar autenticación (esto mostrará login si no está autenticado)
verificar_autenticacion()

# ==================== CONFIGURAR PÁGINA (SOLO UNA VEZ) ====================
st.set_page_config(
    page_title="Dashboard Analítico - Sistema de Conteo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DASHBOARD ====================
# Obtener usuario actual
usuario = obtener_usuario_actual()

# Sidebar con información del usuario
with st.sidebar:
    st.title(f"👤 {usuario.get('username', 'Usuario')}")
    st.write(f"**Rol:** {usuario.get('rol', 'usuario')}")
    st.write(f"**Email:** {usuario.get('email', '')}")

    st.markdown("---")

    if st.button("🚪 Cerrar Sesión", type="primary", use_container_width=True):
        cerrar_sesion()

    st.markdown("---")

# ==================== CONFIGURACIÓN DE BASE DE DATOS ====================
DATABASE_CONFIG = {
    'dbname': 'contador_cerdos',
    'user': 'postgres',
    'password': 'a1b2c3d4',
    'host': 'localhost',
    'port': '5432'
}

#DATABASE_CONFIG = {
    #'dbname': os.getenv("DB_NAME", "contador_cerdos"),
   # 'user': os.getenv("DB_USER", "postgres"),
   # 'password': os.getenv("DB_PASSWORD", "a1b2c3d4"),
   # 'host': os.getenv("DB_HOST", "db"), # 'db_contador' es el nombre del contenedor de la base de datos
  #  'port': os.getenv("DB_PORT", "5432")
#}


# ==================== FUNCIONES PARA LOGOS MEJORADAS ====================
def cargar_logo(ruta, tamaño=(200, 80)):
    """Cargar y redimensionar logo manteniendo calidad"""
    try:
        img = Image.open(ruta)
        img.thumbnail(tamaño, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        st.warning(f"No se pudo cargar el logo: {e}")
        return None


def mostrar_logo_sidebar():
    """Mostrar logo en el sidebar con mejor calidad"""
    try:
        logo_path = "./image/logo.png"
        if os.path.exists(logo_path):
            logo = cargar_logo(logo_path, tamaño=(300, 120))
            if logo:
                st.sidebar.image(logo, width=200)
                st.sidebar.markdown("---")
    except Exception as e:
        st.sidebar.info("Logo no disponible")


# ==================== ESTILOS CSS MEJORADAS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1E3A8A, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 10px;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3A7094;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #3B82F6;
        padding-left: 15px;
        background: #3A7094;
        padding: 10px;
        border-radius: 5px;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 12px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    .metric-title {
        font-size: 0.85rem;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 5px 0;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
    }
    .metric-delta {
        font-size: 0.8rem;
        opacity: 0.9;
        background: rgba(255,255,255,0.15);
        padding: 2px 6px;
        border-radius: 10px;
        display: inline-block;
        margin-top: 5px;
    }
    .filter-card {
        background: #3A7094;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .user-form {
        background: #f8fafc;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ==================== CONEXIÓN BASE DE DATOS ====================
@st.cache_resource(ttl=300)
def get_db_connection():
    """Establecer conexión a la base de datos"""
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión a la base de datos: {str(e)}")
        return None


# ==================== FUNCIONES DE DATOS MEJORADAS ====================
@st.cache_data(ttl=300)
def cargar_datos_completos():
    """Cargar todos los datos de la base de datos con lotes"""
    conn = get_db_connection()
    if conn:
        try:
            query = """
                    SELECT *,
                           EXTRACT(HOUR FROM hora_inicio_embarque)                        as hora_inicio,
                           EXTRACT(DOW FROM fecha_hora_registro)                          as dia_semana,
                           EXTRACT(EPOCH FROM (hora_fin_embarque - hora_inicio_embarque)) as duracion_segundos,
                           CASE
                               WHEN EXTRACT(DOW FROM fecha_hora_registro) IN (0, 6) THEN 'Fin de Semana'
                               ELSE 'Día Laboral'
                               END                                                        as tipo_dia
                    FROM registro_embarque
                    ORDER BY fecha_hora_registro DESC
                    """
            df = pd.read_sql(query, conn)
            conn.close()

            if not df.empty:
                datetime_cols = ['fecha_hora_registro', 'hora_inicio_embarque', 'hora_fin_embarque']
                for col in datetime_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])

                if 'fecha_hora_registro' in df.columns:
                    df['anio'] = df['fecha_hora_registro'].dt.year
                    df['mes'] = df['fecha_hora_registro'].dt.month
                    df['fecha'] = df['fecha_hora_registro'].dt.date
                    df['semana'] = df['fecha_hora_registro'].dt.isocalendar().week
                    df['trimestre'] = df['fecha_hora_registro'].dt.quarter
                    df['mes_nombre'] = df['fecha_hora_registro'].dt.strftime('%B')
                    df['dia_nombre'] = df['fecha_hora_registro'].dt.strftime('%A')

                if 'duracion_segundos' in df.columns and 'total_neto_cerdos' in df.columns:
                    df['duracion_minutos'] = df['duracion_segundos'] / 60
                    df['eficiencia'] = np.where(
                        df['duracion_segundos'] > 0,
                        df['total_neto_cerdos'] / (df['duracion_segundos'] / 3600),
                        0
                    )

                if 'total_neto_cerdos' in df.columns:
                    df['categoria_volumen'] = pd.cut(df['total_neto_cerdos'],
                                                     bins=[0, 50, 100, 200, float('inf')],
                                                     labels=['Muy Bajo', 'Bajo', 'Medio', 'Alto'])

                if 'lote_cerdos' not in df.columns:
                    df['lote_cerdos'] = 'Lote-' + (df.index + 1).astype(str).str.zfill(3)
                else:
                    df['lote_cerdos'] = df['lote_cerdos'].fillna('Sin Lote')

            return df
        except Exception as e:
            st.error(f"❌ Error al cargar datos: {str(e)}")
            return pd.DataFrame()
    return pd.DataFrame()


@st.cache_data(ttl=300)
def obtener_metricas_generales(df):
    """Calcular métricas generales del sistema mejoradas"""
    if df.empty:
        return {}

    if 'fecha' not in df.columns and 'fecha_hora_registro' in df.columns:
        df = df.copy()
        df['fecha'] = df['fecha_hora_registro'].dt.date

    hoy = datetime.now().date()
    ayer = hoy - timedelta(days=1)
    semana_pasada = hoy - timedelta(days=7)
    mes_pasado = hoy - relativedelta(months=1)

    df_hoy = df[df['fecha'] == hoy] if 'fecha' in df.columns else pd.DataFrame()
    df_ayer = df[df['fecha'] == ayer] if 'fecha' in df.columns else pd.DataFrame()
    df_semana = df[df['fecha'] >= semana_pasada] if 'fecha' in df.columns else pd.DataFrame()
    df_mes = df[df['fecha'] >= mes_pasado] if 'fecha' in df.columns else pd.DataFrame()

    metricas = {
        'total_embarques': len(df),
        'total_cerdos': df['total_neto_cerdos'].sum() if 'total_neto_cerdos' in df.columns else 0,
        'promedio_cerdos': df['total_neto_cerdos'].mean() if 'total_neto_cerdos' in df.columns else 0,
        'total_lotes': df['lote_cerdos'].nunique() if 'lote_cerdos' in df.columns else 0,
        'embarques_hoy': len(df_hoy),
        'cerdos_hoy': df_hoy[
            'total_neto_cerdos'].sum() if not df_hoy.empty and 'total_neto_cerdos' in df_hoy.columns else 0,
        'embarques_ayer': len(df_ayer),
        'cerdos_ayer': df_ayer[
            'total_neto_cerdos'].sum() if not df_ayer.empty and 'total_neto_cerdos' in df_ayer.columns else 0,
        'embarques_semana': len(df_semana),
        'cerdos_semana': df_semana[
            'total_neto_cerdos'].sum() if not df_semana.empty and 'total_neto_cerdos' in df_semana.columns else 0,
        'embarques_mes': len(df_mes),
        'cerdos_mes': df_mes[
            'total_neto_cerdos'].sum() if not df_mes.empty and 'total_neto_cerdos' in df_mes.columns else 0,
        'eficiencia_promedio': df['eficiencia'].mean() if 'eficiencia' in df.columns else 0,
        'duracion_promedio': df['duracion_minutos'].mean() if 'duracion_minutos' in df.columns else 0,
        'origenes_unicos': df['sitio_origen'].nunique() if 'sitio_origen' in df.columns else 0,
        'destinos_unicos': df['sitio_destino'].nunique() if 'sitio_destino' in df.columns else 0,
        'tendencia_7dias': 0,
        'tendencia_30dias': 0,
    }

    return metricas


# ==================== FUNCIONES DE EXPORTACIÓN ====================
class PDFWithLogo(FPDF):
    def header(self):
        try:
            logo1_path = "./image/logo1sinfondo.png"
            if os.path.exists(logo1_path):
                self.image(logo1_path, x=170, y=8, w=30, h=15)
        except:
            pass
        self.set_font('Arial', 'B', 16)
        self.cell(0, 20, 'Reporte de Conteo de Cerdos', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        try:
            logo_path = "./image/logo.png"
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=self.get_y() - 5, w=20, h=10)
        except:
            pass
        self.cell(0, 10, f'Página {self.page_no()} / {{nb}}', 0, 0, 'C')
        self.ln(5)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 5, 'Sistema de Conteo de Cerdos - Reporte generado automáticamente', 0, 0, 'C')


# ==================== FUNCIÓN PDF CON TEXTO MULTILÍNEA ====================
def exportar_a_pdf(df, titulo="Reporte de Conteo de Cerdos"):
    """Exportar DataFrame a PDF con texto que se ajusta en múltiples líneas"""

    class PDFMultilinea(FPDF):
        def header(self):
            try:
                logo1_path = "./image/logo1sinfondo.png"
                if os.path.exists(logo1_path):
                    self.image(logo1_path, x=10, y=8, w=35, h=15)
            except:
                pass

            self.set_font('Arial', 'B', 16)
            self.cell(0, 15, 'REPORTE DE CONTEO DE CERDOS', 0, 1, 'C')
            self.set_font('Arial', 'I', 10)
            self.cell(0, 5, 'Sistema de Gestión de Embarques', 0, 1, 'C')
            self.line(10, 30, 200, 30)
            self.ln(10)

        def multi_cell_table(self, w, h, txt, border=0, align='L', fill=False, max_lines=None):
            """Versión mejorada de multi_cell para tablas"""
            txt = str(txt)

            # Si el texto cabe en una línea, usar cell normal
            if self.get_string_width(txt) <= w:
                self.cell(w, h, txt, border, 0, align, fill)
                return h

            # Calcular cuántas líneas se necesitan
            lines = []
            words = txt.split(' ')
            current_line = ''

            for word in words:
                test_line = f"{current_line} {word}".strip()
                if self.get_string_width(test_line) <= w:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            # Limitar líneas si se especifica
            if max_lines and len(lines) > max_lines:
                lines = lines[:max_lines]
                if len(lines) == max_lines:
                    lines[-1] = lines[-1][:self.get_string_width_inverse(w - 10)] + '...'

            # Dibujar múltiples líneas
            x = self.get_x()
            y = self.get_y()

            for i, line in enumerate(lines):
                if i > 0:  # Si no es la primera línea
                    self.set_xy(x, self.get_y() + h / 2)  # Espaciado entre líneas

                self.cell(w, h, line, border, 2, align, fill)
                if i < len(lines) - 1:  # Si no es la última línea
                    self.set_xy(x, self.get_y())

            # Calcular altura total utilizada
            altura_total = (len(lines) * h) + ((len(lines) - 1) * (h / 2))
            return altura_total

    pdf = PDFMultilinea()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Información del reporte
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
    pdf.cell(0, 8, f"Total de registros: {len(df):,}", 0, 1)
    pdf.ln(5)

    # Logo central
    try:
        logo_path = r"D:\codigos\contador_cerdos\imagenes\logo.png"
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=(210 - 60) / 2, y=50, w=60, h=30)
            pdf.ln(35)
    except:
        pass

    # Estadísticas principales
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Estadísticas Principales:", 0, 1)
    pdf.set_font("Arial", '', 10)

    estadisticas = [
        f"Total de cerdos: {df['total_neto_cerdos'].sum() if 'total_neto_cerdos' in df.columns else 0:,}",
        f"Total de embarques: {len(df):,}",
        f"Promedio por embarque: {df['total_neto_cerdos'].mean() if 'total_neto_cerdos' in df.columns else 0:.1f}",
        f"Total de lotes: {df['lote_cerdos'].nunique() if 'lote_cerdos' in df.columns else 0}",
        f"Orígenes únicos: {df['sitio_origen'].nunique() if 'sitio_origen' in df.columns else 0}",
        f"Destinos únicos: {df['sitio_destino'].nunique() if 'sitio_destino' in df.columns else 0}"
    ]

    for i, estadistica in enumerate(estadisticas):
        pdf.cell(0, 6, estadistica, 0, 1)
        if i == 2:
            pdf.ln(2)

    pdf.ln(8)

    # ==================== TABLA CON TEXTO MULTILÍNEA ====================
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Datos de Embarques:", 0, 1)

    # Definir configuración de columnas
    config_columnas = [
        {'campo': 'fecha', 'nombre': 'Fecha', 'ancho': 25, 'alineacion': 'C', 'max_lineas': 1},
        {'campo': 'lote_cerdos', 'nombre': 'Lote', 'ancho': 30, 'alineacion': 'C', 'max_lineas': 2},
        {'campo': 'placa_vehiculo', 'nombre': 'Placa', 'ancho': 25, 'alineacion': 'C', 'max_lineas': 1},
        {'campo': 'sitio_origen', 'nombre': 'Origen', 'ancho': 45, 'alineacion': 'L', 'max_lineas': 3},
        {'campo': 'sitio_destino', 'nombre': 'Destino', 'ancho': 45, 'alineacion': 'L', 'max_lineas': 3},
        {'campo': 'total_neto_cerdos', 'nombre': 'Cerdos', 'ancho': 25, 'alineacion': 'R', 'max_lineas': 1}
    ]

    # Filtrar columnas que existen
    config_columnas = [col for col in config_columnas if col['campo'] in df.columns]

    if not config_columnas or len(df) == 0:
        pdf.cell(0, 10, "No hay datos para mostrar", 0, 1)
        return pdf

    # Tomar muestra de datos
    df_muestra = df.head(30)

    # Calcular anchos totales y posición
    anchos = [col['ancho'] for col in config_columnas]
    total_ancho = sum(anchos)
    x_inicial = max(10, (210 - total_ancho) / 2)  # Mínimo margen izquierdo

    # ==================== FUNCIÓN PARA PROCESAR TEXTO ====================
    def procesar_texto(pdf, texto, ancho, max_lineas=None, fuente='Arial', tamaño=8):
        """Dividir texto en líneas que caben en el ancho"""
        if not isinstance(texto, str):
            texto = str(texto)

        # Si es fecha, formatear
        if isinstance(texto, datetime) or (hasattr(texto, 'strftime') and texto != 'NaT'):
            try:
                texto = texto.strftime('%d/%m/%Y')
            except:
                texto = str(texto)

        # Si es número, formatear
        if isinstance(texto, (int, float)):
            texto = f"{texto:,.0f}" if texto == int(texto) else f"{texto:,.2f}"

        # Configurar fuente temporal para cálculo
        pdf.set_font(fuente, '', tamaño)

        # Si el texto cabe en una línea, retornar como está
        if pdf.get_string_width(texto) <= ancho:
            return [texto]

        # Dividir en palabras
        palabras = texto.split(' ')
        lineas = []
        linea_actual = ''

        for palabra in palabras:
            prueba = f"{linea_actual} {palabra}".strip()

            if pdf.get_string_width(prueba) <= ancho:
                linea_actual = prueba
            else:
                if linea_actual:
                    lineas.append(linea_actual)
                linea_actual = palabra

        if linea_actual:
            lineas.append(linea_actual)

        # Limitar líneas si es necesario
        if max_lineas and len(lineas) > max_lineas:
            lineas = lineas[:max_lineas]
            # Truncar última línea si es muy larga
            if lineas:
                ultima_linea = lineas[-1]
                while pdf.get_string_width(ultima_linea + '...') > ancho and len(ultima_linea) > 3:
                    ultima_linea = ultima_linea[:-1]
                lineas[-1] = ultima_linea + '...'

        return lineas

    # ==================== DIBUJAR ENCABEZADOS ====================
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(30, 58, 138)  # Color azul oscuro
    pdf.set_text_color(255, 255, 255)  # Texto blanco

    pdf.set_x(x_inicial)
    y_inicial = pdf.get_y()

    for config in config_columnas:
        nombre = config['nombre']
        ancho = config['ancho']
        alineacion = config['alineacion']

        # Procesar texto del encabezado
        lineas_encabezado = procesar_texto(pdf, nombre, ancho, max_lineas=2, tamaño=9)

        # Calcular altura del encabezado
        altura_encabezado = len(lineas_encabezado) * 4 + 4  # 4mm por línea + padding

        # Dibujar encabezado multilínea
        x_actual = pdf.get_x()
        y_actual = pdf.get_y()

        for i, linea in enumerate(lineas_encabezado):
            if i == 0:
                pdf.cell(ancho, altura_encabezado, linea, 1, 2, alineacion, fill=True)
                pdf.set_xy(x_actual + ancho, y_actual)
            else:
                pdf.set_xy(x_actual, pdf.get_y())
                pdf.cell(ancho, 4, linea, 'LR', 2, alineacion, fill=True)
                pdf.set_xy(x_actual + ancho, pdf.get_y() - 4)

        # Restaurar posición para siguiente columna
        pdf.set_xy(x_actual + ancho, y_actual)

    pdf.ln(altura_encabezado)

    # Restaurar color de texto
    pdf.set_text_color(0, 0, 0)

    # ==================== DIBUJAR DATOS ====================
    pdf.set_font("Arial", '', 8)

    # Altura base de fila (se ajustará dinámicamente)
    altura_base_fila = 6
    fill = False

    for idx, fila in df_muestra.iterrows():
        # Calcular altura máxima necesaria para esta fila
        alturas_por_columna = []

        for config in config_columnas:
            campo = config['campo']
            ancho = config['ancho']
            max_lineas = config.get('max_lineas', 3)

            if campo in fila:
                valor = fila[campo]
                lineas = procesar_texto(pdf, valor, ancho, max_lineas, tamaño=8)
                altura_necesaria = len(lineas) * 3 + 2  # 3mm por línea + padding
                alturas_por_columna.append(altura_necesaria)

        altura_fila = max(alturas_por_columna) if alturas_por_columna else altura_base_fila

        # Dibujar fila
        pdf.set_x(x_inicial)
        y_fila_inicio = pdf.get_y()

        for i, config in enumerate(config_columnas):
            campo = config['campo']
            ancho = config['ancho']
            alineacion = config['alineacion']
            max_lineas = config.get('max_lineas', 3)

            if campo in fila:
                valor = fila[campo]
                lineas = procesar_texto(pdf, valor, ancho, max_lineas, tamaño=8)

                # Configurar color de fondo
                if fill:
                    pdf.set_fill_color(240, 240, 240)
                else:
                    pdf.set_fill_color(255, 255, 255)

                # Dibujar celda con múltiples líneas
                x_celda = pdf.get_x()
                y_celda = pdf.get_y()

                for j, linea in enumerate(lineas):
                    if j == 0:
                        # Primera línea - dibujar bordes completos
                        bordes = 'LTR' if i == 0 else 'TR'
                        if i == len(config_columnas) - 1:
                            bordes += 'R'
                        pdf.cell(ancho, altura_fila, linea, bordes, 2, alineacion, fill=fill)
                    else:
                        # Líneas adicionales - solo bordes laterales
                        pdf.set_xy(x_celda, pdf.get_y())
                        pdf.cell(ancho, 3, linea, 'LR', 2, alineacion, fill=fill)

                # Rellenar espacio restante si hay menos líneas
                lineas_dibujadas = len(lineas)
                if lineas_dibujadas * 3 < altura_fila:
                    espacio_extra = altura_fila - (lineas_dibujadas * 3)
                    pdf.set_xy(x_celda, pdf.get_y())
                    pdf.cell(ancho, espacio_extra, '', 'LRB', 2, alineacion, fill=fill)

                # Posicionar para siguiente columna
                pdf.set_xy(x_celda + ancho, y_celda)

        # Mover a siguiente fila
        pdf.set_xy(x_inicial, y_fila_inicio + altura_fila)
        fill = not fill

    # ==================== PIE INFORMATIVO ====================
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, f"*Mostrando {len(df_muestra)} de {len(df)} registros. Texto ajustado automáticamente.*", 0, 1, 'C')

    if len(df) > 30:
        pdf.cell(0, 5, f"*Nota: Para ver todos los registros, exporte en formato Excel.*", 0, 1, 'C')

    return pdf

def exportar_a_excel(df):
    """Exportar DataFrame a Excel"""
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Datos Completos', index=False)

        resumen_data = {
            'Métrica': ['Total Embarques', 'Total Cerdos', 'Promedio por Embarque',
                        'Total Lotes', 'Orígenes Únicos', 'Destinos Únicos'],
            'Valor': [
                len(df),
                df['total_neto_cerdos'].sum() if 'total_neto_cerdos' in df.columns else 0,
                df['total_neto_cerdos'].mean() if 'total_neto_cerdos' in df.columns else 0,
                df['lote_cerdos'].nunique() if 'lote_cerdos' in df.columns else 0,
                df['sitio_origen'].nunique() if 'sitio_origen' in df.columns else 0,
                df['sitio_destino'].nunique() if 'sitio_destino' in df.columns else 0
            ]
        }
        resumen_df = pd.DataFrame(resumen_data)
        resumen_df.to_excel(writer, sheet_name='Resumen', index=False)

        workbook = writer.book

        try:
            logo1_path = "./image/logo1sinfondo.png"
            if os.path.exists(logo1_path):
                worksheet = writer.sheets['Resumen']
                worksheet.insert_image('A1', logo1_path, {'x_scale': 0.4, 'y_scale': 0.4})
        except:
            pass

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#1E3A8A',
            'font_color': 'white',
            'border': 1,
            'font_size': 10
        })

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            if sheet_name == 'Datos Completos':
                columns = df.columns
                data_df = df
            else:
                columns = resumen_df.columns
                data_df = resumen_df

            for col_num, value in enumerate(columns):
                worksheet.write(0, col_num, value, header_format)
                max_len = max(
                    data_df[value].astype(str).apply(len).max() if len(data_df) > 0 else 0,
                    len(str(value))
                ) + 2
                worksheet.set_column(col_num, col_num, min(max_len, 40))

    output.seek(0)
    return output


def exportar_a_csv(df):
    """Exportar DataFrame a CSV"""
    return df.to_csv(index=False).encode('utf-8')


# ==================== FUNCIONES DE GRÁFICOS ====================
def crear_grafico_analisis_lotes(df):
    """Crear gráfico de análisis por lotes"""
    if df.empty or 'lote_cerdos' not in df.columns:
        return None

    df_lotes = df.groupby('lote_cerdos').agg({
        'total_neto_cerdos': ['sum', 'count', 'mean']
    }).reset_index()

    df_lotes.columns = ['lote', 'total_cerdos', 'num_embarques', 'promedio_cerdos']
    df_lotes = df_lotes.sort_values('total_cerdos', ascending=False).head(15)

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Top 15 Lotes - Total Cerdos', 'Embarques por Lote'),
        vertical_spacing=0.15
    )

    fig.add_trace(
        go.Bar(
            x=df_lotes['lote'],
            y=df_lotes['total_cerdos'],
            name='Total Cerdos',
            marker_color='#6366F1'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            x=df_lotes['lote'],
            y=df_lotes['num_embarques'],
            name='N° Embarques',
            marker_color='#8B5CF6'
        ),
        row=2, col=1
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        template='plotly_white',
        hovermode='x unified'
    )

    fig.update_xaxes(title_text="Lote", row=2, col=1, tickangle=45)
    fig.update_yaxes(title_text="Total de Cerdos", row=1, col=1)
    fig.update_yaxes(title_text="Número de Embarques", row=2, col=1)

    return fig


def crear_grafico_tendencia_mensual(df):
    """Crear gráfico de tendencia mensual"""
    if df.empty:
        return None

    if 'anio' not in df.columns or 'mes' not in df.columns:
        if 'fecha_hora_registro' in df.columns:
            try:
                df = df.copy()
                df['anio'] = df['fecha_hora_registro'].dt.year
                df['mes'] = df['fecha_hora_registro'].dt.month
            except:
                return None

    try:
        df_mensual = df.groupby(['anio', 'mes']).agg({
            'total_neto_cerdos': ['sum', 'count']
        }).reset_index()

        df_mensual.columns = ['anio', 'mes', 'cerdos_total', 'embarques_total']
        df_mensual = df_mensual.sort_values(['anio', 'mes'])
        df_mensual['periodo'] = df_mensual['anio'].astype(str) + '-' + df_mensual['mes'].astype(str).str.zfill(2)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_mensual['periodo'],
            y=df_mensual['cerdos_total'],
            name='Total de Cerdos',
            marker_color='#3B82F6'
        ))

        fig.add_trace(go.Scatter(
            x=df_mensual['periodo'],
            y=df_mensual['embarques_total'],
            name='Número de Embarques',
            mode='lines+markers',
            line=dict(color='#EF4444', width=2),
            marker=dict(size=8),
            yaxis='y2'
        ))

        fig.update_layout(
            title='Tendencia Mensual',
            xaxis_title='Periodo',
            yaxis_title='Total de Cerdos',
            yaxis2=dict(
                title='Número de Embarques',
                overlaying='y',
                side='right',
                showgrid=False
            ),
            hovermode='x unified',
            showlegend=True,
            height=500,
            template='plotly_white'
        )

        fig.update_xaxes(tickangle=45)
        return fig

    except Exception as e:
        return None


# ==================== FUNCIONES PARA GESTIÓN DE USUARIOS ====================
def mostrar_gestion_usuarios():
    """Mostrar interfaz para gestión de usuarios (solo admin)"""
    usuario_actual = obtener_usuario_actual()

    if usuario_actual.get('rol') != 'admin':
        st.warning("🚫 Solo los administradores pueden acceder a esta sección")
        return

    st.markdown('<h2 class="sub-header">👥 Gestión de Usuarios</h2>', unsafe_allow_html=True)

    # Tabs para diferentes operaciones
    tab_crear, tab_listar, tab_editar = st.tabs(["➕ Crear Usuario", "📋 Listar Usuarios", "✏️ Editar Usuario"])

    with tab_crear:
        st.markdown("### Crear Nuevo Usuario")

        with st.form("form_crear_usuario"):
            col1, col2 = st.columns(2)

            with col1:
                nuevo_username = st.text_input("Nombre de usuario*", placeholder="juan.perez")
                nuevo_email = st.text_input("Email*", placeholder="juan@empresa.com")
                nuevo_nombre = st.text_input("Nombre completo", placeholder="Juan Pérez")

            with col2:
                nuevo_password = st.text_input("Contraseña*", type="password", placeholder="******")
                confirm_password = st.text_input("Confirmar contraseña*", type="password", placeholder="******")
                nuevo_rol = st.selectbox("Rol*", ["usuario", "supervisor", "admin"])

            st.caption("* Campos obligatorios")
            submitted = st.form_submit_button("✅ Crear Usuario", type="primary")

            if submitted:
                if not all([nuevo_username, nuevo_email, nuevo_password, confirm_password]):
                    st.error("❌ Todos los campos marcados con * son obligatorios")
                elif nuevo_password != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif len(nuevo_password) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres")
                else:
                    try:
                        # Obtener token del usuario actual
                        token = st.session_state.get("access_token")
                        headers = {"Authorization": f"Bearer {token}"}

                        # Datos del nuevo usuario
                        usuario_data = {
                            "username": nuevo_username,
                            "email": nuevo_email,
                            "nombre_completo": nuevo_nombre,
                            "password": nuevo_password,
                            "rol": nuevo_rol
                        }

                        # Llamar a la API para crear usuario
                        response = requests.post(
                            f"{API_URL}/usuarios/",
                            json=usuario_data,
                            headers=headers,
                            timeout=10
                        )

                        if response.status_code == 200:
                            st.success(f"✅ Usuario '{nuevo_username}' creado exitosamente")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        elif response.status_code == 400:
                            error_data = response.json()
                            st.error(f"❌ Error: {error_data.get('detail', 'Error al crear usuario')}")
                        else:
                            st.error(f"❌ Error del servidor: {response.status_code}")

                    except requests.exceptions.ConnectionError:
                        st.error("❌ No se puede conectar con el servidor")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    with tab_listar:
        st.markdown("### Lista de Usuarios Registrados")

        try:
            # Obtener token del usuario actual
            token = st.session_state.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Llamar a la API para obtener usuarios
            response = requests.get(
                f"{API_URL}/usuarios/",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                usuarios = response.json()

                if usuarios:
                    # Convertir a DataFrame para mejor visualización
                    df_usuarios = pd.DataFrame(usuarios)

                    # Formatear fechas
                    if 'creado_en' in df_usuarios.columns:
                        df_usuarios['creado_en'] = pd.to_datetime(df_usuarios['creado_en']).dt.strftime(
                            '%Y-%m-%d %H:%M')

                    # Filtrar columnas importantes
                    columnas_mostrar = ['id', 'username', 'email', 'nombre_completo', 'rol', 'activo', 'creado_en']
                    columnas_mostrar = [col for col in columnas_mostrar if col in df_usuarios.columns]

                    # Mostrar tabla
                    st.dataframe(
                        df_usuarios[columnas_mostrar],
                        use_container_width=True,
                        height=400
                    )

                    # Estadísticas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Usuarios", len(usuarios))
                    with col2:
                        usuarios_activos = sum(1 for u in usuarios if u.get('activo', True))
                        st.metric("Usuarios Activos", usuarios_activos)
                    with col3:
                        admins = sum(1 for u in usuarios if u.get('rol') == 'admin')
                        st.metric("Administradores", admins)
                else:
                    st.info("📭 No hay usuarios registrados")

            elif response.status_code == 403:
                st.error("❌ No tiene permisos para ver usuarios")
            else:
                st.error(f"❌ Error al obtener usuarios: {response.status_code}")

        except requests.exceptions.ConnectionError:
            st.error("❌ No se puede conectar con el servidor")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    with tab_editar:
        st.markdown("### Editar o Desactivar Usuario")

        try:
            # Obtener lista de usuarios primero
            token = st.session_state.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(
                f"{API_URL}/usuarios/",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                usuarios = response.json()

                if usuarios:
                    # Filtrar usuarios (no mostrar el usuario actual para no desactivarse a sí mismo)
                    usuario_actual_id = usuario_actual.get('id')
                    usuarios_filtrados = [u for u in usuarios if u['id'] != usuario_actual_id]

                    if usuarios_filtrados:
                        # Crear lista de opciones
                        opciones_usuarios = [f"{u['id']} - {u['username']} ({u['rol']})" for u in usuarios_filtrados]

                        usuario_seleccionado = st.selectbox(
                            "Seleccionar usuario a editar",
                            options=opciones_usuarios,
                            index=0
                        )

                        if usuario_seleccionado:
                            # Extraer ID del usuario seleccionado
                            usuario_id = int(usuario_seleccionado.split(" - ")[0])

                            # Buscar datos del usuario seleccionado
                            usuario_info = next((u for u in usuarios if u['id'] == usuario_id), None)

                            if usuario_info:
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.markdown("#### Información Actual")
                                    st.write(f"**ID:** {usuario_info.get('id')}")
                                    st.write(f"**Usuario:** {usuario_info.get('username')}")
                                    st.write(f"**Email:** {usuario_info.get('email')}")
                                    st.write(f"**Nombre:** {usuario_info.get('nombre_completo', 'No especificado')}")
                                    st.write(f"**Rol:** {usuario_info.get('rol')}")
                                    st.write(
                                        f"**Estado:** {'✅ Activo' if usuario_info.get('activo', True) else '❌ Inactivo'}")
                                    if 'creado_en' in usuario_info:
                                        st.write(f"**Creado:** {usuario_info.get('creado_en')}")

                                with col2:
                                    st.markdown("#### Acciones")

                                    # Cambiar estado
                                    st.markdown("**Cambiar Estado**")
                                    nuevo_estado = st.radio(
                                        "Estado del usuario:",
                                        ["Activo", "Inactivo"],
                                        index=0 if usuario_info.get('activo', True) else 1,
                                        key=f"estado_{usuario_id}"
                                    )

                                    if st.button("🔄 Actualizar Estado", key=f"btn_estado_{usuario_id}",
                                                 use_container_width=True):
                                        try:
                                            endpoint = "activar" if nuevo_estado == "Activo" else "desactivar"
                                            response = requests.patch(
                                                f"{API_URL}/usuarios/{usuario_id}/{endpoint}",
                                                headers=headers,
                                                timeout=10
                                            )

                                            if response.status_code == 200:
                                                st.success(f"✅ Usuario {nuevo_estado.lower()} correctamente")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ Error al actualizar estado")

                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")

                                    # Cambiar rol
                                    st.markdown("**Cambiar Rol**")
                                    nuevo_rol = st.selectbox(
                                        "Nuevo rol:",
                                        ["usuario", "supervisor", "admin"],
                                        index=["usuario", "supervisor", "admin"].index(
                                            usuario_info.get('rol', 'usuario')),
                                        key=f"rol_{usuario_id}"
                                    )

                                    if st.button("🎭 Cambiar Rol", key=f"btn_rol_{usuario_id}",
                                                 use_container_width=True):
                                        try:
                                            # Para cambiar rol necesitamos usar el endpoint de actualización
                                            update_data = {"rol": nuevo_rol}
                                            response = requests.put(
                                                f"{API_URL}/usuarios/{usuario_id}",
                                                json=update_data,
                                                headers=headers,
                                                timeout=10
                                            )

                                            if response.status_code == 200:
                                                st.success(f"✅ Rol cambiado a {nuevo_rol}")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ Error al cambiar rol")

                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")

                                    st.markdown("---")

                                    # Eliminar usuario (con confirmación)
                                    st.markdown("**Eliminar Usuario**")
                                    st.warning("⚠️ Esta acción es irreversible y eliminará el usuario permanentemente")

                                    with st.expander("Mostrar opción de eliminación"):
                                        confirmar = st.checkbox(
                                            f"Confirmar eliminación de {usuario_info.get('username')}",
                                            key=f"confirm_{usuario_id}")

                                        if confirmar:
                                            if st.button("🗑️ Eliminar Usuario Permanentemente",
                                                         type="secondary",
                                                         key=f"delete_{usuario_id}",
                                                         use_container_width=True):
                                                try:
                                                    response = requests.delete(
                                                        f"{API_URL}/usuarios/{usuario_id}",
                                                        headers=headers,
                                                        timeout=10
                                                    )

                                                    if response.status_code == 200:
                                                        st.success("✅ Usuario eliminado correctamente")
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Error al eliminar usuario")

                                                except Exception as e:
                                                    st.error(f"❌ Error: {str(e)}")
                    else:
                        st.info("📭 No hay otros usuarios para editar (solo existe su usuario)")
                else:
                    st.info("📭 No hay usuarios registrados")

            else:
                st.error("❌ Error al obtener usuarios")

        except requests.exceptions.ConnectionError:
            st.error("❌ No se puede conectar con el servidor")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


# ==================== INTERFAZ PRINCIPAL ====================
def main():
    # Header principal
    col_header1, col_header2, col_header3 = st.columns([3, 4, 2])

    with col_header1:
        st.empty()

    with col_header2:
        st.markdown('<h1 class="main-header">📊 Dashboard Analítico</h1>',
                    unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #64748B; margin-top: -10px;">Sistema de Conteo de Cerdos</p>',
                    unsafe_allow_html=True)

    with col_header3:
        try:
            logo1_path = "./image/logo1sinfondo.png"
            if os.path.exists(logo1_path):
                logo1 = cargar_logo(logo1_path, tamaño=(120, 80))
                if logo1:
                    st.image(logo1, width=80)
        except:
            pass

    # Cargar datos
    with st.spinner('📥 Cargando datos...'):
        df_completo = cargar_datos_completos()

    if df_completo.empty:
        st.error("No se pudieron cargar datos de la base de datos")
        return

    # Sidebar con filtros
    with st.sidebar:
        mostrar_logo_sidebar()

        st.markdown('<div class="filter-card">', unsafe_allow_html=True)
        st.markdown("### 🔍 Filtros")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if 'fecha' in df_completo.columns:
                fecha_min = df_completo['fecha'].min()
                fecha_max = df_completo['fecha'].max()
                fecha_inicio = st.date_input("Desde", value=fecha_min, key="fecha_inicio")
        with col2:
            if 'fecha' in df_completo.columns:
                fecha_fin = st.date_input("Hasta", value=fecha_max, key="fecha_fin")

        if 'lote_cerdos' in df_completo.columns:
            lote_seleccionado = st.selectbox("Lote", ["Todos"] + sorted(df_completo['lote_cerdos'].unique().tolist()))

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            aplicar_filtros = st.button("✅ Aplicar", type="primary", use_container_width=True)
        with col_b2:
            limpiar_filtros = st.button("🔄 Limpiar", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Aplicar filtros
    if limpiar_filtros:
        st.session_state.df_filtrado = df_completo.copy()
        st.rerun()

    if 'df_filtrado' not in st.session_state:
        st.session_state.df_filtrado = df_completo.copy()

    if aplicar_filtros:
        df_filtrado = df_completo.copy()

        if 'fecha' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                (df_filtrado['fecha'] >= fecha_inicio) &
                (df_filtrado['fecha'] <= fecha_fin)
                ]

        if 'lote_cerdos' in df_filtrado.columns and lote_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['lote_cerdos'] == lote_seleccionado]

        st.session_state.df_filtrado = df_filtrado

    df_filtrado = st.session_state.df_filtrado
    metricas = obtener_metricas_generales(df_filtrado)

    # ==================== SECCIÓN 1: KPIs ====================
    st.markdown('<h2 class="sub-header">📈 KPIs Principales</h2>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Embarques",
            value=f"{metricas.get('total_embarques', 0):,}",
            delta=f"{metricas.get('embarques_hoy', 0)} hoy"
        )

    with col2:
        st.metric(
            label="Total Cerdos",
            value=f"{metricas.get('total_cerdos', 0):,}",
            delta=f"{metricas.get('cerdos_hoy', 0):,} hoy"
        )

    with col3:
        st.metric(
            label="Total Lotes",
            value=metricas.get('total_lotes', 0),
            delta="únicos"
        )

    with col4:
        st.metric(
            label="Tendencia 7 días",
            value=f"{metricas.get('tendencia_7dias', 0):+.0f}",
            delta="cerdos/día"
        )

    # ==================== SECCIÓN 2: PESTAÑAS ====================
    # Verificar si es admin para mostrar pestaña de usuarios
    usuario_actual = obtener_usuario_actual()
    es_admin = usuario_actual.get('rol') == 'admin'

    if es_admin:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Análisis",
            "📈 Tendencias",
            "🔍 Detalles",
            "📥 Exportar",
            "👥 Usuarios"
        ])
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Análisis",
            "📈 Tendencias",
            "🔍 Detalles",
            "📥 Exportar"
        ])

    with tab1:
        col_analisis1, col_analisis2 = st.columns(2)

        with col_analisis1:
            st.markdown("### 📦 Distribución por Lotes")
            if 'lote_cerdos' in df_filtrado.columns:
                fig_lotes = crear_grafico_analisis_lotes(df_filtrado)
                if fig_lotes:
                    st.plotly_chart(fig_lotes, use_container_width=True)

        with col_analisis2:
            st.markdown("### 📅 Distribución por Día")
            if 'dia_nombre' in df_filtrado.columns:
                df_dia = df_filtrado.groupby('dia_nombre').agg({
                    'total_neto_cerdos': 'sum'
                }).reset_index()

                dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                dias_espanol = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                dia_map = dict(zip(dias_orden, dias_espanol))
                df_dia['dia_nombre_es'] = df_dia['dia_nombre'].map(dia_map)

                fig_dia = px.bar(
                    df_dia,
                    x='dia_nombre_es',
                    y='total_neto_cerdos',
                    title='Cerdos por Día de la Semana',
                    color='total_neto_cerdos',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_dia, use_container_width=True)

    with tab2:
        st.markdown("### 📈 Evolución Mensual")
        fig_tendencia = crear_grafico_tendencia_mensual(df_filtrado)
        if fig_tendencia:
            st.plotly_chart(fig_tendencia, use_container_width=True)

    with tab3:
        st.markdown("### 📋 Datos Detallados")

        columnas_importantes = ['fecha', 'lote_cerdos', 'sitio_origen', 'sitio_destino', 'total_neto_cerdos']
        columnas_mostrar = [col for col in columnas_importantes if col in df_filtrado.columns]

        if columnas_mostrar:
            st.dataframe(
                df_filtrado[columnas_mostrar].head(100),
                use_container_width=True,
                height=400
            )

    with tab4:
        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            st.markdown("### 📤 Exportar Datos")

            formato = st.radio(
                "Formato de exportación",
                ["Excel", "PDF", "CSV"],
                horizontal=True
            )

            nombre_base = st.text_input(
                "Nombre del archivo",
                value=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}"
            )

            if formato == "Excel":
                if st.button("📊 Exportar a Excel", use_container_width=True):
                    try:
                        excel_data = exportar_a_excel(df_filtrado)
                        st.download_button(
                            label="⬇️ Descargar Excel",
                            data=excel_data.getvalue(),
                            file_name=f"{nombre_base}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            elif formato == "PDF":
                if st.button("📄 Exportar a PDF", use_container_width=True):
                    try:
                        pdf = exportar_a_pdf(df_filtrado)
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                            pdf.output(tmp.name)
                            with open(tmp.name, 'rb') as f:
                                pdf_data = f.read()

                        st.download_button(
                            label="⬇️ Descargar PDF",
                            data=pdf_data,
                            file_name=f"{nombre_base}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        os.unlink(tmp.name)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            elif formato == "CSV":
                if st.button("📝 Exportar a CSV", use_container_width=True):
                    try:
                        csv_data = exportar_a_csv(df_filtrado)
                        st.download_button(
                            label="⬇️ Descargar CSV",
                            data=csv_data,
                            file_name=f"{nombre_base}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        with col_exp2:
            st.markdown("### 📊 Resumen")

            st.markdown("**📅 Período analizado**")
            if 'fecha' in df_filtrado.columns:
                st.write(f"{df_filtrado['fecha'].min()} al {df_filtrado['fecha'].max()}")

            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Embarques", metricas.get('total_embarques', 0))
                st.metric("Cerdos", f"{metricas.get('total_cerdos', 0):,}")
                st.metric("Lotes", metricas.get('total_lotes', 0))

            with col_res2:
                if 'eficiencia_promedio' in metricas:
                    st.metric("Eficiencia", f"{metricas.get('eficiencia_promedio', 0):.1f}")
                st.metric("Orígenes", metricas.get('origenes_unicos', 0))
                st.metric("Destinos", metricas.get('destinos_unicos', 0))

    # Manejar la pestaña de usuarios si es admin
    if es_admin:
        with tab5:
            mostrar_gestion_usuarios()

    # ==================== PIE DE PÁGINA ====================
    st.markdown("---")

    col_footer1, col_footer2 = st.columns([3, 1])

    with col_footer1:
        st.markdown("**Dashboard Analítico v3.0** • Sistema de Conteo Inteligente")
        st.markdown(f"*Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}*")

    with col_footer2:
        st.markdown(
            f"**{len(df_filtrado):,} registros** • **{df_filtrado['lote_cerdos'].nunique() if 'lote_cerdos' in df_filtrado.columns else 0} lotes**")


# ==================== EJECUCIÓN PRINCIPAL ====================
if __name__ == "__main__":
    main()