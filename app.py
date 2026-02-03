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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1E293B; }
    .stApp { background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%); }
    section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
    div[data-testid="metric-container"] {
        background: #FFFFFF; border: 1px solid #F1F5F9; padding: 15px; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); border-color: #3B82F6; }
    h1, h2, h3 { font-weight: 800 !important; color: #0F172A; }
    .hero-box {
        text-align: center; padding: 30px; background: #F8FAFC; border-radius: 20px; 
        margin-bottom: 20px; border: 1px dashed #CBD5E1;
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
# 2. CARGA DE DATOS (SUPER ROBUSTA)
# ==========================================
@st.cache_data
def load_data():
    df_ent = pd.DataFrame()
    df_con = pd.DataFrame()
    
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    # Función interna para probar lecturas
    def smart_read(file_path):
        separators = [';', ',', '\t', '|']
        encodings = ['utf-8', 'latin-1', 'ISO-8859-1']
        
        for enc in encodings:
            for sep in separators:
                try:
                    # Leemos solo 2 líneas para ver si tiene sentido
                    preview = pd.read_csv(file_path, sep=sep, compression='gzip', encoding=enc, nrows=2)
                    if len(preview.columns) > 1: # Si detectó más de 1 columna, es probable que sea el separador correcto
                        return pd.read_csv(file_path, sep=sep, compression='gzip', encoding=enc)
                except:
                    continue
        return pd.DataFrame()

    # 1. Cargar Entidades
    if os.path.exists(file_ent):
        df_ent = smart_read(file_ent)
    
    # 2. Cargar Contratistas
    if os.path.exists(file_con):
        df_con = smart_read(file_con)

    # --- NORMALIZACIÓN DE COLUMNAS ---
    # Convertimos todo a minúsculas para buscar mejor
    if not df_ent.empty:
        df_ent.columns = [c.strip() for c in df_ent.columns] # Quitar espacios
        
        # Buscar Nombre Entidad
        if 'nombre_entidad_normalizado' not in df_ent.columns:
            # Buscar alternativas
            cols_ent = [c for c in df_ent.columns if 'nombre' in c.lower() and 'entidad' in c.lower()]
            if cols_ent: df_ent.rename(columns={cols_ent[0]: 'nombre_entidad_normalizado'}, inplace=True)
            else: df_ent['nombre_entidad_normalizado'] = "Entidad Desconocida"

        # Buscar Municipio (Prioridad: Limpio -> Base -> Ciudad)
        col_muni_found = None
        for cand in ['municipio_limpio', 'municipio_base', 'ciudad', 'municipio', 'ubicacion']:
            if cand in df_ent.columns:
                col_muni_found = cand
                break
        
        if col_muni_found:
            df_ent['municipio_grafica'] = df_ent[col_muni_found].fillna("No Definido")
        else:
            # Si no encuentra, usa Departamento
            if 'departamento_base' in df_ent.columns:
                df_ent['municipio_grafica'] = df_ent['departamento_base'] + " (Depto)"
            else:
                df_ent['municipio_grafica'] = "Indeterminado"

    if not df_con.empty:
        df_con.columns = [c.strip() for c in df_con.columns]
        
        # 1. Buscar PROVEEDOR (Búsqueda amplia)
        col_prov = None
        candidates_prov = ['nom_proveedor', 'nom_contratista', 'nombre_contratista', 'razon_social', 'proveedor', 'nombre', 'contratista']
        for c in candidates_prov:
            if c in df_con.columns:
                col_prov = c
                break
        
        if col_prov:
            df_con['nom_proveedor_final'] = df_con[col_prov].fillna("Sin Nombre")
        else:
            # Si no encuentra columna de nombre, coge la segunda columna del archivo (heurística)
            if len(df_con.columns) > 1:
                 df_con['nom_proveedor_final'] = df_con.iloc[:, 1].fillna("Desconocido")
            else:
                 df_con['nom_proveedor_final'] = "Error Lectura"

        # 2. Buscar RIESGO
        col_risk = None
        candidates_risk = ['riesgo', 'alerta_legal_ss', 'alerta_riesgo_legal', 'nivel_riesgo', 'alerta']
        for c in candidates_risk:
            matches = [col for col in df_con.columns if c in col.lower()]
            if matches:
                col_risk = matches[0]
                break
        
        if col_risk:
            df_con['Riesgo'] = df_con[col_risk].fillna('OK').astype(str).str.upper()
            # Normalizar
            df_con['Riesgo'] = df_con['Riesgo'].apply(lambda x: x if x in ['CRÍTICA', 'ALTA', 'MEDIA', 'BAJA', 'OK'] else 'OK')
        else:
            df_con['Riesgo'] = 'OK'

        # 3. Buscar AFILIACION
        col_afil = next((c for c in df_con.columns if 'afilia' in c.lower()), None)
        if col_afil: df_con['estado_afiliacion'] = df_con[col_afil].fillna('Sin Dato')
        else: df_con['estado_afiliacion'] = 'Sin Dato'

        col_reg = next((c for c in df_con.columns if 'regimen' in c.lower()), None)
        if col_reg: df_con['regimen'] = df_con[col_reg].fillna('Sin Dato')
        else: df_con['regimen'] = 'Sin Dato'

        # Año
        col_year = next((c for c in df_con.columns if 'anio' in c.lower() or 'year' in c.lower() or 'fecha_firma' in c.lower()), None)
        if col_year:
             # Si es fecha completa, extraer año
             try:
                 df_con['anio_ultimo_contrato'] = pd.to_numeric(df_con[col_year], errors='coerce').fillna(2024).astype(int)
             except:
                 df_con['anio_ultimo_contrato'] = 2024
        else:
            df_con['anio_ultimo_contrato'] = 2024

    return df_ent, df_con

df_ent, df_con = load_data()

# ==========================================
# 3. INTERFAZ Y SIDEBAR
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
    
    # --- DEBUGGER VISUAL ---
    with st.expander("🛠️ Ver Columnas del Archivo"):
        if not df_ent.empty:
            st.write("**Entidades:**")
            st.write(list(df_ent.columns))
        if not df_con.empty:
            st.write("**Contratistas:**")
            st.write(list(df_con.columns))

# ================= SECCIÓN: HOME =================
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
    crit = len(df_con[df_con['Riesgo']=='CRÍTICA']) if 'Riesgo' in df_con.columns else 0
    k3.metric("Alertas Críticas", f"{crit:,}", delta_color="inverse")

# ================= SECCIÓN: CONTRATOS =================
elif menu == "Contratos Secop":
    st.title("📊 Visión General")
    
    # Filtros
    sel_riesgo = st.multiselect("Filtrar Riesgo:", ['CRÍTICA', 'ALTA', 'MEDIA', 'OK'], default=['CRÍTICA', 'ALTA', 'MEDIA', 'OK'])
    df_f = df_con[df_con['Riesgo'].isin(sel_riesgo)] if 'Riesgo' in df_con.columns else df_con

    # Graficas
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("📆 Evolución de Riesgo")
        if 'anio_ultimo_contrato' in df_f.columns:
            df_evol = df_f.groupby(['anio_ultimo_contrato', 'Riesgo']).size().reset_index(name='Cantidad')
            df_evol['Año'] = df_evol['anio_ultimo_contrato'].astype(str)
            fig = px.bar(df_evol, x='Año', y='Cantidad', color='Riesgo', 
                         color_discrete_map={'CRÍTICA':'#EF4444', 'ALTA':'#F97316', 'MEDIA':'#FACC15', 'OK':'#10B981'})
            st.plotly_chart(fig, use_container_width=True)
    
    with g2:
        st.subheader("🏆 Top Entidades (Cantidad)")
        if 'cantidad_contratos' in df_ent.columns:
            top_c = df_ent.nlargest(10, 'cantidad_contratos')
            fig_c = px.pie(top_c, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.4)
            st.plotly_chart(fig_c, use_container_width=True)

# ================= SECCIÓN: ENTIDADES (CORREGIDO) =================
elif menu == "Entidades":
    st.title("🏢 Auditoría por Entidad")
    
    # 1. GRÁFICA DE MUNICIPIOS (REAL)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**Distribución Geográfica**")
        # Usamos la columna que normalizamos en load_data
        if 'municipio_grafica' in df_ent.columns:
            df_muni = df_ent['municipio_grafica'].value_counts().head(10).reset_index()
            df_muni.columns = ['Ubicación', 'Cantidad']
            # Filtramos 'Indeterminado' si es posible, o lo mostramos para saber que hay error
            fig_m = px.pie(df_muni, values='Cantidad', names='Ubicación', hole=0.5)
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.warning("No se pudo determinar la ubicación.")

    with col_g2:
        st.markdown("**Distribución por Tamaño**")
        if 'cantidad_contratos' in df_ent.columns:
            top_v = df_ent.nlargest(10, 'cantidad_contratos')
            fig_v = px.pie(top_v, values='cantidad_contratos', names='nombre_entidad_normalizado', hole=0.5)
            st.plotly_chart(fig_v, use_container_width=True)
    
    st.markdown("---")

    # 2. BUSCADOR
    text_filter = st.text_input("🔍 Buscar Entidad:", placeholder="Escribe el nombre...")
    all_ents = sorted(df_ent['nombre_entidad_normalizado'].astype(str).unique()) if 'nombre_entidad_normalizado' in df_ent.columns else []
    
    list_f = [e for e in all_ents if text_filter.upper() in e.upper()] if text_filter else all_ents
    sel_ent = st.selectbox("Seleccione:", list_f) if list_f else None

    # 3. DETALLE
    if sel_ent:
        row = df_ent[df_ent['nombre_entidad_normalizado'] == sel_ent].iloc[0]
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Presupuesto", fmt_cop(row.get('presupuesto_total_historico', 0)))
        k2.metric("Contratos", f"{row.get('cantidad_contratos', 0):,.0f}")
        k3.metric("Riesgo", f"{row.get('exposicion_riesgo_legal', 0):.1f}%")

        # 4. TABLA CONTRATISTAS (NOMBRE REAL)
        st.subheader("👷 Contratistas Asociados")
        # Buscar columna que sirva de filtro de entidad contratante
        col_ent_cont = next((c for c in df_con.columns if 'entidad_contratante' in c or 'entidad' in c), None)
        
        if col_ent_cont:
            df_sub = df_con[df_con[col_ent_cont].astype(str).str.contains(sel_ent, na=False, case=False)]
            
            if not df_sub.empty:
                # Mostrar columnas mapeadas
                df_view = df_sub.copy()
                df_view = df_view.rename(columns={
                    'nom_proveedor_final': 'Contratista',
                    'doc_proveedor': 'NIT/Doc',
                    'Riesgo': 'Nivel Riesgo',
                    'estado_afiliacion': 'Afiliación'
                })
                
                cols_final = ['Contratista', 'NIT/Doc', 'Nivel Riesgo', 'Afiliación']
                cols_ok = [c for c in cols_final if c in df_view.columns]
                st.dataframe(df_view[cols_ok], use_container_width=True)
            else:
                st.info("No se encontraron contratistas directos.")
        else:
            st.warning("No se encontró la columna de relación Entidad-Contratista.")

# ================= SECCIÓN: AFILIACIONES (MAESTRA) =================
elif menu == "Afiliaciones":
    st.title("🏥 Control de Seguridad Social")
    
    # Gráficas Torta
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

    # Tabla Maestra
    col_ent_cont = next((c for c in df_con.columns if 'entidad_contratante' in c or 'entidad' in c), None)
    
    if col_ent_cont and 'Riesgo' in df_con.columns:
        df_con['crit'] = (df_con['Riesgo']=='CRÍTICA').astype(int)
        df_con['alto'] = (df_con['Riesgo']=='ALTA').astype(int)
        df_con['medio'] = (df_con['Riesgo']=='MEDIA').astype(int)
        df_con['ok'] = (df_con['Riesgo']=='OK').astype(int)
        
        board = df_con.groupby(col_ent_cont)[['crit', 'alto', 'medio', 'ok']].sum().reset_index()
        board['Total Contratos'] = board['crit'] + board['alto'] + board['medio'] + board['ok']
        board['Total Alertas'] = board['crit'] + board['alto'] + board['medio']
        board['% Cumplimiento'] = (board['ok'] / board['Total Contratos']) * 100
        board['% Cumplimiento'] = board['% Cumplimiento'].fillna(0)
        
        def get_semaforo(val): return "🟢" if val >= 90 else "🟡" if val >= 50 else "🔴"
        board['Semáforo'] = board['% Cumplimiento'].apply(get_semaforo)
        
        board = board.sort_values('% Cumplimiento', ascending=True)
        
        st.dataframe(
            board,
            column_order=[col_ent_cont, 'Total Contratos', 'crit', 'alto', 'medio', 'ok', 'Total Alertas', '% Cumplimiento', 'Semáforo'],
            column_config={
                col_ent_cont: st.column_config.TextColumn("Entidad", width="large"),
                "crit": "🔴 Crítico", "alto": "🟠 Alto", "medio": "🟡 Medio", "ok": "🟢 OK",
                "% Cumplimiento": st.column_config.ProgressColumn("Cumplimiento", format="%.1f%%", min_value=0, max_value=100)
            },
            use_container_width=True,
            hide_index=True
        )
