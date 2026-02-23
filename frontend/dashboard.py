import streamlit as st
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
from fpdf import FPDF, HTMLMixin
import tempfile
import os
from PIL import Image


warnings.filterwarnings('ignore')

# ==================== CONFIGURACIÓN ====================
st.set_page_config(
    page_title="Dashboard Analítico - Sistema de Conteo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de base de datos
DATABASE_CONFIG = {
    'dbname': 'contador_cerdos',
    'user': 'postgres',
    'password': 'a1b2c3d4',
    'host': 'localhost',
    'port': '5432'
}


# ==================== FUNCIONES PARA LOGOS MEJORADAS ====================
def cargar_logo(ruta, tamaño=(200, 80)):
    """Cargar y redimensionar logo manteniendo calidad"""
    try:
        img = Image.open(ruta)
        # Mantener proporciones si se especifica solo un tamaño
        img.thumbnail(tamaño, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        st.warning(f"No se pudo cargar el logo: {e}")
        return None


def mostrar_logo_sidebar():
    """Mostrar logo en el sidebar con mejor calidad"""
    try:
        logo_path = r"/frontend/image\logo.png"
        if os.path.exists(logo_path):
            # Cargar con mayor resolución
            logo = cargar_logo(logo_path, tamaño=(300, 120))
            if logo:
                st.sidebar.image(logo, width=200)
                st.sidebar.center(logo)
                st.sidebar.markdown("---")
    except Exception as e:
        st.sidebar.info("Logo no disponible")


# ==================== ESTILOS CSS MEJORADOS ====================
st.markdown("""
<style>
    /* Main styling */
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

    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 5px 0;
    }

    .header-logo {
        text-align: right;
        padding: 5px;
    }

    /* Ajustes para mejor espaciado */
    .st-emotion-cache-1dp5vir {
        margin-top: -10px;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* Mejorar visualización de tabs */
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-size: 0.9rem;
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
                # Convertir tipos de datos
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

                # Calcular eficiencia
                if 'duracion_segundos' in df.columns and 'total_neto_cerdos' in df.columns:
                    df['duracion_minutos'] = df['duracion_segundos'] / 60
                    df['eficiencia'] = np.where(
                        df['duracion_segundos'] > 0,
                        df['total_neto_cerdos'] / (df['duracion_segundos'] / 3600),
                        0
                    )

                # Categorizar por volumen
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

    # Filtrar datos
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
        'tendencia_7dias': calcular_tendencia(df, dias=7),
        'tendencia_30dias': calcular_tendencia(df, dias=30),
    }

    return metricas


def calcular_tendencia(df, dias=7):
    """Calcular tendencia de crecimiento en los últimos N días"""
    if df.empty or len(df) < 2:
        return 0

    if 'fecha' not in df.columns or 'total_neto_cerdos' not in df.columns:
        return 0

    fecha_limite = datetime.now().date() - timedelta(days=dias)
    df_reciente = df[df['fecha'] >= fecha_limite]

    if len(df_reciente) < 2:
        return 0

    diario = df_reciente.groupby('fecha')['total_neto_cerdos'].sum().reset_index()

    if len(diario) < 2:
        return 0

    x = np.arange(len(diario))
    y = diario['total_neto_cerdos'].values
    if len(y) > 1:
        slope = np.polyfit(x, y, 1)[0]
        return slope

    return 0


# ==================== FUNCIONES DE EXPORTACIÓN MEJORADAS ====================
class PDFWithLogo(FPDF):
    def header(self):
        """Encabezado profesional para el PDF"""
        # Configurar márgenes
        self.set_margins(10, 15, 10)

        # ===== LOGO IZQUIERDO =====
        try:
            logo1_path = r"/frontend/image\logo1sinfondo.png"
            if os.path.exists(logo1_path):
                # Logo en esquina superior izquierda
                self.image(logo1_path, x=10, y=8, w=35, h=50)
        except:
            pass

        # ===== LOGO DERECHO =====
        try:
            logo_path = r"D:\codigos\contador_cerdos\imagenes\logo.png"
            if os.path.exists(logo_path):
                # Logo en esquina superior derecha
                self.image(logo_path, x=165, y=8, w=35, h=15)
        except:
            pass

        # ===== TÍTULO PRINCIPAL CENTRADO =====
        self.set_font('Arial', 'B', 18)
        self.set_text_color(30, 58, 138)  # Color azul oscuro #1E3A

        # Título
        self.set_font('Arial', 'B', 16)
        self.cell(0, 20, 'Reporte de Conteo de Cerdos', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Posición a 1.5 cm del final
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)

        # Logo en el pie de página (logo.png)
        try:
            logo_path = r"D:\codigos\contador_cerdos\imagenes\logo.png"
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=self.get_y() - 5, w=20, h=10)
        except:
            pass

        # Texto del pie de página
        self.cell(0, 10, f'Página {self.page_no()} / {{nb}}', 0, 0, 'C')
        self.ln(5)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 5, 'Sistema de Conteo de Cerdos - Reporte generado automáticamente', 0, 0, 'C')


def exportar_a_pdf(df, titulo="Reporte de Conteo de Cerdos"):
    """Exportar DataFrame a PDF con formato profesional y logos"""
    pdf = PDFWithLogo()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Configurar márgenes
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)

    # Información del reporte
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 8, f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
    pdf.cell(0, 8, f"Total de registros: {len(df):,}", 0, 1)
    pdf.ln(5)

    # Logo central más grande (logo.png)
    try:
        logo_path = r"D:\codigos\contador_cerdos\imagenes\logo.png"
        if os.path.exists(logo_path):
            # Centrar el logo
            pdf.image(logo_path, x=(210 - 60) / 2, y=50, w=60, h=30)
            pdf.ln(35)  # Espacio después del logo
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
        if i == 2:  # Espacio después de 3 estadísticas
            pdf.ln(2)

    pdf.ln(8)

    # Tabla de datos
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Datos de Embarques (primeros 30 registros):", 0, 1)

    columnas_mostrar = ['fecha', 'lote_cerdos', 'placa_vehiculo', 'sitio_origen',
                        'sitio_destino', 'total_neto_cerdos']
    columnas_mostrar = [col for col in columnas_mostrar if col in df.columns]

    if columnas_mostrar and len(df) > 0:
        df_muestra = df[columnas_mostrar].head(30)

        # Anchos de columna proporcionales
        anchos = [18, 20, 25, 40, 40, 35]

        # Encabezados
        pdf.set_font("Arial", 'B', 9)
        for i, columna in enumerate(columnas_mostrar):
            pdf.cell(anchos[i], 8, str(columna).replace('_', ' ').title(), 1, 0, 'C')
        pdf.ln()

        # Datos
        pdf.set_font("Arial", '', 8)
        for _, row in df_muestra.iterrows():
            for i, columna in enumerate(columnas_mostrar):
                valor = str(row[columna])
                if columna == 'fecha' and hasattr(row[columna], 'strftime'):
                    valor = row[columna].strftime('%d/%m/%Y')
                # Truncar si es muy largo
                if len(valor) > 50:
                    valor = valor[:12] + '...'
                pdf.cell(anchos[i], 6, valor, 1, 0, 'C')
            pdf.ln()

    return pdf


def exportar_a_excel(df):
    """Exportar DataFrame a Excel """
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Hoja principal
        df.to_excel(writer, sheet_name='Datos Completos', index=False)

        # Hoja con resumen
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

        # Logo en Excel
        try:
            logo1_path = r"/frontend/image\logo1sinfondo.png"
            if os.path.exists(logo1_path):
                worksheet = writer.sheets['Resumen']
                # Insertar logo en la parte superior
                worksheet.insert_image('A1', logo1_path, {'x_scale': 0.4, 'y_scale': 0.4})
        except:
            pass

        # Formato de encabezado
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#1E3A8A',
            'font_color': 'white',
            'border': 1,
            'font_size': 10
        })

        # Aplicar formato
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


# ==================== INTERFAZ PRINCIPAL ====================
def main():
    # Header principal optimizado
    col_header1, col_header2, col_header3 = st.columns([3, 4, 2])

    with col_header1:
        st.empty()  # Espacio para balance

    with col_header2:
        st.markdown('<h1 class="main-header">📊 Dashboard Analítico</h1>',
                    unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; color: #64748B; margin-top: -10px;">Sistema de Conteo de Cerdos</div>',
                    unsafe_allow_html=True)

    with col_header3:
        # Logo en la parte superior derecha
        try:
            logo1_path = r"/frontend/image\logo1sinfondo.png"
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

    # Sidebar optimizado
    with st.sidebar:
        mostrar_logo_sidebar()

        st.markdown('<div class="filter-card">', unsafe_allow_html=True)
        st.markdown("### 🔍 Filtros")
        st.markdown("---")

        # Filtros simplificados
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

    # ==================== SECCIÓN 1: KPIs MEJORADOS ====================
    st.markdown('<h2 class="sub-header">📈 KPIs Principales</h2>', unsafe_allow_html=True)

    # Usar métricas nativas de Streamlit para mejor control
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta_embarques = metricas.get('embarques_hoy', 0) - metricas.get('embarques_ayer', 0)
        st.metric(
            label="Total Embarques",
            value=f"{metricas.get('total_embarques', 0):,}",
            delta=f"{metricas.get('embarques_hoy', 0)} hoy"
        )

    with col2:
        delta_cerdos = metricas.get('cerdos_hoy', 0) - metricas.get('cerdos_ayer', 0)
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
        tendencia = metricas.get('tendencia_7dias', 0)
        st.metric(
            label="Tendencia 7 días",
            value=f"{tendencia:+.0f}",
            delta="cerdos/día"
        )

    # ==================== SECCIÓN 2: PESTAÑAS ====================
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

    # ==================== PIE DE PÁGINA ====================
    st.markdown("---")

    col_footer1, col_footer2 = st.columns([3, 1])

    with col_footer1:
        st.markdown("**Dashboard Analítico v3.0** • Sistema de Conteo Inteligente")
        st.markdown(f"*Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}*")

    with col_footer2:
        st.markdown(
            f"**{len(df_filtrado):,} registros** • **{df_filtrado['lote_cerdos'].nunique() if 'lote_cerdos' in df_filtrado.columns else 0} lotes**")


if __name__ == "__main__":
    main()