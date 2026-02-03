import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Tablero EULER 2026",
    page_icon="📊",
    layout="wide"
)

# --- FUNCIÓN DE CARGA DE DATOS ---
@st.cache_data
def load_data():
    # Nombres exactos confirmados por el Modo Detective
    file_ent = "entidad_final.csv.gz"
    file_con = "contratista_final.csv.gz"
    
    # 1. Cargar Entidades
    try:
        df_ent = pd.read_csv(file_ent, sep=";", compression="gzip", encoding='utf-8')
    except Exception as e:
        st.error(f"Error leyendo {file_ent}: {e}")
        df_ent = pd.DataFrame()

    # 2. Cargar Contratistas
    try:
        df_con = pd.read_csv(file_con, sep=";", compression="gzip", encoding='utf-8')
    except Exception as e:
        st.error(f"Error leyendo {file_con}: {e}")
        df_con = pd.DataFrame()

    return df_ent, df_con

# --- EJECUTAR CARGA ---
df_ent, df_con = load_data()

# --- VALIDACIÓN FINAL ---
if df_ent.empty or df_con.empty:
    st.warning("⚠️ Los archivos se cargaron pero parecen estar vacíos o hubo un error de lectura.")
    st.stop()

# ==============================================================================
#                             INTERFAZ DEL TABLERO
# ==============================================================================

# Título y Logo (si existe)
col_header_1, col_header_2 = st.columns([1, 5])
with col_header_1:
    # Intenta cargar el logo si existe, si no, no pasa nada
    try:
        st.image("LogoEuler.png", use_column_width=True)
    except:
        st.write("📊")
with col_header_2:
    st.title("Tablero de Control de Riesgo - EULER 2026")
    st.markdown("**Fuente:** Datos procesados de SECOP II")

st.markdown("---")

# --- SIDEBAR: FILTROS ---
st.sidebar.header("🔍 Filtros de Visualización")

# Filtro 1: Departamento (si existe la columna)
if 'departamento_base' in df_ent.columns:
    lista_deptos = sorted(df_ent['departamento_base'].dropna().astype(str).unique())
    depto_sel = st.sidebar.selectbox("Filtrar por Departamento:", ["Todos"] + lista_deptos)
    
    if depto_sel != "Todos":
        df_ent = df_ent[df_ent['departamento_base'] == depto_sel]
        st.sidebar.success(f"Filtrado: {depto_sel}")

# --- KPIS PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏢 Entidades Analizadas", f"{len(df_ent):,}")

with col2:
    st.metric("👷 Contratistas Analizados", f"{len(df_con):,}")

with col3:
    if 'presupuesto_total_historico' in df_ent.columns:
        total_pres = df_ent['presupuesto_total_historico'].sum()
        st.metric("💰 Presupuesto Global", f"${total_pres:,.0f}")
    else:
        st.metric("💰 Presupuesto", "N/A")

with col4:
    if 'cantidad_contratos' in df_ent.columns:
        total_contratos = df_ent['cantidad_contratos'].sum()
        st.metric("📄 Total Contratos", f"{total_contratos:,}")
    else:
        st.metric("📄 Contratos", "N/A")

st.markdown("---")

# --- PESTAÑAS DE ANÁLISIS ---
tab_ent, tab_con = st.tabs(["🏛️ ANÁLISIS DE ENTIDADES", "🏗️ ANÁLISIS DE CONTRATISTAS"])

# === PESTAÑA 1: ENTIDADES ===
with tab_ent:
    col_g1, col_g2 = st.columns(2)
    
    # Gráfica 1: Top Presupuesto
    with col_g1:
        st.subheader("Top 10 Entidades por Presupuesto")
        if 'presupuesto_total_historico' in df_ent.columns:
            top_budget = df_ent.nlargest(10, 'presupuesto_total_historico').sort_values('presupuesto_total_historico', ascending=True)
            fig_bar = px.bar(
                top_budget, 
                x='presupuesto_total_historico', 
                y='nombre_entidad_normalizado', 
                orientation='h',
                text_auto='.2s',
                color='presupuesto_total_historico',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(xaxis_title="Presupuesto Total", yaxis_title="Entidad", showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Columna 'presupuesto_total_historico' no encontrada.")

    # Gráfica 2: Top Cantidad de Contratos
    with col_g2:
        st.subheader("Top 10 Entidades por Volumen de Contratos")
        if 'cantidad_contratos' in df_ent.columns:
            top_qty = df_ent.nlargest(10, 'cantidad_contratos').sort_values('cantidad_contratos', ascending=True)
            fig_bar2 = px.bar(
                top_qty, 
                x='cantidad_contratos', 
                y='nombre_entidad_normalizado', 
                orientation='h',
                text_auto=True,
                color='cantidad_contratos',
                color_continuous_scale='Oranges'
            )
            fig_bar2.update_layout(xaxis_title="Cantidad de Contratos", yaxis_title="Entidad", showlegend=False)
            st.plotly_chart(fig_bar2, use_container_width=True)
        else:
            st.info("Columna 'cantidad_contratos' no encontrada.")

    # Tabla de Datos
    st.subheader("📋 Detalle de Entidades")
    st.dataframe(df_ent)

# === PESTAÑA 2: CONTRATISTAS ===
with tab_con:
    st.subheader("Top Contratistas por Valor Ganado")
    
    if 'valor_total_historico' in df_con.columns:
        # Aseguramos que sea numérico
        df_con['valor_total_historico'] = pd.to_numeric(df_con['valor_total_historico'], errors='coerce').fillna(0)
        
        top_con = df_con.nlargest(15, 'valor_total_historico').sort_values('valor_total_historico', ascending=True)
        
        # Usamos documento porque a veces no hay nombre
        eje_y = 'doc_proveedor'
        
        fig_con = px.bar(
            top_con, 
            x='valor_total_historico', 
            y=eje_y, 
            orientation='h',
            title="Top 15 Contratistas (Por Documento/NIT)",
            text_auto='.2s',
            color='valor_total_historico',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_con, use_container_width=True)
    else:
        st.warning("No se encontró la columna 'valor_total_historico'.")

    st.subheader("📋 Base de Datos de Contratistas")
    st.dataframe(df_con.head(1000)) # Mostramos los primeros 1000 para no saturar
