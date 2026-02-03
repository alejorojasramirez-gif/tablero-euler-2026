import streamlit as st
import pandas as pd
import plotly.express as px
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
    
    /* FONDO DEGRADADO SUTIL */
    .stApp { 
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%); 
    }
    
    /* SIDEBAR ELEGANTE */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
        box-shadow: 4px 0 24px rgba(0,0,0,0.02);
    }
    
    /* TARJETAS KPI FLOTANTES */
    div[data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #F1F5F9;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        border-color: #06B6D4;
    }
    
    /* TITULOS CON DEGRADADO */
    h1, h2, h3 {
        background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 50%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    
    /* HERO SECTION DEL HOME */
    .hero-container {
        text-align: center;
        padding: 40px 20px;
        background: radial-gradient(circle at center, rgba(6,182,212,0.05) 0%, rgba(255,255,255,0) 70%);
        border-radius: 20px;
        margin-bottom: 20px;
    }
    .hero-title {
        font-size: 60px;
        font-weight: 900;
        margin: 0;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 20px;
        color: #64748B;
        margin-top: 10px;
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
# 2. CARGA DE DATOS (LA PARTE CLAVE)
# ==========================================
@st.cache_data
def load_data():
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()

    # 1. Cargar Entidades
    if os.path.exists(file_ent):
        try:
            df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
        except:
            df_ent = pd.read_csv(file_ent, sep=",", compression="gzip", encoding='utf-8')

    # 2. Cargar Contratistas
    if os.path.exists(file_con):
        try:
            df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
        except:
            df_con = pd.read_csv(file_con, sep=",", compression="gzip", encoding='utf-8')
            
    # VALIDACIÓN DE COLUMNAS (NORMALIZACIÓN)
    # Esto asegura que el código funcione aunque los nombres cambien un poco
    if not df_ent.empty:
        # Si no existe 'nombre_entidad_normalizado', buscamos alternativas
        if 'nombre_entidad_normalizado' not in df_ent.columns and 'nombre_entidad' in df_ent.columns:
            df_ent.rename(columns={'nombre_entidad': 'nombre_entidad_normalizado'}, inplace=True)
            
    if not df_con.empty:
        # Normalizar proveedor
        if 'nom_proveedor' not in df_con.columns:
            for c in ['nom_contratista', 'nombre_contratista', 'proveedor', 'razon_social']:
                if c in df_con.columns:
                    df_con.rename(columns={c: 'nom_proveedor'}, inplace=True)
                    break
            if 'nom_proveedor' not in df_con.columns:
                 df_con['nom_proveedor'] = "Desconocido"
        
        # Calcular Riesgo si no existe
        if 'Riesgo' not in df_con.columns:
            # Buscar columnas de alerta
            col_riesgo = None
            for c in ['alerta_legal_ss', 'alerta_riesgo_legal', 'nivel_riesgo']:
                if c in df_con.columns:
                    col_riesgo = c
                    break
            
            if col_riesgo:
                df_con['Riesgo'] = df_con[col_riesgo].fillna('OK').astype(str).str.upper()
                # Limpiar valores extraños
                validos = ['CRÍTICA', 'ALTA', 'MEDIA', 'BAJA', 'OK']
                df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in validos else 'OK')
            else:
                df_con['Riesgo'] = 'OK' # Valor por defecto si no hay datos de riesgo

    return df_ent, df_con

df_ent, df_con = load_data()

# Si falla la carga, mostramos error elegante
if df_ent.empty:
    st.error("⚠️ No se encontraron datos. Verifica que los archivos .csv.gz estén en GitHub.")
    st.stop()

# ==========================================
# 3. INTERFAZ Y NAVEGACIÓN
# ==========================================

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # LOGO SEGURO
    if os.path.exists("LogoEuler.png"): 
        st.image("LogoEuler.png", use_container_width=True)
    else: 
        st.markdown("<h2 style='text-align: center;'>🛡️ EULER</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("MENÚ PRINCIPAL")
    
    # NAVEGACIÓN LATERAL (ESTILO PREMIUM)
    menu = st.radio(
        "Ir a:", 
        ["Home", "Contratos Secop", "Entidades", "Afiliaciones"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.info(f"📊 Datos cargados:\n- {len(df_ent)} Entidades\n- {len(df_con)} Contratistas")

# ================= SECCIÓN: HOME =================
if menu == "Home":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">EULER 360</h1>
        <p class="hero-subtitle">Plataforma de Inteligencia Artificial para Auditoría Pública</p>
    </div>
    """, unsafe_allow_html=True)
    
    # KPI CARDS
    k1, k2, k3 = st.columns(3)
    k1.metric("🏛️ Entidades Vigiladas", f"{len(df_ent):,}")
    k2.metric("👥 Base Contratistas", f"{len(df_con):,}")
    
    criticos = len(df_con[df_con['Riesgo'] == 'CRÍTICA']) if 'Riesgo' in df_con.columns else 0
    k3.metric("🚨 Alertas Críticas", f"{criticos:,}", delta_color="inverse")

    st.markdown("---")
    st.subheader("📌 Resumen Ejecutivo")
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("Bienvenido al panel de control. Utilice el menú lateral para navegar entre los módulos de análisis.")
    with c2:
        if 'departamento_base' in df_ent.columns:
            top_dep = df_ent['departamento_base'].mode()[0]
            st.success(f"📍 Región con mayor actividad: **{top_dep}**")

# ================= SECCIÓN: CONTRATOS SECOP =================
elif menu == "Contratos Secop":
    st.markdown("## 📊 Visión General de Contratación")
    
    # Filtro Rápido
    riesgos_posibles = ['CRÍTICA', 'ALTA', 'MEDIA', 'OK']
    sel_riesgo = st.multiselect("Filtrar por Nivel de Riesgo:", riesgos_posibles, default=riesgos_posibles)
    
    if 'Riesgo' in df_con.columns:
        df_filtered = df_con[df_con['Riesgo'].isin(sel_riesgo)]
    else:
        df_filtered = df_con
    
    # Gráficas
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("💰 Evolución Presupuestal")
        # Intentar graficar evolución si existe el JSON
        if 'json_evolucion_anual' in df_ent.columns:
            timeline = []
            for j in df_ent['json_evolucion_anual']:
                data = parse_json(j)
                for y, v in data.items():
                    if str(y) in ['2023', '2024', '2025', '2026']: 
                        timeline.append({'Año': str(y), 'Valor': v})
            
            if timeline:
                df_time = pd.DataFrame(timeline).groupby('Año').sum().reset_index().sort_values('Año')
                fig_line = px.area(df_time, x='Año', y='Valor', title="Presupuesto Histórico Agregado")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No hay datos históricos temporales disponibles.")
        else:
            st.info("Columna de evolución anual no encontrada.")

    with c2:
        st.subheader("⚠️ Distribución de Riesgos")
        if 'Riesgo' in df_filtered.columns:
            counts = df_filtered['Riesgo'].value_counts().reset_index()
            counts.columns = ['Riesgo', 'Cantidad']
            fig_pie = px.pie(
                counts, values='Cantidad', names='Riesgo', 
                color='Riesgo',
                color_discrete_map={'CRÍTICA': '#EF4444', 'ALTA': '#F97316', 'MEDIA': '#FACC15', 'OK': '#10B981'},
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# ================= SECCIÓN: ENTIDADES =================
elif menu == "Entidades":
    st.markdown("## 🏢 Auditoría por Entidad")
    
    # Buscador
    all_ents = sorted(df_ent['nombre_entidad_normalizado'].astype(str).unique()) if 'nombre_entidad_normalizado' in df_ent.columns else []
    sel_ent = st.selectbox("🔍 Seleccione una Entidad:", all_ents)
    
    if sel_ent:
        # Datos de la entidad seleccionada
        row = df_ent[df_ent['nombre_entidad_normalizado'] == sel_ent].iloc[0]
        
        col_kpi, col_risk = st.columns(2)
        with col_kpi:
            pres = row.get('presupuesto_total_historico', 0)
            st.metric("Presupuesto Total", fmt_cop(pres))
            st.metric("Contratos", f"{row.get('cantidad_contratos', 0):,.0f}")
        
        with col_risk:
            st.markdown("### Nivel de Riesgo Legal")
            risk_val = row.get('exposicion_riesgo_legal', 0)
            st.progress(min(float(risk_val)/100, 1.0))
            st.caption(f"Exposición calculada: {risk_val:.1f}%")

# ================= SECCIÓN: AFILIACIONES (TABLA SEMÁFORO) =================
elif menu == "Afiliaciones":
    st.markdown("## 🏥 Control de Afiliaciones y Alertas")
    
    st.markdown("### 🚨 Semáforo de Cumplimiento por Entidad")
    
    if 'ultima_entidad_contratante' in df_con.columns and 'Riesgo' in df_con.columns:
        # Preparamos los datos para el tablero
        df_con['is_crit'] = (df_con['Riesgo'] == 'CRÍTICA').astype(int)
        df_con['is_high'] = (df_con['Riesgo'] == 'ALTA').astype(int)
        df_con['is_med'] = (df_con['Riesgo'] == 'MEDIA').astype(int)
        df_con['is_ok'] = (df_con['Riesgo'] == 'OK').astype(int)
        
        board = df_con.groupby('ultima_entidad_contratante')[['is_crit', 'is_high', 'is_med', 'is_ok']].sum().reset_index()
        board['Total'] = board['is_crit'] + board['is_high'] + board['is_med'] + board['is_ok']
        
        # Calcular porcentaje de cumplimiento (OK / Total)
        board['pct_val'] = (board['is_ok'] / board['Total']) * 100
        
        # Lógica del Semáforo (Puntito de color)
        def get_color_dot(val):
            if val >= 99: return "🟢" # Excelente
            if val >= 90: return "🟢" # Bueno
            if val >= 50: return "🟡" # Regular
            return "🔴" # Crítico
        
        board['Semáforo'] = board['pct_val'].apply(get_color_dot)
        
        # Filtro de texto
        txt_f = st.text_input("Filtrar Entidad en la tabla:", "")
        if txt_f: 
            board = board[board['ultima_entidad_contratante'].str.contains(txt_f.upper(), na=False)]
        
        # Ordenar por críticos (para ver lo malo primero)
        board = board.sort_values('is_crit', ascending=False)
        
        # MOSTRAR TABLA
        st.dataframe(
            board[['ultima_entidad_contratante', 'Total', 'is_crit', 'is_high', 'is_med', 'is_ok', 'pct_val', 'Semáforo']],
            column_config={
                "ultima_entidad_contratante
