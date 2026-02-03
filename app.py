import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN VISUAL (ESTILO PREMIUM)
# ==========================================
st.set_page_config(
    page_title="EULER RISK 360",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1E293B; }
    .stApp { background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%); }
    section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
    
    /* KPI CARDS */
    div[data-testid="metric-container"] {
        background: #FFFFFF; border: 1px solid #F1F5F9; padding: 15px; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); border-color: #3B82F6; }
    
    /* TITULOS */
    h1, h2, h3 { color: #0F172A; font-weight: 800 !important; }
    
    /* HERO SECTION */
    .hero-box {
        text-align: center; padding: 30px; background: #F8FAFC; border-radius: 20px; margin-bottom: 20px;
        border: 1px dashed #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES AUXILIARES ---
def fmt_cop(val):
    if pd.isna(val): return "$0"
    if val >= 1e12: return f"${val/1e12:,.2f}B"
    if val >= 1e9: return f"${val/1e9:,.1f}MM"
    if val >= 1e6: return f"${val/1e6:,.1f}M"
    return f"${val:,.0f}"

def parse_json(val):
    try: return json.loads(str(val).replace("'", '"'))
    except: return {}

# ==========================================
# 2. CARGA DE DATOS INTELIGENTE
# ==========================================
@st.cache_data
def load_data():
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()
    
    # Intentar leer CSVs (Separador ; o ,)
    files = {
        "ent": "entidad_final.csv.gz",
        "con": "contratista_final.csv.gz"
    }
    
    # ENTIDADES
    if os.path.exists(files["ent"]):
        try: df_ent = pd.read_csv(files["ent"], sep=";", compression="gzip", encoding='utf-8')
        except: df_ent = pd.read_csv(files["ent"], sep=",", compression="gzip", encoding='utf-8')
    
    # CONTRATISTAS
    if os.path.exists(files["con"]):
        try: df_con = pd.read_csv(files["con"], sep=";", compression="gzip", encoding='utf-8')
        except: df_con = pd.read_csv(files["con"], sep=",", compression="gzip", encoding='utf-8')

    # --- NORMALIZACIÓN DE COLUMNAS (Para que las gráficas no fallen) ---
    if not df_ent.empty:
        # Renombrar si es necesario
        if 'nombre_entidad' in df_ent.columns and 'nombre_entidad_normalizado' not in df_ent.columns:
            df_ent.rename(columns={'nombre_entidad': 'nombre_entidad_normalizado'}, inplace=True)
            
    if not df_con.empty:
        # Crear columna Riesgo si no existe
        if 'Riesgo' not in df_con.columns:
            # Buscar columnas candidatas
            candidates = ['alerta_legal_ss', 'alerta_riesgo_legal', 'nivel_riesgo']
            col_found = next((c for c in candidates if c in df_con.columns), None)
            
            if col_found:
                df_con['Riesgo'] = df_con[col_found].fillna('OK').astype(str).str.upper()
                # Limpiar valores
                df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'] else 'OK')
            else:
                df_con['Riesgo'] = 'OK' # Valor por defecto

        # Asegurar columnas de afiliación para gráficas
        if 'estado_afiliacion' not in df_con.columns: df_con['estado_afiliacion'] = 'Desconocido'
        if 'regimen' not in df_con.columns: df_con['regimen'] = 'Desconocido'

    return df_ent, df_con

df_ent, df_con = load_data()

# Si falla la carga
if df_ent.empty:
    st.error("⚠️ Error: No se encontraron datos. Verifica que subiste 'entidad_final.csv.gz' y 'contratista_final.csv.gz'.")
    st.stop()

# ==========================================
# 3. INTERFAZ Y NAVEGACIÓN LATERAL
# ==========================================

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    if os.path.exists("LogoEuler.png"): 
        st.image("LogoEuler.png", use_container_width=True)
    else: 
        st.markdown("## 🛡️ EULER")
    
    st.markdown("---")
    
    # MENU DE NAVEGACIÓN
    menu = st.radio("MENÚ PRINCIPAL", ["Home", "Contratos Secop", "Entidades", "Afiliaciones"])
    
    st.markdown("---")
    st.caption(f"Registros Cargados:\n🏛️ {len(df_ent)} Entidades\n👷 {len(df_con)} Contratistas")

# ==========================================
# SECCIÓN 1: HOME
# ==========================================
if menu == "Home":
    st.markdown("""
    <div class="hero-box">
        <h1 style="margin:0; font-size: 3rem;">EULER RISK 360™</h1>
        <p style="color:#64748B;">Plataforma de Inteligencia Artificial para Auditoría Pública</p>
    </div>
    """, unsafe_allow_html=True)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Entidades Vigiladas", f"{len(df_ent):,}")
    k2.metric("Contratistas", f"{len(df_con):,}")
    criticos = len(df_con[df_con['Riesgo']=='CRÍTICA']) if 'Ries
