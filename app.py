import streamlit as st

import streamlit as st

st.set_page_config(
    page_title="Arriendos",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Arriendos")
st.write("Bienvenido a nuestra aplicación de arriendos.")

st.divider()

st.header("Departamentos disponibles")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Serena Pacífico")
    st.write("Departamento disponible para arriendo.")

with col2:
    st.subheader("Las Gredas")
    st.write("Departamento disponible para arriendo.")

with col3:
    st.subheader("Oceanic")
    st.write("Departamento disponible para arriendo.")