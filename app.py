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
    
    /* KPI CARDS */
    div[data-testid="metric-container"] {
        background: #FFFFFF; 
        border: 1px solid #F1F5F9; 
        padding: 15px; 
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        transition: all 0.2s;
    }
    div[data-testid="metric-container"]:hover { 
        transform: translateY(-3px); 
        border-color: #3B82F6; 
    }
    
    /* HERO SECTION */
    .hero-box {
        text-align: center; 
        padding: 30px; 
        background: #F8FAFC; 
        border-radius: 20px; 
        margin-bottom: 20px; 
        border: 1px dashed #CBD5E1;
    }
    
    h1, h2, h3 { font-weight: 800 !important; color: #0F172A; }
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
# 2. CARGA DE DATOS ROBUSTA (QA CHECKED)
# ==========================================
@st.cache_data
def load_data():
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()
    
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    # 1. Cargar Entidades
    if os.path.exists(file_ent):
        try: df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
        except: df_ent = pd.read_csv(file_ent, sep=",", compression="gzip", encoding='utf-8')
    
    # 2. Cargar Contratistas
    if os.path.exists(file_con):
        try: df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
        except: df_con = pd.read_csv(file_con, sep=",", compression="gzip", encoding='utf-8')

    # --- NORMALIZACIÓN DE COLUMNAS (FIX: KEYERROR PREVENTIVO) ---
    if not df_ent.empty:
        # Renombrar para estandarizar
        if 'nombre_entidad' in df_ent.columns and 'nombre_entidad_normalizado' not in df_ent.columns:
            df_ent.rename(columns={'nombre_entidad': 'nombre_entidad_normalizado'}, inplace=True)
            
    if not df_con.empty:
        # Asegurar columna Proveedor
        if 'nom_proveedor' not in df_con.columns:
            candidates = ['nom_contratista', 'nombre_contratista', 'proveedor', 'razon_social']
            for c in candidates:
                if c in df_con.columns:
                    df_con['nom_proveedor'] = df_con[c]
                    break
            if 'nom_proveedor' not in df_con.columns: 
                df_con['nom_proveedor'] = "Desconocido"

        # Asegurar columna Riesgo
        if 'Riesgo' not in df_con.columns:
            # Buscar columnas posibles
            col_found = None
            for c in ['alerta_legal_ss', 'alerta_riesgo_legal', 'nivel_riesgo']:
                if c in df_con.columns:
                    col_found = c
                    break
            
            if col_found:
                df_con['Riesgo'] = df_con[col_found].fillna('OK').astype(str).str.upper()
                validos = ['CRÍTICA', 'ALTA', 'MEDIA', 'BAJA', 'OK']
                df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in validos else 'OK')
            else:
                df_con['Riesgo'] = 'OK'
        
        # Asegurar año para gráficas
        if 'anio_ultimo_contrato' not in df_con.columns:
            df_con['anio_ultimo_contrato'] = 2024 # Valor por defecto si falta
            
        # Asegurar columnas de Afiliación
        if 'estado_afiliacion' not in df_con.columns: df_con['estado_afiliacion'] = 'Sin Dato'
        if 'regimen' not in df_con.columns: df_con['regimen'] = 'Sin Dato'

    return df_ent, df_con

df_ent, df_con = load_data()

# Validación de seguridad
if df_ent.empty:
    st.error("⚠️ Error Crítico: No se encontraron datos. Verifica que los archivos .csv.gz estén en GitHub.")
    st.stop()

# ==========================================
# 3. INTERFAZ Y NAVEGACIÓN (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Logo seguro
    if os.path.exists("LogoEuler.png"): 
        st.image("LogoEuler.png", use_container_width=True)
    else: 
        st.markdown("## 🛡️ EULER")
    
    st.markdown("---")
    
    # MENÚ DE NAVEGACIÓN
    menu = st.radio("MENÚ PRINCIPAL", ["Home", "Contratos Secop", "Entidades", "Afiliaciones"])
    
    st.markdown("---")
    st.caption(f"Base de Datos:\n🏛️ {len(df_ent)} Entidades\n👷 {len(df_con)} Contratistas")

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
    k2.metric("Base Contratistas", f"{len(df_con):,}")
    
    # FIX: Syntax error corregido aquí
    criticos = len(df_con[df_con['Riesgo']=='CRÍTICA']) if 'Riesgo' in df_con.columns else 0
    k3.metric("Alertas Críticas", f"{criticos:,}", delta_color="inverse")
    
    st.info("👈 Utiliza el menú lateral izquierdo para navegar por los módulos.")

