import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(
    page_title="EULER RISK 360",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PREMIUM ---
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
    
    /* HERO SECTION */
    .hero-box {
        text-align: center; padding: 40px; 
        background: radial-gradient(circle at center, rgba(59, 130, 246, 0.1) 0%, rgba(255,255,255,0) 70%); 
        border-radius: 20px; margin-bottom: 30px; border: 1px dashed #E2E8F0;
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
# 2. CARGA DE DATOS ROBUSTA
# ==========================================
@st.cache_data
def load_data():
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()
    
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    # Lectura Inteligente
    def smart_read(path):
        for sep in [';', ',', '\t']:
            try:
                df = pd.read_csv(path, sep=sep, compression='gzip', encoding='utf-8')
                if len(df.columns) > 1: return df
            except: continue
        return pd.DataFrame()

    if os.path.exists(file_ent): df_ent = smart_read(file_ent)
    if os.path.exists(file_con): df_con = smart_read(file_con)

    # --- NORMALIZACIÓN ENTIDADES ---
    if not df_ent.empty:
        if 'nombre_entidad' in df_ent.columns and 'nombre_entidad_normalizado' not in df_ent.columns:
            df_ent.rename(columns={'nombre_entidad': 'nombre_entidad_normalizado'}, inplace=True)
        
        # Municipio
        col_muni = next((c for c in ['municipio_limpio', 'municipio_base', 'ciudad'] if c in df_ent.columns), None)
        df_ent['municipio_grafica'] = df_ent[col_muni].fillna("No Definido") if col_muni else "Indeterminado"

    # --- NORMALIZACIÓN CONTRATISTAS ---
    if not df_con.empty:
        # Nombre Proveedor
        col_prov = next((c for c in ['nom_proveedor', 'nom_contratista', 'nombre_contratista', 'razon_social'] if c in df_con.columns), None)
        df_con['nom_proveedor_final'] = df_con[col_prov].fillna("Desconocido") if col_prov else "Sin Nombre"

        # Riesgo
        col_risk = next((c for c in ['Riesgo', 'alerta_legal_ss', 'alerta_riesgo_legal'] if c in df_con.columns), None)
        if col_risk:
            df_con['Riesgo'] = df_con[col_risk].fillna('OK').astype(str).str.upper()
            df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'] else 'OK')
        else:
            df_con['Riesgo'] = 'OK'
            
        # Afiliación y Fechas
        if 'estado_afiliacion' not in df_con.columns: df_con['estado_afiliacion'] = 'Sin Dato'
        if 'regimen' not in df_con.columns: df_con['regimen'] = 'Sin Dato'
        
        # Intentar obtener año temporal
        if 'anio_ultimo_contrato' not in df_con.columns: 
            # Si no hay año explícito, intentar sacarlo de una fecha
            col_date = next((c for c in ['fecha_firma', 'fecha_inicio', 'fecha_contrato'] if c in df_con.columns), None)
            if col_date:
                try: df_con['anio_ultimo_contrato'] = pd.to_datetime(df_con[col_date], errors='coerce').dt.year
                except: df_con['anio_ultimo_contrato'] = 2024
            else:
                df_con['anio_ultimo_contrato'] = 2024

        df_con['anio_ultimo_contrato'] = df_con['anio_ultimo_contrato'].fillna(2024).astype(int)

    return df_ent, df_con

df_ent, df_con = load_data()

# ==========================================
# 3. SIDEBAR Y NAVEGACIÓN
# ==========================================
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    if os.path.exists("LogoEuler.png"): st.image("LogoEuler.png", use_container_width=True)
    else: st.markdown("## 🛡️ EULER")
    
    st.markdown("---")
    menu = st.radio("MENÚ PRINCIPAL", ["Home", "Contratos Secop", "Entidades", "Afiliaciones"])
    st.markdown("---")
    st.caption(f"Registros:\n🏛️ {len(df_ent)}\n👷 {len(df_con)}")

# ================= SECCIÓN: HOME =================
if menu == "Home":
    st.markdown("""
    <div class="hero-box">
        <h1 style="font-size: 3rem; background: linear-gradient(90deg, #2563EB, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">EULER RISK 360™</h1>
        <p style="color:#64748B; font-size: 1.2rem; margin-top:10px;">Plataforma de Inteligencia Artificial para Auditoría Pública</p>
    </div>
    """, unsafe_allow_html=True)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Entidades Vigiladas", f"{len(df_ent):,}")
    k2.metric("Base Contratistas", f"{len(df_con):,}")
    crit = len(df_con[df_con['Riesgo']=='CRÍTICA']) if 'Riesgo' in df_con.columns else 0
    k3.metric("Alertas Críticas", f"{crit:,}", delta_color="inverse")

# ================= SECCIÓN: CONTRATOS SECOP (REDISEÑADO) =================
elif menu == "Contratos Secop":
    st.title("📊 Visión General de Contratos")
    st.markdown("Análisis de tendencias, distribución de riesgos y geografía.")
    
    # --- FILTROS GLOBALES INTERACTIVOS ---
    st.markdown("### 🎛️ Filtros Interactivos")
    f1, f2 = st.columns([1, 2])
    
    with f1:
        sel_riesgo = st.multiselect("Nivel de Riesgo:", ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'], default=['CRÍTICA', 'ALTA', 'MEDIA', 'OK'])
    with f2:
        txt_buscar = st.text_input("Buscar por Entidad o Municipio:", placeholder="Escribe para filtrar todas las gráficas...")

    # APLICAR FILTROS
    # 1. Filtro Riesgo
    df_c_filtered = df_con[df_con['Riesgo'].isin(sel_riesgo)] if 'Riesgo' in df_con.columns else df_con
    
    # 2. Filtro Texto (Entidad o Municipio)
    if txt_buscar:
        # Filtrar contratistas que pertenecen a entidades que coinciden
        col_ent_c = next((c for c in df_c_filtered.columns if 'entidad' in c), None)
        col_mun_c = next((c for c in df_c_filtered.columns if 'municipio' in c or 'ciudad' in c), None)
        
        mask = pd.Series(False, index=df_c_filtered.index)
        if col_ent_c: mask |= df_c_filtered[col_ent_c].astype(str).str.contains(txt_buscar, case=False, na=False)
        if col_mun_c: mask |= df_c_filtered[col_mun_c].astype(str).str.contains(txt_buscar, case=False, na=False)
        
        df_c_filtered = df_c_filtered[mask]
        
        # También filtramos el dataframe de entidades para las tortas
        mask_e = df_ent['nombre_entidad_normalizado'].astype(str).str.contains(txt_buscar, case=False, na=False)
        if 'municipio_grafica' in df_ent.columns:
            mask_e |= df_ent['municipio_grafica'].astype(str).str.contains(txt_buscar, case=False, na=False)
        df_e_filtered = df_ent[mask_e]
    else:
        df_e_filtered = df_ent

    st.markdown("---")

    # --- KPI SUMMARY ---
    c1, c2 = st.columns(2)
    c1.metric("Contratos Filtrados", f"{len(df_c_filtered):,}")
    c2.metric("Entidades Relacionadas", f"{len(df_e_filtered):,}")

    # --- GRÁFICAS DE TENDENCIA (LO QUE PEDISTE) ---
    st.subheader("📈 Tendencias Temporales")
    
    # GRÁFICA 1: VALOR TOTAL ($)
    # Usamos la historia de las entidades filtradas
    if 'json_evolucion_anual' in df_e_filtered.columns:
        timeline = []
        for j in df_e_filtered['json_evolucion_anual']:
            data = parse_json(j)
            for y, v in data.items():
                if str(y) in ['2023', '2024', '2025', '2026']: 
                    timeline.append({'Año': str(y), 'Valor': v})
        
        if timeline:
            df_t = pd.DataFrame(timeline).groupby('Año').sum().reset_index()
            fig_val = px.area(df_t, x='Año', y='Valor', title="Tendencia: Valor Total de Contratos ($)", markers=True)
            st.plotly_chart(fig_val, use_container_width=True)
        else:
            st.info("No hay datos históricos de valor disponibles para la selección.")

    # GRÁFICA 2: CANTIDAD DE CONTRATOS POR RIESGO (#)
    if 'anio_ultimo_contrato' in df_c_filtered.columns and 'Riesgo' in df_c_filtered.columns:
        # Agrupar por Tiempo y Riesgo
        df_trend = df_c_filtered.groupby(['anio_ultimo_contrato', 'Riesgo']).size().reset_index(name='Cantidad')
        df_trend['Año'] = df_trend['anio_ultimo_contrato'].astype(str) # String para eje X limpio
        
        fig_qty = px.bar(
            df_trend, x='Año', y='Cantidad', color='Riesgo',
            title="Tendencia: Cantidad de Contratos por Nivel de Alerta",
            color_discrete_map={'CRÍTICA':'#EF4444', 'ALTA':'#F97316', 'MEDIA':'#FACC15', 'OK':'#10B981'},
            text_auto=True
        )
        st.plotly_chart(fig_qty, use_container_width=True)
    else:
        st.warning("Faltan columnas de fecha o riesgo para generar la tendencia.")

    # --- TORTAS DE DISTRIBUCIÓN ---
    st.subheader("🗺️ Distribución Geográfica y Entidad")
    g1, g2 = st.columns(2)
    
    with g1:
        st.markdown("**Por Entidad**")
        if not df_e_filtered.empty and 'cantidad_contratos' in df_e_filtered.columns:
            # Top 10 de lo filtrado
            top_ent = df_e_filtered.nlargest(10, 'cantidad_contratos')
            fig_e = px.pie(top_ent, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.4)
            st.plotly_chart(fig_e, use_container_width=True)
        else:
            st.info("Sin datos para mostrar.")
            
    with g2:
        st.markdown("**Por Municipio**")
        if not df_e_filtered.empty and 'municipio_grafica' in df_e_filtered.columns:
            top_mun = df_e_filtered['municipio_grafica'].value_counts().head(10).reset_index()
            top_mun.columns = ['Municipio', 'Cantidad']
            fig_m = px.pie(top_mun, values='Cantidad', names='Municipio', hole=0.4)
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("Sin datos geográficos.")


# ================= SECCIÓN: ENTIDADES (CORREGIDO: LISTADO VUELVE) =================
elif menu == "Entidades":
    st.title("🏢 Auditoría por Entidad")
    
    # 1. GRÁFICAS GENERALES
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**Distribución Geográfica**")
        if 'municipio_grafica' in df_ent.columns:
            df_m = df_ent['municipio_grafica'].value_counts().head(10).reset_index()
            df_m.columns = ['Municipio', 'Cantidad']
            fig_m = px.pie(df_m, values='Cantidad', names='Municipio', hole=0.5)
            st.plotly_chart(fig_m, use_container_width=True)
    with r2:
        st.markdown("**Distribución por Volumen**")
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

        st.subheader("📊 Ejecución Presupuestal")
        if 'json_evolucion_anual' in df_ent.columns:
            hist_data = parse_json(row['json_evolucion_anual'])
            if hist_data:
                df_h = pd.DataFrame(list(hist_data.items()), columns=['Año', 'Monto'])
                df_h['Año'] = df_h['Año'].astype(str).str.replace(',', '').str.replace('.', '')
                df_h = df_h[df_h['Año'].isin(['2023','2024','2025','2026'])].sort_values('Año')
                fig_bar = px.bar(df_h, x='Año', y='Monto', color='Monto')
                st.plotly_chart(fig_bar, use_container_width=True)

        # 4. LISTADO DE CONTRATISTAS (EL PECADO CORREGIDO)
        st.subheader("👷 Listado de Contratistas")
        
        # Filtramos contratistas de esta entidad
        col_rel = next((c for c in df_con.columns if 'entidad' in c), None)
        if col_rel:
            df_sub = df_con[df_con[col_rel].astype(str).str.contains(sel_ent, na=False, case=False)]
            
            if not df_sub.empty:
                # Renombrar columnas para que se vea limpio
                df_view = df_sub.rename(columns={
                    'nom_proveedor_final': 'Nombre Contratista',
                    'doc_proveedor': 'Documento/NIT',
                    'Riesgo': 'Nivel Riesgo',
                    'estado_afiliacion': 'Afiliación Salud'
                })
                # Seleccionar columnas a mostrar
                cols_final = ['Nombre Contratista', 'Documento/NIT', 'Nivel Riesgo', 'Afiliación Salud']
                cols_exist = [c for c in cols_final if c in df_view.columns]
                
                st.dataframe(df_view[cols_exist], use_container_width=True)
            else:
                st.info("No se encontraron contratistas directos para esta entidad en la base actual.")
        else:
            st.warning("No se puede vincular contratistas (falta columna de relación).")

# ================= SECCIÓN: AFILIACIONES (INTACTA) =================
elif menu == "Afiliaciones":
    st.title("🏥 Control de Seguridad Social")
    
    c1, c2 = st.columns(2)
    with c1:
        if 'estado_afiliacion' in df_con.columns:
            st.subheader("Estado Afiliación")
            fig = px.pie(df_con, names='estado_afiliacion', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if 'regimen' in df_con.columns:
            st.subheader("Régimen Salud")
            fig = px.pie(df_con, names='regimen', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🚨 Semáforo de Cumplimiento")

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
