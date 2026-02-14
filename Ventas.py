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

# -------------------- FUNCIÓN PARA CARGAR EMPLEADOS --------------------
def cargar_empleados():
    """Carga la lista de empleados desde la sesión o usa la lista por defecto"""
    if 'empleados' not in st.session_state:
        st.session_state.empleados = [
            "Angel Bonilla", "Claudia Parada", "Cristina Gomez", "Daniela Velasco",
            "Darcy Tovar", "Erika Salazar", "Estheiry Cardozo", "Janeth Jimenez",
            "Jessica Sanabria", "Johanna Cuervo", "Leonardo Vera", "Lucia Guerrero",
            "Luna Galindez", "Mariana Mejia", "Niyireth Silva", "Ruth Avila", "Valeria Delgado"
        ]
    return st.session_state.empleados

# -------------------- FUNCIÓN PARA GUARDAR EMPLEADOS --------------------
def guardar_empleados(nueva_lista):
    """Guarda la nueva lista de empleados en la sesión"""
    st.session_state.empleados = nueva_lista

# -------------------- UI --------------------
st.title("📊 Equipo Locatel Restrepo")

# Menú principal
menu = st.sidebar.radio("Menú", ["📝 Registrar Ventas", "📋 Ver Registros", "📈 Dashboard", "⚙️ Administrar Empleados"])

empleados = cargar_empleados()

# -------------------- ADMINISTRAR EMPLEADOS --------------------
if menu == "⚙️ Administrar Empleados":
    st.subheader("👥 Administrar Lista de Empleados")
    
    st.info("Aquí puedes modificar los nombres de las personas que aparecen en el registro diario.")
    
    # Mostrar lista actual
    st.write("**Lista actual de empleados:**")
    empleados_actuales = st.session_state.empleados.copy()
    
    # Editor de empleados
    with st.form("form_empleados"):
        st.write("Edita la lista de empleados (un nombre por línea):")
        nombres_texto = st.text_area(
            "Nombres de empleados",
            value="\n".join(empleados_actuales),
            height=300,
            help="Escribe un nombre por línea. Los cambios se guardarán al hacer clic en 'Guardar Cambios'"
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            guardar = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
        with col2:
            restaurar = st.form_submit_button("🔄 Restaurar Original", use_container_width=True)
    
    if guardar:
        # Procesar el texto y crear lista (eliminar líneas vacías y espacios extras)
        nueva_lista = [nombre.strip() for nombre in nombres_texto.split('\n') if nombre.strip()]
        if nueva_lista:
            guardar_empleados(nueva_lista)
            st.success(f"✅ Lista de empleados actualizada correctamente ({len(nueva_lista)} empleados)")
            st.rerun()
        else:
            st.error("❌ La lista no puede estar vacía")
    
    if restaurar:
        # Restaurar lista original
        lista_original = [
            "Angel Bonilla", "Claudia Parada", "Cristina Gomez", "Daniela Velasco",
            "Darcy Tovar", "Erika Salazar", "Estheiry Cardozo", "Janeth Jimenez",
            "Jessica Sanabria", "Johanna Cuervo", "Leonardo Vera", "Lucia Guerrero",
            "Luna Galindez", "Mariana Mejia", "Niyireth Silva", "Ruth Avila", "Valeria Delgado"
        ]
        guardar_empleados(lista_original)
        st.success("✅ Lista restaurada a la original")
        st.rerun()
    
    # Vista previa de cómo se verá en el selector
    st.divider()
    st.write("**Vista previa del selector de empleados:**")
    st.selectbox("Así se verá en el registro diario", st.session_state.empleados)

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

    if not df.empty:
        # Convertir a Excel para descargar
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