# ==========================================
# SECCIÓN 2: CONTRATOS SECOP
# ==========================================
elif menu == "Contratos Secop":
    st.title("📊 Visión General de Contratos")
    
    # Filtros
    sel_riesgo = st.multiselect("Filtrar por Riesgo:", ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'], default=['CRÍTICA', 'ALTA', 'MEDIA', 'OK'])
    
    if 'Riesgo' in df_con.columns:
        df_f = df_con[df_con['Riesgo'].isin(sel_riesgo)]
    else:
        df_f = df_con

    # KPIs Superiores
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Contratos Filtrados", f"{len(df_f):,}")
    with c2:
        val_tot = df_ent['presupuesto_total_historico'].sum() if 'presupuesto_total_historico' in df_ent.columns else 0
        st.metric("Presupuesto Global", fmt_cop(val_tot))
    
    st.markdown("---")

    # 1. GRÁFICA DE BARRAS APILADAS (FIX: AHORA SÍ MUESTRA EVOLUCIÓN)
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("📆 Evolución de Riesgo (Histórico)")
        if 'anio_ultimo_contrato' in df_f.columns and 'Riesgo' in df_f.columns:
            # Agrupar y convertir año a String para evitar "2,025.5"
            df_evol = df_f.groupby(['anio_ultimo_contrato', 'Riesgo']).size().reset_index(name='Cantidad')
            df_evol['Año'] = df_evol['anio_ultimo_contrato'].astype(int).astype(str)
            
            fig_stack = px.bar(
                df_evol, x='Año', y='Cantidad', color='Riesgo',
                title="Distribución por Año",
                color_discrete_map={'CRÍTICA':'#EF4444', 'ALTA':'#F97316', 'MEDIA':'#FACC15', 'OK':'#10B981'}
            )
            st.plotly_chart(fig_stack, use_container_width=True)
        else:
            st.warning("No hay datos de año disponibles.")

    # 2. TOP ENTIDADES (FIX: AGREGADA LA GRÁFICA DE CANTIDAD)
    with g2:
        st.subheader("🏆 Top Entidades")
        tab_money, tab_qty = st.tabs(["💰 Por Presupuesto", "#️⃣ Por Cantidad"])
        
        with tab_money:
            if 'presupuesto_total_historico' in df_ent.columns:
                top_p = df_ent.nlargest(10, 'presupuesto_total_historico')
                fig_p = px.pie(top_p, values='presupuesto_total_historico', names='nombre_entidad_normalizado', hole=0.4, color_discrete_sequence=px.colors.sequential.Blues)
                st.plotly_chart(fig_p, use_container_width=True)
        
        with tab_qty:
            if 'cantidad_contratos' in df_ent.columns:
                top_c = df_ent.nlargest(10, 'cantidad_contratos')
                fig_c = px.pie(top_c, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.4, color_discrete_sequence=px.colors.sequential.Oranges)
                st.plotly_chart(fig_c, use_container_width=True)

    # 3. EVOLUCIÓN TEMPORAL
    st.subheader("📈 Evolución Presupuestal Global")
    if 'json_evolucion_anual' in df_ent.columns:
        timeline = []
        for j in df_ent['json_evolucion_anual']:
            data = parse_json(j)
            for y, v in data.items():
                if str(y) in ['2023', '2024', '2025', '2026']: 
                    timeline.append({'Año': str(y), 'Valor': v})
        
        if timeline:
            df_t = pd.DataFrame(timeline).groupby('Año').sum().reset_index()
            fig_line = px.area(df_t, x='Año', y='Valor', title="Histórico Agregado ($COP)")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No se encontraron datos históricos.")
    else:
        st.info("Columna de evolución no disponible.")

# ==========================================
# SECCIÓN 3: ENTIDADES
# ==========================================
elif menu == "Entidades":
    st.title("🏢 Auditoría por Entidad")
    
    # 1. GRÁFICAS DE DISTRIBUCIÓN (FIX: AGREGADAS)
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**Distribución por Municipio**")
        if 'municipio_base' in df_ent.columns:
            # Top 10 municipios
            df_muni = df_ent['municipio_base'].value_counts().head(10).reset_index()
            df_muni.columns = ['Municipio', 'Cantidad']
            fig_m = px.pie(df_muni, values='Cantidad', names='Municipio', hole=0.5)
            st.plotly_chart(fig_m, use_container_width=True)
        elif 'departamento_base' in df_ent.columns:
            df_dep = df_ent['departamento_base'].value_counts().reset_index()
            df_dep.columns = ['Departamento', 'Cantidad']
            fig_d = px.pie(df_dep, values='Cantidad', names='Departamento', hole=0.5)
            st.plotly_chart(fig_d, use_container_width=True)

    with r2:
        st.markdown("**Distribución por Volumen de Contratación**")
        if 'cantidad_contratos' in df_ent.columns:
            top_vol = df_ent.nlargest(10, 'cantidad_contratos')
            fig_v = px.pie(top_vol, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.5)
            st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")

    # 2. BUSCADOR INTELIGENTE
    st.subheader("🔍 Detalle Individual")
    
    col_search, col_sel = st.columns([1, 2])
    with col_search:
        text_filter = st.text_input("Filtrar nombre:", placeholder="Ej: Hospital, Alcaldía...")
    
    all_ents = sorted(df_ent['nombre_entidad_normalizado'].astype(str).unique()) if 'nombre_entidad_normalizado' in df_ent.columns else []
    
    if text_filter:
        filtered_list = [e for e in all_ents if text_filter.upper() in e.upper()]
    else:
        filtered_list = all_ents

    with col_sel:
        if filtered_list:
            sel_ent = st.selectbox("Seleccione Entidad:", filtered_list)
        else:
            st.warning("No se encontraron coincidencias.")
            sel_ent = None

    # 3. DASHBOARD ENTIDAD
    if sel_ent:
        row = df_ent[df_ent['nombre_entidad_normalizado'] == sel_ent].iloc[0]
        
        # KPIs
        k1, k2, k3 = st.columns(3)
        pres = row.get('presupuesto_total_historico', 0)
        cnt = row.get('cantidad_contratos', 0)
        risk = row.get('exposicion_riesgo_legal', 0)
        
        k1.metric("Presupuesto Total", fmt_cop(pres))
        k2.metric("Contratos Totales", f"{cnt:,.0f}")
        k3.metric("Riesgo Legal", f"{risk:.1f}%")
        
        st.write("Nivel de Exposición al Riesgo:")
        st.progress(min(float(risk)/100, 1.0))

        # GRÁFICA EVOLUCIÓN (FIX: AÑOS LIMPIOS)
        st.subheader(f"📊 Comportamiento Anual: {sel_ent}")
        if 'json_evolucion_anual' in df_ent.columns:
            hist_data = parse_json(row['json_evolucion_anual'])
            if hist_data:
                df_h = pd.DataFrame(list(hist_data.items()), columns=['Año', 'Monto'])
                # Limpieza de año: Convertir a string puro
                df_h['Año'] = df_h['Año'].astype(str).str.replace(',', '').str.replace('.', '')
                df_h = df_h[df_h['Año'].isin(['2023','2024','2025','2026'])].sort_values('Año')
                
                fig_bar = px.bar(df_h, x='Año', y='Monto', color='Monto', title="Ejecución Presupuestal")
                fig_bar.update_xaxes(type='category') # Forzar que el eje X sea texto
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sin histórico anual disponible.")

        # LISTA CONTRATISTAS (FIX: BLINDAJE CONTRA KEYERROR)
        st.subheader("👷 Contratistas Vinculados")
        if 'ultima_entidad_contratante' in df_con.columns:
            # Filtro flexible
            df_sub = df_con[df_con['ultima_entidad_contratante'].astype(str).str.contains(sel_ent, na=False, case=False)]
            
            if not df_sub.empty:
                # Seleccionar solo las columnas que SI existen
                cols_wanted = ['nom_proveedor', 'doc_proveedor', 'Riesgo', 'estado_afiliacion']
                cols_present = [c for c in cols_wanted if c in df_sub.columns]
                
                st.dataframe(df_sub[cols_present], use_container_width=True)
            else:
                st.info("No se encontraron contratistas directos en la base.")
    else:
        st.info("Seleccione una entidad para ver detalles.")

# ==========================================
# SECCIÓN 4: AFILIACIONES (INTACTO)
# ==========================================
elif menu == "Afiliaciones":
    st.title("🏥 Control de Seguridad Social")
    
    # 1. GRÁFICAS DE TORTA
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Estado de Afiliación")
        if 'estado_afiliacion' in df_con.columns:
            fig_a = px.pie(df_con, names='estado_afiliacion', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_a, use_container_width=True)
            
    with c2:
        st.subheader("Régimen de Salud")
        if 'regimen' in df_con.columns:
            fig_r = px.pie(df_con, names='regimen', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("---")

    # 2. SEMÁFORO DE CUMPLIMIENTO
    st.subheader("🚨 Semáforo de Cumplimiento por Entidad")
    
    if 'ultima_entidad_contratante' in df_con.columns and 'Riesgo' in df_con.columns:
        # Preparación de datos
        df_con['crit'] = (df_con['Riesgo']=='CRÍTICA').astype(int)
        df_con['ok'] = (df_con['Riesgo']=='OK').astype(int)
        
        board = df_con.groupby('ultima_entidad_contratante')[['crit', 'ok']].sum().reset_index()
        board['Total'] = df_con.groupby('ultima_entidad_contratante')['Riesgo'].count().values
        board['Cumplimiento'] = (board['ok'] / board['Total']) * 100
        board['Cumplimiento'] = board['Cumplimiento'].fillna(0)
        
        # Filtro tabla
        filtro_tabla = st.text_input("Filtrar Entidad en la tabla:", placeholder="Escribe para buscar...")
        if filtro_tabla:
            board = board[board['ultima_entidad_contratante'].str.contains(filtro_tabla, case=False, na=False)]
            
        # Iconos
        def get_icon(val):
            return "🟢" if val >= 90 else "🟡" if val >= 50 else "🔴"
        
        board['Estado'] = board['Cumplimiento'].apply(get_icon)
        board = board.sort_values('Cumplimiento', ascending=True)
        
        st.dataframe(
            board[['ultima_entidad_contratante', 'Total', 'crit', 'Cumplimiento', 'Estado']],
            column_config={
                "ultima_entidad_contratante": st.column_config.TextColumn("Entidad", width="large"),
                "crit": st.column_config.NumberColumn("Alertas Críticas"),
                "Cumplimiento": st.column_config.ProgressColumn("% Cumplimiento", format="%.1f%%", min_value=0, max_value=100),
                "Estado": st.column_config.TextColumn("Semáforo", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
