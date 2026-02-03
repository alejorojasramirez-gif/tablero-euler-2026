import streamlit as st
import os
import pandas as pd

st.set_page_config(page_title="Diagnóstico EULER", layout="wide")

st.title("🕵️‍♂️ MODO DETECTIVE: ¿Dónde están mis archivos?")

st.markdown("---")
st.write("### 1. ¿Qué archivos ve Streamlit en la carpeta?")
# Esto nos mostrará la lista real de archivos que existen
archivos = os.listdir(".")
st.code(archivos)

st.markdown("---")
st.write("### 2. Verificación de Nombres Exactos")

# Chequeo Entidades
if "entidad_final.csv.gz" in archivos:
    st.success("✅ 'entidad_final.csv.gz' ENCONTRADO.")
    try:
        df = pd.read_csv("entidad_final.csv.gz", sep=";", compression="gzip")
        st.write(f"   -> Filas leídas: {len(df)}")
    except Exception as e:
        st.error(f"   -> El archivo existe pero falló al leer: {e}")
else:
    st.error("❌ NO ENCUENTRO 'entidad_final.csv.gz'")
    st.warning("Busca en la lista de arriba si se llama diferente (Ej: 'Entidad_final', 'entidad.csv', etc).")

# Chequeo Contratistas
if "contratista_final.csv.gz" in archivos:
    st.success("✅ 'contratista_final.csv.gz' ENCONTRADO.")
else:
    st.error("❌ NO ENCUENTRO 'contratista_final.csv.gz'")

st.markdown("---")
st.info("Si ves cruces rojas ❌, compara el nombre que esperábamos con la lista del paso 1.")
