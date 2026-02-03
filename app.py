import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import sqlite3
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
        box-shadow: 4px 0 24px rgba(0,0,0,0.02);
    }
    
    /* TARJETAS KPI FLOTANTES (GLASSMORPHISM) */
    div[data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #F1F5F9;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        border-color: #06B6D4;
    }
    
    /* TÍTULOS CON DEGRADADO (TIPO APPLE/STRIPE) */
    h1, h2, h3, .gradient-text {
        background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 50%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    
    /* TABLAS PULIDAS */
    .stDataFrame { 
        border: 1px solid #E2E8F0; 
        border-radius: 12px; 
        overflow: hidden;
    }
    
    /* ESTILOS ESPECÍFICOS DEL HOME HERO */
    .hero-container {
        text-align: center;
        padding: 60px 20px;
        background: radial-gradient(circle at center, rgba(6,182,212,0.05) 0%, rgba(255,255,255,0) 70%);
        border-radius: 20px;
        margin-bottom: 30px;
    }
    .hero-title {
        font-size: 80px;
        font-weight: 900;
        margin: 0;
        line-height: 1.1;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 2px 10px rgba(0,201,255,0.2));
    }
    .hero-subtitle {
        font-size: 24px;
        color: #64748B;
        font-weight: 400;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES ---
def fmt_cop(val):
    if pd.isna(val): return "$0"
    if val >= 1e12: return f"${val/1e12:,.2f}B"
    if val >= 1e9: return f"${val/1e9:,.1f}MM"
    if val >= 1e6: return f"${val/1e6:,.1f}M"
    return f"${val:,.0f}"

def parse_json(val):
    try: return json.loads(str(val).replace("'", '"'))
    except: return {}

# --- 4. CARGA DE DATOS (SQLITE NATIVO) ---
@st.cache_data
def load_data():
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()
    
    try:
        # 1. INTENTAR CARGAR SQLITE (PRIORIDAD)
        db_file = "secop_v2_completa.db"
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            try:
                # Leer tablas completas
                df_ent = pd.read_sql("SELECT * FROM perfil_entidad_analytics", conn)
                df_con = pd.read_sql("SELECT * FROM perfil_contratista_analytics", conn)
            except Exception as e:
                st.warning(f"Error leyendo tablas SQL: {e}. Intentando CSV...")
            finally:
                conn.close()
        
        # 2. SI FALLA SQL, INTENTAR CSV (RESPALDO)
        if df_ent.empty or df_con.empty:
            if os.path.exists("perfil_entidad_analytics.csv"):
                df_ent = pd.read_csv("perfil_entidad_analytics.csv", sep=";", encoding='utf-8')
                if df_ent.shape[1] < 2: df_ent = pd.read_csv("perfil_entidad_analytics.csv", sep=",", encoding='utf-8')
            
            if os.path.exists("perfil_contratista_analytics.csv"):
                df_con = pd.read_csv("perfil_contratista_analytics.csv", sep=";", encoding='utf-8')
                if df_con.shape[1] < 2: df_con = pd.read_csv("perfil_contratista_analytics.csv", sep=",", encoding='utf-8')

        if df_ent.empty or df_con.empty:
            return pd.DataFrame(), pd.DataFrame()

        # --- NORMALIZACIÓN DE COLUMNAS ---
        # Estandarizamos nombres para que el código funcione igual sea CSV o SQL
        col_map = {
            'nom_contratista': 'nom_proveedor', 'nombre_contratista': 'nom_proveedor', 'proveedor': 'nom_proveedor',
            'nombre_entidad': 'nombre_entidad_normalizado', 'entidad': 'nombre_entidad_normalizado',
            'ciudad': 'municipio_base'
        }
        df_con.rename(columns=col_map, inplace=True)
        df_ent.rename(columns=col_map, inplace=True)
        
        # Validar texto contratista
        if 'nom_proveedor' not in df_con.columns:
            text_cols = df_con.select_dtypes(include=['object']).columns
            df_con['nom_proveedor'] = df_con[text_cols[0]] if len(text_cols) > 0 else "Desconocido"

        # --- LÓGICA DE RIESGO ---
        # Detectamos automáticamente qué columna de riesgo trae la base
        if 'alerta_legal_ss' in df_con.columns:
            df_con['Riesgo'] = df_con['alerta_legal_ss'].fillna('OK').str.upper()
        elif 'alerta_riesgo_legal' in df_con.columns:
            df_con['Riesgo'] = df_con['alerta_riesgo_legal'].fillna('OK').str.upper()
        else:
            df_con['Riesgo'] = 'OK'

        valid_risks = ['CRÍTICA', 'ALTA', 'MEDIA', 'BAJA', 'OK']
        df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in valid_risks else 'OK')

        # Numéricos
        for c in ['presupuesto_total_historico', 'cantidad_contratos']:
            if c in df_ent.columns:
                df_ent[c] = pd.to_numeric(df_ent[c], errors='coerce').fillna(0)
        
        # Asegurar año contrato para gráficas
        if 'anio_ultimo_contrato' not in df_con.columns:
            df_con['anio_ultimo_contrato'] = 2025 # Fallback

        return df_ent, df_con

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_ent, df_con = load_data()

