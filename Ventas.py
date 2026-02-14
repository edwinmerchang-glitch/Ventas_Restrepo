import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Equipo Locatel Restrepo", layout="wide")

# -------------------- DB --------------------
def get_connection():
    return sqlite3.connect("ventas.db", check_same_thread=False)

def create_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS registros_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE,
            empleado TEXT,
            autoliquidable INTEGER,
            oferta INTEGER,
            marca_propia INTEGER,
            producto_adicional INTEGER,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

create_table()

# -------------------- UI --------------------
st.title("📊 Equipo Locatel Restrepo")
menu = st.sidebar.radio("Menú", ["📝 Registrar Ventas", "📋 Ver Registros", "📈 Dashboard"])

empleados = [
    "Angel Bonilla","Claudia Parada","Cristina Gomez","Daniela Velasco",
    "Darcy Tovar","Erika Salazar","Estheiry Cardozo","Janeth Jimenez",
    "Jessica Sanabria","Johanna Cuervo","Leonardo Vera","Lucia Guerrero",
    "Luna Galindez","Mariana Mejia","Niyireth Silva","Ruth Avila","Valeria Delgado"
]

# -------------------- REGISTRO --------------------
if menu == "📝 Registrar Ventas":
    st.subheader("Registro Diario")

    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("📅 Fecha")
        empleado = st.selectbox("👤 Nombre", empleados)

    with col2:
        autoliquidable = st.number_input("Autoliquidable", min_value=0, step=1)
        oferta = st.number_input("Oferta de la semana", min_value=0, step=1)
        marca_propia = st.number_input("Marca propia", min_value=0, step=1)
        producto = st.number_input("Producto adicional", min_value=0, step=1)

    if st.button("💾 Guardar registro"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO registros_ventas
            (fecha, empleado, autoliquidable, oferta, marca_propia, producto_adicional)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fecha, empleado, autoliquidable, oferta, marca_propia, producto))
        conn.commit()
        conn.close()

        st.success("✅ Registro guardado correctamente")

# -------------------- TABLA --------------------
if menu == "📋 Ver Registros":
    st.subheader("Base de Datos de Ventas")

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM registros_ventas ORDER BY fecha DESC", conn)
    conn.close()

    col1, col2 = st.columns(2)
    with col1:
        filtro_empleado = st.selectbox("Filtrar por empleado", ["Todos"] + empleados)
    with col2:
        filtro_fecha = st.date_input("Filtrar por fecha", value=None)

    if filtro_empleado != "Todos":
        df = df[df["empleado"] == filtro_empleado]

    if filtro_fecha:
        df = df[df["fecha"] == str(filtro_fecha)]

    st.dataframe(df, use_container_width=True)

    excel = df.to_excel(index=False, engine='openpyxl')
    st.download_button("📥 Descargar Excel", excel, "ventas_locatel.xlsx")

# -------------------- DASHBOARD --------------------
if menu == "📈 Dashboard":
    st.subheader("Indicadores")

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM registros_ventas", conn)
    conn.close()

    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Autoliquidable", int(df["autoliquidable"].sum()))
        col2.metric("Oferta", int(df["oferta"].sum()))
        col3.metric("Marca Propia", int(df["marca_propia"].sum()))
        col4.metric("Producto Adicional", int(df["producto_adicional"].sum()))

        st.bar_chart(df.groupby("empleado")[["autoliquidable","oferta","marca_propia","producto_adicional"]].sum())
    else:
        st.info("Aún no hay datos registrados")
