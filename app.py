import streamlit as st
import pandas as pd
import plotly.express as px
import json
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA (Debe ser lo primero) ---
st.set_page_config(
    page_title="Tablero EULER 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
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

# --- FUNCIÓN DE CARGA ROBUSTA ---
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

# --- PROCESAMIENTO DE JSON (Para gráficas avanzadas) ---
def parse_json_column(df, column_name):
    """Convierte columnas de texto JSON en DataFrames usables"""
    if column_name not in df.columns:
        return pd.DataFrame()
    
    data_list = []
    for index, row in df.iterrows():
        try:
            val = row[column_name]
            if isinstance(val, str):
                val = val.replace("'", '"') # Corregir comillas simples
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    parsed['entidad'] = row.get('nombre_entidad_normalizado', f"Entidad {index}")
                    data_list.append(parsed)
        except:
            continue
    return pd.DataFrame(data_list)

# --- CARGA ---
df_ent, df_con = load_data()

if df_ent.empty:
    st.error("⚠️ No se pudieron cargar los datos. Revisa los archivos en GitHub.")
    st.stop()

# ==============================================================================
#                             SIDEBAR (FILTROS)
# ==============================================================================
st.sidebar.image("LogoEuler.png", use_column_width=True) if "LogoEuler.png" in st.sidebar else None
st.sidebar.title("🔍 Panel de Control")

# Filtro 1: Departamento
if 'departamento_base' in df_ent.columns:
    deptos = sorted(df_ent['departamento_base'].dropna().astype(str).unique())
    selected_depto = st.sidebar.selectbox("📍 Filtrar por Departamento:", ["Todos"] + deptos)
    
    if selected_depto != "Todos":
        df_ent = df_ent[df_ent['departamento_base'] == selected_depto]

# Filtro 2: Rango de Presupuesto
if 'presupuesto_total_historico' in df_ent.columns:
    min_val = float(df_ent['presupuesto_total_historico'].min())
    max_val = float(df_ent['presupuesto_total_historico'].max())
    
    # Usamos logaritmo para sliders de dinero porque los rangos son gigantes
    val_range = st.sidebar.slider(
        "💰 Rango de Presupuesto (Millones)",
        min_value=0.0,
        max_value=max_val/1_000_000,
        value=(0.0, max_val/1_000_000)
    )
    mask = (df_ent['presupuesto_total_historico'] >= val_range[0]*1_000_000) & \
           (df_ent['presupuesto_total_historico'] <= val_range[1]*1_000_000)
    df_ent = df_ent[mask]

st.sidebar.markdown("---")
st.sidebar.info(f"Mostrando {len(df_ent)} entidades filtradas.")

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
    # Calcular promedio de riesgo legal si existe
    if 'exposicion_riesgo_legal' in df_ent.columns:
        riesgo = df_ent['exposicion_riesgo_legal'].mean()
        st.metric("⚖️ Riesgo Legal Prom.", f"{riesgo:.1f}%")
    else:
        st.metric("⚖️ Riesgo Legal", "N/A")

st.markdown("---")

# --- SECCIÓN GRÁFICA ---
tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "🏛️ Detalle Entidades", "🏗️ Detalle Contratistas"])

# === PESTAÑA 1: PANORAMA ===
with tab1:
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Distribución por Departamento")
        if 'departamento_base' in df_ent.columns:
            conteo_depto = df_ent['departamento_base'].value_counts().reset_index()
            conteo_depto.columns = ['Departamento', 'Cantidad']
            fig_map = px.bar(conteo_depto.head(10), x='Cantidad', y='Departamento', orientation='h', color='Cantidad', title="Top 10 Departamentos con más Entidades")
            fig_map.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_map, use_container_width=True)

    with c2:
        st.subheader("Modalidad de Contratación (Global)")
        # Intentar parsear el JSON de modalidades para hacer una gráfica real
        if 'json_por_modalidad' in df_ent.columns:
            try:
                # Truco rápido: Sumar los textos JSON es muy difícil, usamos una aproximación visual simple o datos agregados
                st.info("💡 Análisis de modalidades disponible en detalle por entidad.")
                # Aquí podríamos expandir si tuviéramos tiempo de procesar todo el JSON globalmente
            except:
                pass
        
        # Gráfica alternativa: Presupuesto vs Cantidad
        if 'presupuesto_total_historico' in df_ent.columns and 'cantidad_contratos' in df_ent.columns:
            fig_scatter = px.scatter(
                df_ent, 
                x='cantidad_contratos', 
                y='presupuesto_total_historico',
                size='cantidad_contratos',
                color='departamento_base' if 'departamento_base' in df_ent.columns else None,
                hover_name='nombre_entidad_normalizado',
                log_y=True,
                title="Relación: Cantidad de Contratos vs Presupuesto (Escala Log)"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# === PESTAÑA 2: ENTIDADES (TABLA FULL) ===
with tab2:
    st.subheader("🔍 Ranking de Entidades")
    
    # Selector de columnas para la tabla
    cols_to_show = ['nombre_entidad_normalizado', 'presupuesto_total_historico', 'cantidad_contratos', 'departamento_base']
    # Filtrar solo las que existen
    cols_to_show = [c for c in cols_to_show if c in df_ent.columns]
    
    # Ordenar
    df_sorted = df_ent.sort_values('presupuesto_total_historico', ascending=False)
    
    # Mostrar tabla interactiva
    st.dataframe(
        df_sorted[cols_to_show].style.format({'presupuesto_total_historico': '${:,.0f}'}),
        use_container_width=True,
        height=500
    )

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
            title="Top 20 Contratistas por Monto Adjudicado",
            color='valor_total_historico',
            color_continuous_scale='Viridis'
        )
        fig_con.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_con, use_container_width=True)
        
        st.write("Datos detallados:")
        st.dataframe(df_con.head(100))
    else:
        st.warning("No hay datos suficientes de contratistas.")

# Footer
st.markdown("---")
st.caption("Desarrollado con Tecnología EULER © 2026 | Datos SECOP II")