# --- 5. INTERFAZ ---

if not df_ent.empty:

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        if os.path.exists("logo.png"): 
            st.image("logo.png", use_container_width=True)
        else: 
            st.markdown("<h1 style='text-align: center;'>EULER</h1>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("NAVEGACIÓN")
        menu = st.radio("", ["Home", "Contratos Secop", "Entidades", "Afiliaciones"], label_visibility="collapsed")
        st.markdown("---")

    # ================= HOME (AHORA SÍ, WOW) =================
    if menu == "Home":
        # HERO SECTION CON HTML/CSS INYECTADO
        st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">EULER 360</h1>
            <p class="hero-subtitle">Plataforma de Inteligencia y Auditoría Gubernamental</p>
        </div>
        """, unsafe_allow_html=True)
        
        # LOGO GRANDE SI EXISTE
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if os.path.exists("logo.png"):
                st.image("logo.png", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # TARJETAS FLOTANTES
        k1, k2, k3 = st.columns(3)
        k1.metric("🏛️ Entidades", f"{len(df_ent):,}", "Auditadas")
        k2.metric("👥 Contratistas", f"{len(df_con):,}", "En Base de Datos")
        criticos = len(df_con[df_con['Riesgo'] == 'CRÍTICA'])
        k3.metric("🚨 Alertas Críticas", f"{criticos:,}", "Requieren Atención", delta_color="inverse")

    # ================= CONTRATOS SECOP =================
    elif menu == "Contratos Secop":
        st.markdown("## 📊 Visión General de Contratos")
        
        # Filtros
        col_f1, col_f2 = st.columns(2)
        sel_riesgo = col_f1.multiselect("Filtrar Riesgo:", ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'], default=['CRÍTICA', 'ALTA', 'MEDIA', 'OK'])
        
        df_filtered = df_con[df_con['Riesgo'].isin(sel_riesgo)]
        
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Presupuesto (Global)", fmt_cop(df_ent['presupuesto_total_historico'].sum()))
        k2.metric("Contratos (Global)", f"{df_ent['cantidad_contratos'].sum():,.0f}")
        k3.metric("Contratistas (Filtrados)", f"{len(df_filtered):,.0f}")
        
        st.markdown("---")
        
        # Fila 1: Tendencia y Barras Apiladas
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("#### Tendencia ($)")
            timeline = []
            for j in df_ent['json_evolucion_anual']:
                data = parse_json(j)
                for y, v in data.items():
                    if str(y) in ['2023', '2024', '2025', '2026']: 
                        timeline.append({'Año': str(y), 'Valor': v})
            
            if timeline:
                df_time = pd.DataFrame(timeline).groupby('Año').sum().reset_index().sort_values('Año')
                fig_line = px.area(df_time, x='Año', y='Valor', title="Evolución Presupuestal")
                fig_line.update_xaxes(type='category')
                fig_line.update_layout(yaxis_tickformat='.2s', height=350)
                st.plotly_chart(fig_line, use_container_width=True)

        with c2:
            st.markdown("#### Totales por Riesgo")
            counts = df_filtered['Riesgo'].value_counts().reset_index()
            counts.columns = ['Riesgo', 'Cantidad']
            fig_stack = px.bar(counts, x=pd.Series(["Total"]*len(counts)), y='Cantidad', color='Riesgo',
                               color_discrete_map={'CRÍTICA': '#EF4444', 'ALTA': '#F97316', 'MEDIA': '#FACC15', 'OK': '#10B981'},
                               labels={'x': ''})
            fig_stack.update_layout(height=350, xaxis_showticklabels=False)
            st.plotly_chart(fig_stack, use_container_width=True)

        # Fila 2: LAS TORTAS (DUALIDAD PRESUPUESTO VS CANTIDAD)
        st.markdown("#### Top Entidades")
        p1, p2 = st.columns(2)
        
        with p1:
            # Top Entidades (Presupuesto)
            st.caption("Por Presupuesto Total ($)")
            top_ent_money = df_ent.nlargest(10, 'presupuesto_total_historico')
            fig_pie_ent = px.pie(top_ent_money, values='presupuesto_total_historico', names='nombre_entidad_normalizado', 
                                 hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig_pie_ent, use_container_width=True)
            
        with p2:
            # Top Entidades (Cantidad Contratos)
            st.caption("Por Cantidad de Contratos (#)")
            top_ent_count = df_ent.nlargest(10, 'cantidad_contratos')
            fig_pie_count = px.pie(top_ent_count, values='cantidad_contratos', names='nombre_entidad_normalizado', 
                                   hole=0.4, color_discrete_sequence=px.colors.sequential.Purples)
            st.plotly_chart(fig_pie_count, use_container_width=True)

    # ================= ENTIDADES =================
    elif menu == "Entidades":
        st.markdown("## 🏢 Auditoría Detallada por Entidad")
        
        # 1. TORTA GLOBAL
        st.markdown("#### Panorama General de Inversión")
        top_global = df_ent.nlargest(10, 'presupuesto_total_historico')
        fig_g = px.pie(top_global, values='presupuesto_total_historico', names='nombre_entidad_normalizado', hole=0.5)
        fig_g.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig_g, use_container_width=True)
        st.divider()

        # 2. FILTRO POR PALABRAS
        col_search, col_select = st.columns([1, 2])
        search_term = col_search.text_input("🔍 Escriba para filtrar entidad:", placeholder="Ej: Instituto...")
        
        all_ents = sorted(df_ent['nombre_entidad_normalizado'].astype(str).unique())
        if search_term:
            filtered_ents = [e for e in all_ents if search_term.upper() in e.upper()]
        else:
            filtered_ents = all_ents
        
        if not filtered_ents:
            st.warning("No se encontraron entidades.")
            sel_ent = None
        else:
            sel_ent = col_select.selectbox("Seleccione la Entidad:", filtered_ents)

        # 3. DASHBOARD ENTIDAD
        if sel_ent:
            row = df_ent[df_ent['nombre_entidad_normalizado'] == sel_ent].iloc[0]
            st.markdown(f"### 📌 {sel_ent}")
            
            col_kpi, col_risk = st.columns(2)
            with col_kpi:
                st.metric("Presupuesto", fmt_cop(row['presupuesto_total_historico']))
                st.metric("Total Contratos", f"{row['cantidad_contratos']:,.0f}")
            with col_risk:
                st.markdown("**Nivel de Riesgo Institucional**")
                r_pct = row.get('exposicion_riesgo_legal', 0)
                st.progress(min(float(r_pct), 1.0))
                st.caption(f"Exposición: {r_pct*100:.1f}%")

            # Gráficas Perfil
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                st.markdown("**Comportamiento Presupuestal**")
                hist = parse_json(row.get('json_evolucion_anual'))
                if hist:
                    df_h = pd.DataFrame(list(hist.items()), columns=['Año', 'Monto']).sort_values('Año')
                    fig_h = px.bar(df_h, x='Año', y='Monto', color_discrete_sequence=['#0EA5E9'])
                    fig_h.update_xaxes(type='category')
                    st.plotly_chart(fig_h, use_container_width=True)

            with g_col2:
                # Contratistas de esta entidad
                df_this_ent = pd.DataFrame()
                if 'ultima_entidad_contratante' in df_con.columns:
                    df_this_ent = df_con[df_con['ultima_entidad_contratante'] == sel_ent].copy()
                if df_this_ent.empty:
                    mun = row.get('municipio_limpio')
                    df_this_ent = df_con[df_con['municipio_base'] == mun].copy()

                st.markdown("**Riesgo de Contratistas (Año)**")
                if not df_this_ent.empty and 'anio_ultimo_contrato' in df_this_ent.columns:
                    risk_trend = df_this_ent.groupby(['anio_ultimo_contrato', 'Riesgo']).size().reset_index(name='Cantidad')
                    risk_trend['Año'] = risk_trend['anio_ultimo_contrato'].astype(int).astype(str)
                    fig_rt = px.bar(risk_trend, x='Año', y='Cantidad', color='Riesgo',
                                    color_discrete_map={'CRÍTICA': '#EF4444', 'ALTA': '#F97316', 'MEDIA': '#FACC15', 'OK': '#10B981'})
                    fig_rt.update_xaxes(type='category')
                    st.plotly_chart(fig_rt, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Listado Detallado de Contratistas")
            
            f_risk = st.multiselect("Filtrar Alerta:", ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'], default=['CRÍTICA', 'ALTA', 'MEDIA'])
            
            if not df_this_ent.empty:
                df_table = df_this_ent[df_this_ent['Riesgo'].isin(f_risk)].copy()
                risk_map = {'CRÍTICA': 0, 'ALTA': 1, 'MEDIA': 2, 'OK': 3}
                df_table['sort'] = df_table['Riesgo'].map(risk_map).fillna(4)
                df_table = df_table.sort_values('sort')
                
                def style_risk_row(v):
                    if v == 'CRÍTICA': return 'background-color: #FECACA; color: #991B1B; font-weight: bold'
                    if v == 'ALTA': return 'background-color: #FFEDD5; color: #9A3412'
                    if v == 'MEDIA': return 'background-color: #FEF9C3; color: #854D0E'
                    return 'color: #065F46'

                st.dataframe(
                    df_table[['nom_proveedor', 'doc_proveedor', 'Riesgo', 'ingreso_disponible_estimado']].style.applymap(style_risk_row, subset=['Riesgo']),
                    use_container_width=True,
                    column_config={
                        "ingreso_disponible_estimado": st.column_config.NumberColumn("Capacidad Est.", format="$%d")
                    },
                    hide_index=True
                )
            else:
                st.warning("No se encontraron contratistas.")

    # ================= AFILIACIONES =================
    elif menu == "Afiliaciones":
        st.markdown("## 🏥 Control de Seguridad Social")
        
        g1, g2 = st.columns(2)
        with g1:
            if 'estado_afiliacion' in df_con.columns:
                f1 = px.pie(df_con, names='estado_afiliacion', hole=0.5, title="Estado Global")
                st.plotly_chart(f1, use_container_width=True)
        with g2:
            if 'regimen' in df_con.columns:
                f2 = px.pie(df_con, names='regimen', hole=0.5, title="Régimen Global", color_discrete_sequence=px.colors.sequential.Magenta)
                st.plotly_chart(f2, use_container_width=True)
                
        st.markdown("---")
        st.markdown("### 🚨 Semáforo de Cumplimiento por Entidad")
        
        if 'ultima_entidad_contratante' in df_con.columns:
            df_con['is_crit'] = (df_con['Riesgo'] == 'CRÍTICA').astype(int)
            df_con['is_high'] = (df_con['Riesgo'] == 'ALTA').astype(int)
            df_con['is_med'] = (df_con['Riesgo'] == 'MEDIA').astype(int)
            df_con['is_ok'] = (df_con['Riesgo'] == 'OK').astype(int)
            
            board = df_con.groupby('ultima_entidad_contratante')[['is_crit', 'is_high', 'is_med', 'is_ok']].sum().reset_index()
            board['Total'] = board['is_crit'] + board['is_high'] + board['is_med'] + board['is_ok']
            board['Total Alertas'] = board['is_crit'] + board['is_high'] + board['is_med']
            board['pct_val'] = (board['is_ok'] / board['Total']) * 100
            
            def get_color_dot(val):
                if val >= 99: return "🟢"
                if val >= 90: return "🟢" 
                if val >= 50: return "🟡"
                return "🔴"
            
            board['Semáforo'] = board['pct_val'].apply(get_color_dot)
            
            txt_f = st.text_input("Filtrar Entidad:", "")
            if txt_f: board = board[board['ultima_entidad_contratante'].str.contains(txt_f.upper(), na=False)]
            
            board = board.sort_values('is_crit', ascending=False)
            
            st.dataframe(
                board[['ultima_entidad_contratante', 'Total', 'is_crit', 'is_high', 'is_med', 'is_ok', 'Total Alertas', 'pct_val', 'Semáforo']],
                column_config={
                    "ultima_entidad_contratante": st.column_config.TextColumn("Entidad", width="large"),
                    "is_crit": "🔴 Críticos",
                    "is_high": "🟠 Altos",
                    "is_med": "🟡 Medios",
                    "is_ok": "🟢 OK",
                    "pct_val": st.column_config.ProgressColumn("% Cumplimiento", min_value=0, max_value=100, format="%.1f%%"),
                    "Semáforo": st.column_config.TextColumn("Estado", width="small")
                },
                use_container_width=True,
                hide_index=True
            )