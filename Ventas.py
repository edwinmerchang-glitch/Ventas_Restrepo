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

# -------------------- LISTA DE EMPLEADOS --------------------
empleados = [
    "Angel Bonilla",
    "Claudia Parada",
    "Cristina Gomez",
    "Daniela Velasco",
    "Darcy Tovar",
    "Erika Salazar",
    "Estheiry Cardozo",
    "Janeth Jimenez",
    "Jessica Sanabria",
    "Johanna Cuervo",
    "Leonardo Vera",
    "Lucia Guerrero",
    "Luna Galindez",
    "Mariana Mejia",
    "Niyireth Silva",
    "Ruth Avila",
    "Valeria Delgado",
]

# -------------------- FUNCIONES DE PÁGINAS --------------------
def pagina_malla():
    st.title("📊 Malla")
    st.info("Aquí va el contenido de Malla")
    
    # Aquí puedes poner el dashboard actual o lo que necesites
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

def pagina_empleados():
    st.title("👥 Empleados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Registro Diario de Ventas")
        fecha = st.date_input("📅 Fecha", key="fecha_registro")
        empleado = st.selectbox("👤 Nombre", empleados, key="empleado_select")
        
        autoliquidable = st.number_input("Autoliquidable", min_value=0, step=1, key="auto")
        oferta = st.number_input("Oferta de la semana", min_value=0, step=1, key="ofer")
        marca_propia = st.number_input("Marca propia", min_value=0, step=1, key="marca")
        producto = st.number_input("Producto adicional", min_value=0, step=1, key="prod")
        
        if st.button("💾 Guardar registro", use_container_width=True):
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO registros_ventas
                (fecha, empleado, autoliquidable, oferta, marca_propia, producto_adicional)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fecha, empleado, autoliquidable, oferta, marca_propia, producto))
            conn.commit()
            conn.close()
            st.success("✅ Registro guardado")
    
    with col2:
        st.subheader("Lista de Empleados")
        for i, emp in enumerate(empleados, 1):
            st.write(f"{i}. {emp}")
        
        # Opción para agregar empleados (simple)
        with st.expander("➕ Agregar nuevo empleado"):
            nuevo_empleado = st.text_input("Nombre del nuevo empleado")
            if st.button("Agregar"):
                if nuevo_empleado and nuevo_empleado not in empleados:
                    empleados.append(nuevo_empleado)
                    st.success(f"✅ {nuevo_empleado} agregado")
                    st.rerun()
                else:
                    st.error("El empleado ya existe o el nombre está vacío")

def pagina_config():
    st.title("⚙️ Configuración")
    
    st.subheader("Ajustes de la aplicación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Configuración general**")
        tema = st.selectbox("Tema", ["Claro", "Oscuro", "Sistema"])
        idioma = st.selectbox("Idioma", ["Español", "Inglés"])
        
    with col2:
        st.write("**Configuración de ventas**")
        productos_adicionales = st.multiselect(
            "Productos adicionales activos",
            ["Producto 1", "Producto 2", "Producto 3", "Producto 4"]
        )
    
    if st.button("Guardar configuración"):
        st.success("Configuración guardada")

def pagina_usuarios():
    st.title("👤 Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["Usuarios activos", "Agregar usuario", "Permisos"])
    
    with tab1:
        st.dataframe({
            "Usuario": ["admin", "usuario1", "usuario2"],
            "Rol": ["Administrador", "Vendedor", "Vendedor"],
            "Último acceso": ["2026-02-13", "2026-02-12", "2026-02-11"]
        })
    
    with tab2:
        st.text_input("Nombre de usuario")
        st.text_input("Contraseña", type="password")
        st.selectbox("Rol", ["Administrador", "Vendedor", "Supervisor"])
        if st.button("Crear usuario"):
            st.success("Usuario creado")

def pagina_backup():
    st.title("💾 Backup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Crear backup")
        if st.button("📀 Crear backup ahora", use_container_width=True):
            # Aquí iría la lógica de backup
            st.success("Backup creado exitosamente")
    
    with col2:
        st.subheader("Restaurar backup")
        archivo_backup = st.file_uploader("Seleccionar archivo de backup", type=['db', 'sqlite'])
        if archivo_backup and st.button("Restaurar"):
            st.warning("¿Estás seguro? Esto sobrescribirá los datos actuales")
            # Aquí iría la lógica de restauración

def pagina_sistema():
    st.title("🖥️ Sistema")
    
    st.subheader("Información del sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Versión", "1.0.0")
        st.metric("Base de datos", "SQLite")
        st.metric("Registros totales", "150")
    
    with col2:
        st.metric("Última actualización", "2026-02-13")
        st.metric("Espacio usado", "2.3 MB")
        st.metric("Estado", "✅ Online")
    
    st.subheader("Logs del sistema")
    st.text_area("Registro de actividades", 
                 "2026-02-13 20:04: Usuario admin inició sesión\n2026-02-13 19:30: Backup automático completado",
                 height=150)

# -------------------- UI PRINCIPAL --------------------
# Estilo personalizado para el menú
st.markdown("""
<style>
    /* Estilo para el menú lateral */
    .css-1d391kg {
        padding-top: 1rem;
    }
    
    /* Estilo para los items del menú */
    .stRadio > div {
        padding: 0.5rem;
    }
    
    /* Espaciado entre items */
    .stRadio [role="radiogroup"] {
        gap: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Menú superior con la hora
col_hora, col_menu = st.columns([1, 5])

with col_hora:
    st.markdown(f"**{datetime.now().strftime('%H:%M')}**")
    st.markdown(f"{datetime.now().strftime('%d/%m • %A')}")

with col_menu:
    st.markdown("### Admin")

# Menú lateral con las opciones de la imagen
with st.sidebar:
    st.markdown("## 🏢 Locatel Restrepo")
    st.divider()
    
    opcion = st.radio(
        "Menú",
        ["Malla", "Empleados", "Config", "Usuarios", "Backup", "Sistema"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption(f"Usuario: Admin")
    st.caption(f"Último acceso: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# -------------------- NAVEGACIÓN --------------------
if opcion == "Malla":
    pagina_malla()
elif opcion == "Empleados":
    pagina_empleados()
elif opcion == "Config":
    pagina_config()
elif opcion == "Usuarios":
    pagina_usuarios()
elif opcion == "Backup":
    pagina_backup()
elif opcion == "Sistema":
    pagina_sistema()