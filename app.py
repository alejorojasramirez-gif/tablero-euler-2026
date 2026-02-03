import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN VISUAL (MODO PREMIUM)
# ==========================================
st.set_page_config(
    page_title="EULER RISK 360",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INYECCIÓN DE CSS "WOW" ---
st.markdown("""
<style>
    /* FUENTE MODERNA */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        color: #1E293B; 
    }
    
    /* FONDO DEGRADADO SUTIL (EFECTO CLEAN) */
    .stApp { 
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%); 
    }
    
    /* SIDEBAR ELEGANTE */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    /* TARJETAS DE MÉTRICAS (KPIs) */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
    }
    .metric-label {
        font-size: 14px;
        font-weight: 500;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    
    /* TÍTULOS */
    h1, h2, h3 {
        color: #0F172A; 
        font-weight: 800;
    }
    
    /* PESTAÑAS (TABS) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #FFFFFF;
        border-radius: 8px;
        color: #64748B;
        font-weight: 600;
        border: 1px solid #E2E8F0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB;
        color: white;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARGA DE DATOS (ADAPTADO A CSV.GZ)
# ==========================================
@st.cache_data
def load_data_from_csv():
    # Nombres de archivos que ya confirmamos en GitHub
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()

    # 1. Cargar Entidades
    if os.path.exists(file_ent):
        try:
            df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
        except:
            # Intento secundario
            try:
                df_ent = pd.read_csv(file_ent, sep=",", compression="gzip", encoding='utf-8')
            except:
                pass

    # 2. Cargar Contratistas
    if os.path.exists(file_con):
        try:
            df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
        except:
            try:
                df_con = pd.read_csv(file_con, sep=",", compression="gzip", encoding='utf-8')
            except:
                pass
                
    return df_ent, df_con

# Cargar los datos
df_ent, df_con = load_data_from_csv()

# Si falla la carga, mostramos aviso pero no rompemos
if df_ent.empty:
    st.error("⚠️ No se pudieron cargar los datos de Entidades. Verifica los archivos en GitHub.")
    st.stop()

# ==========================================
# 3. SIDEBAR (FILTROS INTELIGENTES)
# ==========================================
with st.sidebar:
    # Logo Seguro
    if os.path.exists("LogoEuler.png"):
        st.image("LogoEuler.png", use_column_width=True)
    else:
        st.markdown("## 🛡️ EULER RISK")
    
    st.markdown("### 🎛️ Centro de Comando")
    
    # Filtro 1: Departamento
    if 'departamento_base' in df_ent.columns:
        deptos = sorted(df_ent['departamento_base'].dropna().astype(str).unique())
        sel_depto = st.selectbox("📍 Región / Departamento", ["Todos"] + deptos)
        if sel_depto != "Todos":
            df_ent = df_ent[df_ent['departamento_base'] == sel_depto]

    # Filtro 2: Nivel de Riesgo (Si existe la columna calculada)
    if 'exposicion_riesgo_legal' in df_ent.columns:
        st.markdown("---")
        st.markdown("### ⚖️ Nivel de Riesgo Legal")
        riesgo_min, riesgo_max = st.slider(
            "Filtrar por % de Riesgo:",
            min_value=0, max_value=100, value=(0, 100)
        )
        df_ent = df_ent[
            (df_ent['exposicion_riesgo_legal'] >= riesgo_min) & 
            (df_ent['exposicion_riesgo_legal'] <= riesgo_max)
        ]

    st.markdown("---")
    st.info(f"📊 Analizando **{len(df_ent):,}** Entidades")
    st.caption("v2026.1.0 | Powered by EULER")

# ==========================================
# 4. DASHBOARD PRINCIPAL
# ==========================================

# Encabezado
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("EULER RISK 360™")
    st.markdown("**Plataforma de Inteligencia Artificial para Auditoría Pública**")
with col_h2:
    if 'fecha_corte' in df_ent.columns:
        st.caption(f"📅 Actualizado: {df_ent['fecha_corte'].max()}")

# --- KPIS SUPERIORES (ESTILO TARJETAS) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

def kpi_card(col, title, value, color="black"):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value" style="color: {color}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# Cálculos seguros
total_ent = len(df_ent)
total_con = len(df_con)
total_dinero = df_ent['presupuesto_total_historico'].sum() if 'presupuesto_total_historico' in df_ent.columns else 0
riesgo_prom = df_ent['exposicion_riesgo_legal'].mean() if 'exposicion_riesgo_legal' in df_ent.columns else 0

kpi_card(kpi1, "Entidades Vigiladas", f"{total_ent:,}", "#2563EB")
kpi_card(kpi2, "Contratistas", f"{total_con:,}", "#475569")
kpi_card(kpi3, "Presupuesto ($COP)", f"${total_dinero/1e12:,.1f} B", "#16A34A") # Billones
kpi_card(kpi4, "Riesgo Legal Promedio", f"{riesgo_prom:.1f}%", "#DC2626" if riesgo_prom > 50 else "#F59E0B")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. PESTAÑAS DE ANÁLISIS AVANZADO
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🚨 Radar de Riesgos", 
    "🩻 Rayos X (Entidades)", 
    "🗺️ Mapa de Calor", 
    "🔎 Buscador Inteligente"
])

# --- TAB 1: RADAR DE RIESGOS ---
with tab1:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Top 10 Entidades con Mayor Riesgo Legal")
        if 'exposicion_riesgo_legal' in df_ent.columns:
            top_risk = df_ent.nlargest(10, 'exposicion_riesgo_legal').sort_values('exposicion_riesgo_legal', ascending=True)
            
            fig = px.bar(
                top_risk,
                x='exposicion_riesgo_legal',
                y='nombre_entidad_normalizado',
                orientation='h',
                text='exposicion_riesgo_legal',
                color='exposicion_riesgo_legal',
                color_continuous_scale=['#10B981', '#F59E0B', '#EF4444', '#7F1D1D'],
                title=""
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(xaxis_title="% Riesgo Calculado", yaxis_title=None, height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Datos de riesgo no disponibles.")

    with c2:
        st.subheader("Distribución de Alertas")
        # Simulación de semáforo si no tenemos datos de alertas específicas
        if 'exposicion_riesgo_legal' in df_ent.columns:
            alt
