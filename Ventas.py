import streamlit as st
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Equipo Locatel Restrepo", layout="wide")

# -------------------- DB --------------------
def get_connection():
    return sqlite3.connect("ventas.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabla de ventas
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
    
    # Tabla de empleados
    c.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de usuarios del sistema
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            rol TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_acceso TIMESTAMP
        )
    """)
    
    # Insertar empleados por defecto si no existen
    empleados_default = [
        "Angel Bonilla", "Claudia Parada", "Cristina Gomez", "Daniela Velasco",
        "Darcy Tovar", "Erika Salazar", "Estheiry Cardozo", "Janeth Jimenez",
        "Jessica Sanabria", "Johanna Cuervo", "Leonardo Vera", "Lucia Guerrero",
        "Luna Galindez", "Mariana Mejia", "Niyireth Silva", "Ruth Avila", "Valeria Delgado"
    ]
    
    for emp in empleados_default:
        try:
            c.execute("INSERT OR IGNORE INTO empleados (nombre) VALUES (?)", (emp,))
        except:
            pass
    
    # Insertar usuario admin por defecto
    try:
        c.execute("INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
                  ("admin", "admin123", "Administrador"))
    except:
        pass
    
    conn.commit()
    conn.close()

create_tables()

# -------------------- FUNCIONES PARA EMPLEADOS --------------------
def cargar_empleados_db():
    """Carga los empleados desde la base de datos"""
    conn = get_connection()
    df = pd.read_sql("SELECT nombre FROM empleados WHERE activo = 1 ORDER BY nombre", conn)
    conn.close()
    return df['nombre'].tolist() if not df.empty else []

def guardar_empleado_db(nombre):
    """Guarda un nuevo empleado en la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO empleados (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def eliminar_empleado_db(nombre):
    """Elimina (desactiva) un empleado de la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE empleados SET activo = 0 WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()

# -------------------- FUNCIONES PARA CONFIGURACIÓN --------------------
ARCHIVO_CONFIG = "config.json"

def cargar_config():
    """Carga la configuración desde el archivo JSON"""
    if os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "tema": "Claro",
        "idioma": "Español",
        "productos_adicionales": ["Producto 1", "Producto 2", "Producto 3", "Producto 4"],
        "productos_seleccionados": []
    }

def guardar_config(config):
    """Guarda la configuración en el archivo JSON"""
    with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# -------------------- FUNCIONES PARA USUARIOS --------------------
def cargar_usuarios_db():
    """Carga los usuarios desde la base de datos"""
    conn = get_connection()
    df = pd.read_sql("SELECT username, rol, ultimo_acceso FROM usuarios", conn)
    conn.close()
    return df

def crear_usuario_db(username, password, rol):
    """Crea un nuevo usuario en la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
                  (username, password, rol))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def actualizar_ultimo_acceso(username):
    """Actualiza la fecha de último acceso del usuario"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET ultimo_acceso = ? WHERE username = ?",
              (datetime.now(), username))
    conn.commit()
    conn.close()

# -------------------- INICIALIZAR ESTADO DE LA SESIÓN --------------------
def inicializar_estado():
    """Inicializa todas las variables de sesión"""
    if 'empleados' not in st.session_state:
        st.session_state.empleados = cargar_empleados_db()
    
    if 'config' not in st.session_state:
        st.session_state.config = cargar_config()
    
    if 'usuario_actual' not in st.session_state:
        st.session_state.usuario_actual = "admin"
        actualizar_ultimo_acceso("admin")

# Llamar a la función para inicializar
inicializar_estado()

# -------------------- FUNCIONES DE PÁGINAS --------------------
def pagina_empleados():
    st.title("👥 Empleados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Registro Diario de Ventas")
        fecha = st.date_input("📅 Fecha", key="fecha_registro")
        
        if not st.session_state.empleados:
            st.warning("⚠️ No hay empleados registrados. Agrega empleados en la sección de la derecha.")
            empleado = st.selectbox("👤 Nombre", ["Sin empleados"])
        else:
            empleado = st.selectbox("👤 Nombre", st.session_state.empleados, key="empleado_select")
        
        autoliquidable = st.number_input("Autoliquidable", min_value=0, step=1, key="auto")
        oferta = st.number_input("Oferta de la semana", min_value=0, step=1, key="ofer")
        marca_propia = st.number_input("Marca propia", min_value=0, step=1, key="marca")
        producto = st.number_input("Producto adicional", min_value=0, step=1, key="prod")
        
        if st.button("💾 Guardar registro", use_container_width=True):
            if st.session_state.empleados:
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
                st.rerun()
            else:
                st.error("❌ No hay empleados para registrar ventas")
    
    with col2:
        st.subheader("📋 Lista de Empleados")
        
        # Mostrar lista actual
        if st.session_state.empleados:
            for i, emp in enumerate(st.session_state.empleados, 1):
                st.write(f"{i}. {emp}")
        else:
            st.info("No hay empleados registrados")
        
        st.divider()
        
        # Opción para agregar empleados
        with st.expander("➕ Agregar nuevo empleado", expanded=True):
            nuevo_empleado = st.text_input("Nombre del nuevo empleado")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Agregar", use_container_width=True):
                    if nuevo_empleado:
                        if guardar_empleado_db(nuevo_empleado):
                            st.session_state.empleados = cargar_empleados_db()
                            st.success(f"✅ {nuevo_empleado} agregado permanentemente")
                            st.rerun()
                        else:
                            st.error("❌ El empleado ya existe")
                    else:
                        st.error("❌ El nombre no puede estar vacío")
        
        # Opción para eliminar empleados
        if st.session_state.empleados:
            with st.expander("➖ Eliminar empleado"):
                empleado_a_eliminar = st.selectbox("Seleccionar empleado", st.session_state.empleados, key="eliminar_emp")
                if st.button("Eliminar", use_container_width=True):
                    if len(st.session_state.empleados) > 1:
                        eliminar_empleado_db(empleado_a_eliminar)
                        st.session_state.empleados = cargar_empleados_db()
                        st.success(f"✅ {empleado_a_eliminar} eliminado permanentemente")
                        st.rerun()
                    else:
                        st.error("❌ No puedes eliminar el último empleado")

def pagina_config():
    st.title("⚙️ Configuración")
    
    st.subheader("Ajustes de la aplicación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Configuración general**")
        tema = st.selectbox("Tema", ["Claro", "Oscuro", "Sistema"], 
                           index=["Claro", "Oscuro", "Sistema"].index(st.session_state.config.get("tema", "Claro")))
        idioma = st.selectbox("Idioma", ["Español", "Inglés"],
                             index=["Español", "Inglés"].index(st.session_state.config.get("idioma", "Español")))
        
    with col2:
        st.write("**Configuración de ventas**")
        opciones_productos = st.session_state.config.get("productos_adicionales", ["Producto 1", "Producto 2", "Producto 3", "Producto 4"])
        productos_seleccionados = st.multiselect(
            "Productos adicionales activos",
            opciones_productos,
            default=st.session_state.config.get("productos_seleccionados", [])
        )
    
    if st.button("Guardar configuración", use_container_width=True):
        # Actualizar configuración
        st.session_state.config.update({
            "tema": tema,
            "idioma": idioma,
            "productos_seleccionados": productos_seleccionados
        })
        guardar_config(st.session_state.config)
        st.success("✅ Configuración guardada permanentemente")

def pagina_usuarios():
    st.title("👤 Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["Usuarios activos", "Agregar usuario", "Permisos"])
    
    with tab1:
        usuarios_df = cargar_usuarios_db()
        if not usuarios_df.empty:
            st.dataframe(usuarios_df, use_container_width=True)
        else:
            st.info("No hay usuarios registrados")
    
    with tab2:
        with st.form("form_usuario"):
            nuevo_usuario = st.text_input("Nombre de usuario")
            nueva_password = st.text_input("Contraseña", type="password")
            nuevo_rol = st.selectbox("Rol", ["Administrador", "Vendedor", "Supervisor"])
            
            if st.form_submit_button("Crear usuario", use_container_width=True):
                if nuevo_usuario and nueva_password:
                    if crear_usuario_db(nuevo_usuario, nueva_password, nuevo_rol):
                        st.success(f"✅ Usuario {nuevo_usuario} creado permanentemente")
                        st.rerun()
                    else:
                        st.error("❌ El nombre de usuario ya existe")
                else:
                    st.error("❌ Todos los campos son obligatorios")
    
    with tab3:
        st.info("🔧 Módulo de permisos en desarrollo")

def pagina_backup():
    st.title("💾 Backup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📀 Crear backup")
        st.write("Crea una copia de seguridad de toda la base de datos")
        
        if st.button("Crear backup ahora", use_container_width=True):
            # Crear backup de la base de datos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_backup = f"backup_ventas_{timestamp}.db"
            
            import shutil
            shutil.copy2("ventas.db", nombre_backup)
            
            # También respaldar configuración
            if os.path.exists("config.json"):
                shutil.copy2("config.json", f"backup_config_{timestamp}.json")
            
            st.success(f"✅ Backup creado: {nombre_backup}")
            
            # Ofrecer descarga
            with open(nombre_backup, "rb") as f:
                st.download_button("📥 Descargar backup", f, nombre_backup)
    
    with col2:
        st.subheader("🔄 Restaurar backup")
        st.write("Selecciona un archivo de backup para restaurar")
        
        archivo_backup = st.file_uploader("Seleccionar archivo de backup", type=['db'])
        if archivo_backup and st.button("Restaurar", use_container_width=True):
            st.warning("⚠️ ¿Estás seguro? Esto sobrescribirá TODOS los datos actuales")
            col_si, col_no = st.columns(2)
            with col_si:
                if st.button("SÍ, restaurar"):
                    # Guardar el archivo subido
                    with open("ventas.db", "wb") as f:
                        f.write(archivo_backup.getbuffer())
                    st.success("✅ Base de datos restaurada")
                    st.rerun()
            with col_no:
                if st.button("No, cancelar"):
                    st.info("Restauración cancelada")

def pagina_sistema():
    st.title("🖥️ Sistema")
    
    st.subheader("Información del sistema")
    
    conn = get_connection()
    df_ventas = pd.read_sql("SELECT COUNT(*) as total FROM registros_ventas", conn)
    df_empleados = pd.read_sql("SELECT COUNT(*) as total FROM empleados WHERE activo = 1", conn)
    df_usuarios = pd.read_sql("SELECT COUNT(*) as total FROM usuarios", conn)
    conn.close()
    
    total_ventas = df_ventas['total'].iloc[0] if not df_ventas.empty else 0
    total_empleados = df_empleados['total'].iloc[0] if not df_empleados.empty else 0
    total_usuarios = df_usuarios['total'].iloc[0] if not df_usuarios.empty else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Versión", "1.0.0")
        st.metric("Base de datos", "SQLite")
        st.metric("Registros de ventas", total_ventas)
    
    with col2:
        st.metric("Empleados activos", total_empleados)
        st.metric("Usuarios del sistema", total_usuarios)
        st.metric("Archivo config", "✅ OK" if os.path.exists("config.json") else "⚠️ No existe")
    
    with col3:
        st.metric("Última actualización", datetime.now().strftime("%Y-%m-%d"))
        st.metric("Espacio DB", f"{os.path.getsize('ventas.db') / 1024:.1f} KB" if os.path.exists("ventas.db") else "0 KB")
        st.metric("Estado", "✅ Online")
    
    st.subheader("📋 Logs del sistema")
    st.text_area("Registro de actividades", 
                 f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: Sistema iniciado\n"
                 f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: Usuario {st.session_state.usuario_actual} activo\n"
                 f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {total_empleados} empleados cargados",
                 height=150)

def pagina_dashboard():
    st.title("📊 Dashboard de Ventas")
    
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM registros_ventas ORDER BY fecha DESC", conn)
    conn.close()
    
    if not df.empty:
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Autoliquidable", int(df["autoliquidable"].sum()))
        col2.metric("Oferta", int(df["oferta"].sum()))
        col3.metric("Marca Propia", int(df["marca_propia"].sum()))
        col4.metric("Producto Adicional", int(df["producto_adicional"].sum()))
        
        # Gráfico por empleado
        st.subheader("📊 Ventas por Empleado")
        ventas_por_empleado = df.groupby("empleado")[["autoliquidable","oferta","marca_propia","producto_adicional"]].sum()
        st.bar_chart(ventas_por_empleado)
        
        # Ventas por fecha
        st.subheader("📅 Ventas por Fecha")
        ventas_por_fecha = df.groupby("fecha")[["autoliquidable","oferta","marca_propia","producto_adicional"]].sum()
        st.line_chart(ventas_por_fecha)
        
        # Mostrar datos recientes
        st.subheader("📋 Ventas Recientes")
        st.dataframe(df.head(20), use_container_width=True)
        
        # Botón para exportar
        if st.button("📥 Exportar a Excel", use_container_width=True):
            excel = df.to_excel(index=False, engine='openpyxl')
            st.download_button("Descargar Excel", excel, "ventas_completas.xlsx")
    else:
        st.info("📭 Aún no hay datos registrados")

# -------------------- UI PRINCIPAL --------------------
# Estilo personalizado
st.markdown("""
<style>
    .css-1d391kg { padding-top: 1rem; }
    .stRadio > div { padding: 0.5rem; }
    .stRadio [role="radiogroup"] { gap: 0.5rem; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# Menú superior con la hora
col_hora, col_menu, col_usuario = st.columns([1, 3, 1])

with col_hora:
    st.markdown(f"**{datetime.now().strftime('%H:%M')}**")
    st.markdown(f"{datetime.now().strftime('%d/%m • %A')}")

with col_menu:
    st.markdown("### 🏢 Locatel Restrepo")

with col_usuario:
    st.markdown(f"**👤 {st.session_state.usuario_actual}**")

# Menú lateral
with st.sidebar:
    st.markdown("## Menú Principal")
    st.divider()
    
    opcion = st.radio(
        "Navegación",
        ["Empleados", "Dashboard", "Config", "Usuarios", "Backup", "Sistema"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption(f"Usuario: {st.session_state.usuario_actual}")
    st.caption(f"Último acceso: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"Empleados: {len(st.session_state.empleados)}")

# -------------------- NAVEGACIÓN --------------------
if opcion == "Empleados":
    pagina_empleados()
elif opcion == "Dashboard":
    pagina_dashboard()
elif opcion == "Config":
    pagina_config()
elif opcion == "Usuarios":
    pagina_usuarios()
elif opcion == "Backup":
    pagina_backup()
elif opcion == "Sistema":
    pagina_sistema()