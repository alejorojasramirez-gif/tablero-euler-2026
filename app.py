import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ==========================================
# 1. CONFIGURACIÓN VISUAL (TU DISEÑO EXACTO)
# ==========================================
st.set_page_config(
    page_title="EULER RISK 360",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO (Estilo Premium del archivo original) ---
st.markdown("""
<style>
    /* FUENTE MODERNA */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        color: #1E293B; 
    }
    
    /* FONDO DEGRADADO */
    .stApp { 
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%); 
    }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    /* TARJETAS KPI */
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        border-color: #3B82F6;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        color: #0F172A;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARGA DE DATOS
# ==========================================
@st.cache_data
def load_data():
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()

    # Cargar Entidades
    if os.path.exists(file_ent):
        try:
            df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
        except:
            df_ent = pd.read_csv(file_ent, sep=",", compression="gzip", encoding='utf-8')

    # Cargar Contratistas
    if os.path.exists(file_con):
        try:
            df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
        except:
            df_con = pd.read_csv(file_con, sep=",", compression="gzip", encoding='utf-8')
            
    return df_ent, df_con

df_ent, df_con = load_data()

if df_ent.empty:
    st.error("⚠️ Error: No se pudieron leer los datos.")
    st.stop()

# ==========================================
# 3. SIDEBAR (LOGO Y FILTROS)
# ==========================================
with st.sidebar:
    if os.path.exists("LogoEuler.png"):
        st.image("LogoEuler.png", use_column_width=True)
    else:
        st.markdown("## 🛡️ EULER RISK")
        
    st.markdown("---")
    st.markdown("### 🎛️ Filtros Globales")
    
    # Filtro: Departamento
    if 'departamento_base' in df_ent.columns:
        deptos = sorted(df_ent['departamento_base'].dropna().astype(str).unique())
        sel_depto = st.selectbox("📍 Departamento / Región", ["Todos"] + deptos)
        if sel_depto != "Todos":
            df_ent = df_ent[df_ent['departamento_base'] == sel_depto]

    st.markdown("---")
    st.info(f"🏢 Entidades: {len(df_ent):,}")

# ==========================================
# 4. DASHBOARD (TU ESQUEMA ORIGINAL)
# ==========================================

st.title("EULER RISK 360™")
st.markdown("**Plataforma de Inteligencia Artificial para Auditoría Pública**")
st.markdown("---")

# --- KPIS ---
k1, k2, k3, k4 = st.columns(4)

def kpi(col, label, value, color="#0F172A"):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# Cálculos seguros
total_pres = df_ent['presupuesto_total_historico'].sum() if 'presupuesto_total_historico' in df_ent.columns else 0
riesgo_avg = df_ent['exposicion_riesgo_legal'].mean() if 'exposicion_riesgo_legal' in df_ent.columns else 0

kpi(k1, "Entidades Vigiladas", f"{len(df_ent):,}", "#2563EB")
kpi(k2, "Contratistas", f"{len(df_con):,}", "#475569")
kpi(k3, "Presupuesto Total", f"${total_pres/1e12:,.1f}B", "#16A34A")
kpi(k4, "Riesgo Promedio", f"{riesgo_avg:.1f}%", "#DC2626" if riesgo_avg > 50 else "#F59E0B")

st.markdown("<br>", unsafe_allow_html=True)

# --- PESTAÑAS ---
tabs = st.tabs(["🚨 RADAR DE RIESGOS", "🩻 RAYOS X (DETALLE)", "🗺️ MAPA DE CALOR"])

# === TAB 1: RADAR (Aquí estaba el error) ===
with tabs[0]:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Top 10 Entidades con Mayor Riesgo")
        if 'exposicion_riesgo_legal' in df_ent.columns:
            top_risk = df_ent.nlargest(10, 'exposicion_riesgo_legal').sort_values('exposicion_riesgo_legal', ascending=True)
            fig = px.bar(
                top_risk, x='exposicion_riesgo_legal', y='nombre_entidad_normalizado', orientation='h',
                text='exposicion_riesgo_legal',
                color='exposicion_riesgo_legal',
                color_continuous_scale=['#10B981', '#F59E0B', '#EF4444']
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(xaxis_title="Nivel de Riesgo (0-100)", yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
            
    with c2:
        st.subheader("Alertas del Sistema")
        if 'exposicion_riesgo_legal' in df_ent.columns:
            # Lógica de Semáforo
            crit = len(df_ent[df_ent['exposicion_riesgo_legal'] >= 70])
            med = len(df_ent[(df_ent['exposicion_riesgo_legal'] < 70) & (df_ent['exposicion_riesgo_legal'] >= 30)])
            baj = len(df_ent[df_ent['exposicion_riesgo_legal'] < 30])
            
            # --- CORRECCIÓN AQUÍ: px.pie en lugar de px.donut ---
            fig_pie = px.pie(
                values=[crit, med, baj], 
                names=['🔴 Crítico', '🟡 Medio', '🟢 Bajo'],
                color=['🔴 Crítico', '🟡 Medio', '🟢 Bajo'],
                color_discrete_map={'🔴 Crítico':'#EF4444', '🟡 Medio':'#F59E0B', '🟢 Bajo':'#10B981'},
                hole=0.6 # Esto es lo que lo hace una dona
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# === TAB 2: RAYOS X (TU TABLA SEMÁFORO) ===
with tabs[1]:
    st.subheader("Matriz de Control Detallada")
    
    # Columnas Clave
    cols = ['nombre_entidad_normalizado', 'presupuesto_total_historico', 'cantidad_contratos', 'exposicion_riesgo_legal']
    cols_ok = [c for c in cols if c in df_ent.columns]
    
    df_show = df_ent[cols_ok].copy()
    
    # Configuración de Columnas (Estilo App original)
    cfg = {
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
        df_show.sort_values('exposicion_riesgo_legal', ascending=False),
        column_config=cfg,
        use_container_width=True,
        height=600
    )

# === TAB 3: MAPA ===
with tabs[2]:
    st.subheader("Mapa de Presupuesto por Región")
    if 'departamento_base' in df_ent.columns:
        df_map = df_ent.groupby('departamento_base')[['presupuesto_total_historico']].sum().reset_index()
        fig_tree = px.treemap(
            df_map, path=['departamento_base'], values='presupuesto_total_historico',
            color='presupuesto_total_historico', color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_tree, use_container_width=True)
