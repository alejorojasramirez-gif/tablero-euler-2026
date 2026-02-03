import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN VISUAL (TU DISEÑO EXACTO)
# ==========================================
st.set_page_config(
    page_title="EULER RISK 360",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TU CSS PERSONALIZADO (Estilo Premium) ---
st.markdown("""
<style>
    /* FUENTE MODERNA */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        color: #1E293B; 
    }
    
    /* FONDO DEGRADADO SUTIL */
    .stApp { 
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%); 
    }
    
    /* SIDEBAR */
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARGA DE DATOS (CONECTADO A GITHUB)
# ==========================================
@st.cache_data
def load_data():
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()

    # Cargar Entidades
    try:
        df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
    except:
        # Intento secundario por si el formato cambia
        try:
            df_ent = pd.read_csv(file_ent, sep=",", compression="gzip", encoding='utf-8')
        except:
            pass

    # Cargar Contratistas
    try:
        df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
    except:
        try:
            df_con = pd.read_csv(file_con, sep=",", compression="gzip", encoding='utf-8')
        except:
            pass
            
    return df_ent, df_con

df_ent, df_con = load_data()

# Si no carga nada, aviso de seguridad
if df_ent.empty:
    st.error("⚠️ Los datos no cargaron. Verifica que 'entidad_final.csv.gz' esté en GitHub y tenga datos.")
    st.stop()

# ==========================================
# 3. SIDEBAR (FILTROS Y LOGO)
# ==========================================
with st.sidebar:
    # --- LOGO (Protegido para que no tumbe la app si falla, pero se muestra si funciona) ---
    try:
        if os.path.exists("LogoEuler.png"):
            st.image("LogoEuler.png", use_column_width=True)
        else:
            st.markdown("## 🛡️ EULER RISK")
    except:
        st.markdown("## 🛡️ EULER RISK")
    # -------------------------------------------------------------------------------------
    
    st.markdown("### 🎛️ Centro de Comando")
    
    # Filtro 1: Departamento
    if 'departamento_base' in df_ent.columns:
        deptos = sorted(df_ent['departamento_base'].dropna().astype(str).unique())
        sel_depto = st.selectbox("📍 Región / Departamento", ["Todos"] + deptos)
        if sel_depto != "Todos":
            df_ent = df_ent[df_ent['departamento_base'] == sel_depto]

    # Filtro 2: Riesgo (Si existe)
    if 'exposicion_riesgo_legal' in df_ent.columns:
        st.markdown("---")
        st.markdown("### ⚖️ Nivel de Riesgo")
        r_min, r_max = st.slider("Rango de Riesgo (%)", 0, 100, (0, 100))
        df_ent = df_ent[
            (df_ent['exposicion_riesgo_legal'] >= r_min) & 
            (df_ent['exposicion_riesgo_legal'] <= r_max)
        ]

    st.markdown("---")
    st.info(f"📊 Analizando **{len(df_ent):,}** Entidades")

# ==========================================
# 4. DASHBOARD (DISEÑO ORIGINAL)
# ==========================================

st.title("EULER RISK 360™")
st.markdown("**Plataforma de Inteligencia Artificial para Auditoría Pública**")

# --- KPIS (MÉTRICAS) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

def kpi_card(col, title, value, color="black"):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value" style="color: {color}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# Cálculos
total_ent = len(df_ent)
total_con = len(df_con)
presupuesto = df_ent['presupuesto_total_historico'].sum() if 'presupuesto_total_historico' in df_ent.columns else 0
riesgo_prom = df_ent['exposicion_riesgo_legal'].mean() if 'exposicion_riesgo_legal' in df_ent.columns else 0

kpi_card(kpi1, "Entidades", f"{total_ent:,}", "#2563EB")
kpi_card(kpi2, "Contratistas", f"{total_con:,}", "#475569")
kpi_card(kpi3, "Presupuesto", f"${presupuesto/1e12:,.1f} B", "#16A34A")
kpi_card(kpi4, "Riesgo Promedio", f"{riesgo_prom:.1f}%", "#DC2626" if riesgo_prom > 50 else "#F59E0B")

st.markdown("<br>", unsafe_allow_html=True)

# --- PESTAÑAS (TABS) ---
tab1, tab2, tab3 = st.tabs(["🚨 Radar de Riesgos", "🩻 Rayos X (Detalle)", "🗺️ Mapa de Calor"])

# === TAB 1: RADAR ===
with tab1:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Top Entidades con Mayor Riesgo")
        if 'exposicion_riesgo_legal' in df_ent.columns:
            top_risk = df_ent.nlargest(10, 'exposicion_riesgo_legal').sort_values('exposicion_riesgo_legal', ascending=True)
            fig = px.bar(
                top_risk,
                x='exposicion_riesgo_legal',
                y='nombre_entidad_normalizado',
                orientation='h',
                text='exposicion_riesgo_legal',
                color='exposicion_riesgo_legal',
                color_continuous_scale=['#10B981', '#F59E0B', '#EF4444'], # Escala semáforo
                title=""
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos de riesgo calculados.")

    with c2:
        st.subheader("Semáforo de Alertas")
        if 'exposicion_riesgo_legal' in df_ent.columns:
            altos = len(df_ent[df_ent['exposicion_riesgo_legal'] >= 70])
            medios = len(df_ent[(df_ent['exposicion_riesgo_legal'] < 70) & (df_ent['exposicion_riesgo_legal'] >= 30)])
            bajos = len(df_ent[df_ent['exposicion_riesgo_legal'] < 30])
            
            fig_pie = px.donut(
                names=['🔴 Crítico', '🟡 Medio', '🟢 Bajo'],
                values=[altos, medios, bajos],
                color=['🔴 Crítico', '🟡 Medio', '🟢 Bajo'],
                color_discrete_map={'🔴 Crítico':'#EF4444', '🟡 Medio':'#F59E0B', '🟢 Bajo':'#10B981'},
                hole=0.6
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# === TAB 2: RAYOS X (TABLA) ===
with tab2:
    st.subheader("Matriz de Control")
    
    cols = ['nombre_entidad_normalizado', 'presupuesto_total_historico', 'cantidad_contratos', 'exposicion_riesgo_legal']
    cols_existentes = [c for c in cols if c in df_ent.columns]
    
    df_view = df_ent[cols_existentes].copy()
    
    # Configuración bonita
    column_config = {
        "nombre_entidad_normalizado": st.column_config.TextColumn("Entidad", width="large"),
        "presupuesto_total_historico": st.column_config.NumberColumn("Presupuesto", format="$%d"),
        "cantidad_contratos": st.column_config.NumberColumn("Contratos"),
        "exposicion_riesgo_legal": st.column_config.ProgressColumn(
            "Nivel de Riesgo", 
            format="%.1f%%", 
            min_value=0, 
            max_value=100
        )
    }
    
    st.dataframe(
        df_view.sort_values('exposicion_riesgo_legal', ascending=False),
        column_config=column_config,
        use_container_width=True,
        height=600
    )

# === TAB 3: MAPA ===
with tab3:
    st.subheader("Mapa de Calor Presupuestal")
    if 'departamento_base' in df_ent.columns and 'presupuesto_total_historico' in df_ent.columns:
        df_map = df_ent.groupby('departamento_base')[['presupuesto_total_historico']].sum().reset_index()
        fig_tree = px.treemap(
            df_map,
            path=['departamento_base'],
            values='presupuesto_total_historico',
            color='presupuesto_total_historico',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("Datos insuficientes para el mapa.")
