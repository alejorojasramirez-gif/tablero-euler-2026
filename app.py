import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN VISUAL (ESTILO PREMIUM RESTAURADO)
# ==========================================
st.set_page_config(
    page_title="EULER RISK 360",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS "WOW" ORIGINAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif; 
        color: #1E293B; 
    }
    .stApp { 
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%); 
    }
    section[data-testid="stSidebar"] { 
        background-color: #FFFFFF; 
        border-right: 1px solid #E2E8F0; 
    }
    
    /* KPI CARDS (ESTILO ORIGINAL) */
    div[data-testid="metric-container"] {
        background: #FFFFFF; 
        border: 1px solid #F1F5F9; 
        padding: 20px; 
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
        transition: all 0.2s;
    }
    div[data-testid="metric-container"]:hover { 
        transform: translateY(-5px); 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #3B82F6; 
    }
    
    /* HERO SECTION (HOME) */
    .hero-box {
        text-align: center; 
        padding: 40px; 
        background: radial-gradient(circle at center, rgba(59, 130, 246, 0.1) 0%, rgba(255,255,255,0) 70%); 
        border-radius: 20px; 
        margin-bottom: 30px; 
        border: 1px dashed #E2E8F0;
    }
    
    h1, h2, h3 { font-weight: 800 !important; color: #0F172A; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES ---
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
# 2. CARGA DE DATOS (CEREBRO V110 + VISUAL V80)
# ==========================================
@st.cache_data
def load_data():
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()
    
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    # LECTURA INTELIGENTE (Detecta separador ; o ,)
    def smart_read(path):
        for sep in [';', ',', '\t']:
            try:
                df = pd.read_csv(path, sep=sep, compression='gzip', encoding='utf-8')
                if len(df.columns) > 1: return df
            except: continue
        return pd.DataFrame()

    if os.path.exists(file_ent): df_ent = smart_read(file_ent)
    if os.path.exists(file_con): df_con = smart_read(file_con)

    # --- LIMPIEZA Y NORMALIZACIÓN ---
    if not df_ent.empty:
        # Nombre Entidad
        if 'nombre_entidad_normalizado' not in df_ent.columns:
            if 'nombre_entidad' in df_ent.columns: df_ent.rename(columns={'nombre_entidad': 'nombre_entidad_normalizado'}, inplace=True)
        
        # Municipio (Buscamos 'municipio_limpio' o 'ciudad')
        col_muni = next((c for c in ['municipio_limpio', 'municipio_base', 'ciudad'] if c in df_ent.columns), None)
        if col_muni:
            df_ent['municipio_grafica'] = df_ent[col_muni].fillna("No Definido")
        else:
            df_ent['municipio_grafica'] = df_ent.get('departamento_base', 'Indeterminado')

    if not df_con.empty:
        # Nombre Proveedor (Búsqueda agresiva)
        col_prov = next((c for c in ['nom_proveedor', 'nom_contratista', 'nombre_contratista', 'razon_social'] if c in df_con.columns), None)
        if col_prov:
            df_con['nom_proveedor_final'] = df_con[col_prov].fillna("Desconocido")
        else:
            df_con['nom_proveedor_final'] = "Sin Nombre"

        # Riesgo
        col_risk = next((c for c in ['Riesgo', 'alerta_legal_ss', 'alerta_riesgo_legal'] if c in df_con.columns), None)
        if col_risk:
            df_con['Riesgo'] = df_con[col_risk].fillna('OK').astype(str).str.upper()
            df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'] else 'OK')
        else:
            df_con['Riesgo'] = 'OK'
            
        # Afiliación
        if 'estado_afiliacion' not in df_con.columns: df_con['estado_afiliacion'] = 'Sin Dato'
        if 'regimen' not in df_con.columns: df_con['regimen'] = 'Sin Dato'
        if 'anio_ultimo_contrato' not in df_con.columns: df_con['anio_ultimo_contrato'] = 2024

    return df_ent, df_con

df_ent, df_con = load_data()

# ==========================================
# 3. INTERFAZ Y NAVEGACIÓN
# ==========================================
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    if os.path.exists("LogoEuler.png"): 
        st.image("LogoEuler.png", use_container_width=True)
    else: 
        st.markdown("## 🛡️ EULER")
    
    st.markdown("---")
    menu = st.radio("MENÚ PRINCIPAL", ["Home", "Contratos Secop", "Entidades", "Afiliaciones"])
    st.markdown("---")
    st.caption(f"Registros:\n🏛️ {len(df_ent)}\n👷 {len(df_con)}")

# ================= SECCIÓN: HOME (DISEÑO V60) =================
if menu == "Home":
    st.markdown("""
    <div class="hero-box">
        <h1 style="margin:0; font-size: 3.5rem; background: linear-gradient(90deg, #2563EB, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">EULER RISK 360™</h1>
        <p style="color:#64748B; font-size: 1.2rem; margin-top:10px;">Plataforma de Inteligencia Artificial para Auditoría Pública</p>
    </div>
    """, unsafe_allow_html=True)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Entidades Vigiladas", f"{len(df_ent):,}")
    k2.metric("Base Contratistas", f"{len(df_con):,}")
    crit = len(df_con[df_con['Riesgo']=='CRÍTICA']) if 'Riesgo' in df_con.columns else 0
    k3.metric("Alertas Críticas", f"{crit:,}", delta_color="inverse")

# ================= SECCIÓN: CONTRATOS (DISEÑO V80) =================
elif menu == "Contratos Secop":
    st.title("📊 Visión General de Contratos")
    
    sel_riesgo = st.multiselect("Filtrar por Riesgo:", ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'], default=['CRÍTICA', 'ALTA', 'MEDIA', 'OK'])
    df_f = df_con[df_con['Riesgo'].isin(sel_riesgo)] if 'Riesgo' in df_con.columns else df_con

    c1, c2 = st.columns(2)
    with c1: st.metric("Contratos Filtrados", f"{len(df_f):,}")
    with c2: 
        v = df_ent['presupuesto_total_historico'].sum() if 'presupuesto_total_historico' in df_ent.columns else 0
        st.metric("Presupuesto Global", fmt_cop(v))
    
    st.markdown("---")

    # Gráficas
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("📆 Evolución de Riesgo")
        if 'anio_ultimo_contrato' in df_f.columns:
            df_evol = df_f.groupby(['anio_ultimo_contrato', 'Riesgo']).size().reset_index(name='Cantidad')
            df_evol['Año'] = df_evol['anio_ultimo_contrato'].astype(int).astype(str)
            fig = px.bar(df_evol, x='Año', y='Cantidad', color='Riesgo', 
                         color_discrete_map={'CRÍTICA':'#EF4444', 'ALTA':'#F97316', 'MEDIA':'#FACC15', 'OK':'#10B981'})
            st.plotly_chart(fig, use_container_width=True)
    
    with g2:
        st.subheader("🏆 Top Entidades")
        t1, t2 = st.tabs(["💰 Presupuesto", "#️⃣ Cantidad"])
        with t1:
            if 'presupuesto_total_historico' in df_ent.columns:
                top_p = df_ent.nlargest(10, 'presupuesto_total_historico')
                fig_p = px.pie(top_p, values='presupuesto_total_historico', names='nombre_entidad_normalizado', hole=0.4, color_discrete_sequence=px.colors.sequential.Blues)
                st.plotly_chart(fig_p, use_container_width=True)
        with t2:
            if 'cantidad_contratos' in df_ent.columns:
                top_c = df_ent.nlargest(10, 'cantidad_contratos')
                fig_c = px.pie(top_c, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.4, color_discrete_sequence=px.colors.sequential.Oranges)
                st.plotly_chart(fig_c, use_container_width=True)

# ================= SECCIÓN: ENTIDADES (REPARADO) =================
elif menu == "Entidades":
    st.title("🏢 Auditoría por Entidad")
    
    # 1. GRÁFICAS (MUNICIPIO Y VOLUMEN)
    r1, r2 = st.columns(2)
    with r1:
        st.subheader("🗺️ Distribución Geográfica")
        if 'municipio_grafica' in df_ent.columns:
            df_muni = df_ent['municipio_grafica'].value_counts().head(10).reset_index()
            df_muni.columns = ['Municipio', 'Cantidad']
            fig_m = px.pie(df_muni, values='Cantidad', names='Municipio', hole=0.5)
            st.plotly_chart(fig_m, use_container_width=True)
            
    with r2:
        st.subheader("📦 Distribución por Volumen")
        if 'cantidad_contratos' in df_ent.columns:
            top_v = df_ent.nlargest(10, 'cantidad_contratos')
            fig_v = px.pie(top_v, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.5)
            st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")

    # 2. BUSCADOR
    st.subheader("🔍 Detalle Individual")
    col_s, col_l = st.columns([1, 2])
    with col_s: text_f = st.text_input("Filtrar nombre:", placeholder="Ej: Hospital...")
    
    all_ents = sorted(df_ent['nombre_entidad_normalizado'].astype(str).unique()) if 'nombre_entidad_normalizado' in df_ent.columns else []
    list_f = [e for e in all_ents if text_f.upper() in e.upper()] if text_f else all_ents
    with col_l: sel_ent = st.selectbox("Seleccione Entidad:", list_f) if list_f else None

    # 3. DASHBOARD ENTIDAD
    if sel_ent:
        row = df_ent[df_ent['nombre_entidad_normalizado'] == sel_ent].iloc[0]
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Presupuesto", fmt_cop(row.get('presupuesto_total_historico', 0)))
        k2.metric("Contratos", f"{row.get('cantidad_contratos', 0):,.0f}")
        k3.metric("Riesgo", f"{row.get('exposicion_riesgo_legal', 0):.1f}%")
        st.progress(min(float(row.get('exposicion_riesgo_legal', 0))/100, 1.0))

        # Evolución
        st.subheader("📊 Ejecución Presupuestal")
        if 'json_evolucion_anual' in df_ent.columns:
            hist_data = parse_json(row['json_evolucion_anual'])
            if hist_data:
                df_h = pd.DataFrame(list(hist_data.items()), columns=['Año', 'Monto'])
                df_h['Año'] = df_h['Año'].astype(str).str.replace(',', '').str.replace('.', '')
                df_h = df_h[df_h['Año'].isin(['2023','2024','2025','2026'])].sort_values('Año')
                fig_bar = px.bar(df_h, x='Año', y='Monto', color='Monto')
                fig_bar.update_xaxes(type='category')
                st.plotly_chart(fig_bar, use_container_width=True)

        # TABLA CONTRATISTAS (REPARADA: NOMBRE PROVEEDOR)
        st.subheader("👷 Contratistas Vinculados")
        # Filtro de relación entidad-contratista
        col_rel = next((c for c in df_con.columns if 'entidad_contratante' in c or 'entidad' in c), None)
        
        if col_rel:
            df_sub = df_con[df_con[col_rel].astype(str).str.contains(sel_ent, na=False, case=False)]
            
            if not df_sub.empty:
                # Renombrar para visualización limpia
                df_view = df_sub.copy()
                df_view = df_view.rename(columns={
                    'nom_proveedor_final': 'Contratista',
                    'doc_proveedor': 'NIT/Doc',
                    'Riesgo': 'Nivel Riesgo',
                    'estado_afiliacion': 'Afiliación Salud'
                })
                # Mostrar solo columnas útiles
                cols_view = ['Contratista', 'NIT/Doc', 'Nivel Riesgo', 'Afiliación Salud']
                cols_final = [c for c in cols_view if c in df_view.columns]
                st.dataframe(df_view[cols_final], use_container_width=True)
            else:
                st.info("No se encontraron contratistas directos.")

# ================= SECCIÓN: AFILIACIONES (PERFECTA - NO TOCAR) =================
elif menu == "Afiliaciones":
    st.title("🏥 Control de Seguridad Social")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Estado Afiliación")
        if 'estado_afiliacion' in df_con.columns:
            fig_a = px.pie(df_con, names='estado_afiliacion', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_a, use_container_width=True)
    with c2:
        st.subheader("Régimen Salud")
        if 'regimen' in df_con.columns:
            fig_r = px.pie(df_con, names='regimen', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("---")
    st.subheader("🚨 Semáforo de Cumplimiento por Entidad")

    # Lógica exacta solicitada
    col_rel = next((c for c in df_con.columns if 'entidad_contratante' in c or 'entidad' in c), None)
    
    if col_rel and 'Riesgo' in df_con.columns:
        df_con['crit'] = (df_con['Riesgo']=='CRÍTICA').astype(int)
        df_con['alto'] = (df_con['Riesgo']=='ALTA').astype(int)
        df_con['medio'] = (df_con['Riesgo']=='MEDIA').astype(int)
        df_con['ok'] = (df_con['Riesgo']=='OK').astype(int)
        
        board = df_con.groupby(col_rel)[['crit', 'alto', 'medio', 'ok']].sum().reset_index()
        board['Total Contratos'] = board['crit'] + board['alto'] + board['medio'] + board['ok']
        board['Total Alertas'] = board['crit'] + board['alto'] + board['medio']
        board['% Cumplimiento'] = (board['ok'] / board['Total Contratos']) * 100
        board['% Cumplimiento'] = board['% Cumplimiento'].fillna(0)
        
        def get_light(val): return "🟢" if val >= 90 else "🟡" if val >= 50 else "🔴"
        board['Semáforo'] = board['% Cumplimiento'].apply(get_light)
        
        txt_f = st.text_input("Filtrar Entidad:", "")
        if txt_f: board = board[board[col_rel].str.contains(txt_f, case=False, na=False)]
        
        board = board.sort_values('% Cumplimiento', ascending=True)
        
        st.dataframe(
            board,
            column_order=[col_rel, 'Total Contratos', 'crit', 'alto', 'medio', 'ok', 'Total Alertas', '% Cumplimiento', 'Semáforo'],
            column_config={
                col_rel: st.column_config.TextColumn("Entidad", width="large"),
                "crit": "🔴 Críticos", "alto": "🟠 Altos", "medio": "🟡 Medios", "ok": "🟢 OK",
                "Total Alertas": "⚠️ Alertas",
                "% Cumplimiento": st.column_config.ProgressColumn("Cumplimiento", format="%.1f%%", min_value=0, max_value=100),
                "Semáforo": st.column_config.TextColumn("Estado", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
