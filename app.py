import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Tablero EULER 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-left: 5px solid #4F8BF9;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data
def load_data():
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    # 1. Cargar Entidades
    try:
        df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
    except:
        df_ent = pd.DataFrame()

    # 2. Cargar Contratistas
    try:
        df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
    except:
        df_con = pd.DataFrame()

    return df_ent, df_con

# --- EJECUCIÓN DE CARGA ---
df_ent, df_con = load_data()

# Validación Crítica: Si no hay datos, paramos.
if df_ent.empty:
    st.error("⚠️ Los datos no cargaron correctamente. Verifica que 'entidad_final.csv.gz' esté en GitHub y tenga datos.")
    st.stop()

# ==============================================================================
#                             SIDEBAR (FILTROS)
# ==============================================================================

# --- MANEJO SEGURO DEL LOGO ---
# Aquí estaba el error. Ahora lo protegemos con try-except.
try:
    if os.path.exists("LogoEuler.png"):
        st.sidebar.image("LogoEuler.png", use_column_width=True)
    else:
        st.sidebar.markdown("## 📊 EULER")
except Exception as e:
    # Si la imagen falla (está corrupta), mostramos texto y seguimos.
    st.sidebar.warning("⚠️ Error en Logo")
    st.sidebar.markdown("## 📊 EULER")
# ------------------------------

st.sidebar.title("🔍 Panel de Control")

# Filtro: Departamento
if 'departamento_base' in df_ent.columns:
    deptos = sorted(df_ent['departamento_base'].dropna().astype(str).unique())
    selected_depto = st.sidebar.selectbox("📍 Filtrar por Departamento:", ["Todos"] + deptos)
    
    if selected_depto != "Todos":
        df_ent = df_ent[df_ent['departamento_base'] == selected_depto]

# Filtro: Presupuesto
if 'presupuesto_total_historico' in df_ent.columns:
    try:
        min_val = float(df_ent['presupuesto_total_historico'].min())
        max_val = float(df_ent['presupuesto_total_historico'].max())
        
        if max_val > 0:
            val_range = st.sidebar.slider(
                "💰 Rango de Presupuesto (Millones)",
                min_value=0.0,
                max_value=max_val/1_000_000,
                value=(0.0, max_val/1_000_000)
            )
            mask = (df_ent['presupuesto_total_historico'] >= val_range[0]*1_000_000) & \
                   (df_ent['presupuesto_total_historico'] <= val_range[1]*1_000_000)
            df_ent = df_ent[mask]
    except:
        pass

st.sidebar.markdown("---")
st.sidebar.caption(f"Registros: {len(df_ent)}")

# ==============================================================================
#                             DASHBOARD PRINCIPAL
# ==============================================================================

st.markdown('<p class="main-header">Tablero de Control de Riesgo - EULER 2026</p>', unsafe_allow_html=True)

# --- KPI CARDS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏢 Entidades", f"{len(df_ent):,}")
    
with col2:
    val = df_ent['cantidad_contratos'].sum() if 'cantidad_contratos' in df_ent.columns else 0
    st.metric("📄 Contratos Totales", f"{val:,}")

with col3:
    val = df_ent['presupuesto_total_historico'].sum() if 'presupuesto_total_historico' in df_ent.columns else 0
    st.metric("💰 Presupuesto ($COP)", f"${val:,.0f}")

with col4:
    if 'exposicion_riesgo_legal' in df_ent.columns:
        riesgo = df_ent['exposicion_riesgo_legal'].mean()
        st.metric("⚖️ Riesgo Legal Prom.", f"{riesgo:.1f}%")
    else:
        st.metric("⚖️ Riesgo Legal", "N/A")

st.markdown("---")

# --- GRÁFICAS Y PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "🏛️ Detalle Entidades", "🏗️ Detalle Contratistas"])

# === PESTAÑA 1: PANORAMA ===
with tab1:
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Distribución por Departamento")
        if 'departamento_base' in df_ent.columns:
            conteo_depto = df_ent['departamento_base'].value_counts().reset_index()
            conteo_depto.columns = ['Departamento', 'Cantidad']
            fig_map = px.bar(conteo_depto.head(10), x='Cantidad', y='Departamento', orientation='h', color='Cantidad', title="Top 10 Departamentos")
            fig_map.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_map, use_container_width=True)

    with c2:
        st.subheader("Dispersión: Tamaño vs Presupuesto")
        if 'presupuesto_total_historico' in df_ent.columns and 'cantidad_contratos' in df_ent.columns:
            fig_scatter = px.scatter(
                df_ent, 
                x='cantidad_contratos', 
                y='presupuesto_total_historico',
                size='cantidad_contratos',
                color='departamento_base' if 'departamento_base' in df_ent.columns else None,
                hover_name='nombre_entidad_normalizado',
                log_y=True
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# === PESTAÑA 2: ENTIDADES ===
with tab2:
    st.subheader("🔍 Ranking de Entidades")
    cols = ['nombre_entidad_normalizado', 'presupuesto_total_historico', 'cantidad_contratos', 'departamento_base']
    cols = [c for c in cols if c in df_ent.columns]
    
    if 'presupuesto_total_historico' in df_ent.columns:
        st.dataframe(df_ent.sort_values('presupuesto_total_historico', ascending=False)[cols], use_container_width=True)
    else:
        st.dataframe(df_ent)

# === PESTAÑA 3: CONTRATISTAS ===
with tab3:
    st.subheader("🏆 Top Contratistas")
    if not df_con.empty and 'valor_total_historico' in df_con.columns:
        df_con['valor_total_historico'] = pd.to_numeric(df_con['valor_total_historico'], errors='coerce').fillna(0)
        top_con = df_con.nlargest(20, 'valor_total_historico')
        
        fig_con = px.bar(
            top_con,
            x='valor_total_historico',
            y=top_con['doc_proveedor'].astype(str),
            orientation='h',
            title="Top 20 Contratistas",
            color='valor_total_historico',
            color_continuous_scale='Viridis'
        )
        fig_con.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_con, use_container_width=True)
        st.dataframe(df_con.head(100))
    else:
        st.warning("Sin datos de contratistas.")

# Footer
st.markdown("---")
st.caption("EULER © 2026")
