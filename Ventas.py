import streamlit as st
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Equipo Locatel Restrepo", layout="wide")

import streamlit as st
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Equipo Locatel Restrepo", layout="wide")

# Configuración para desarrollo - EVITA EL CACHÉ
import sys
if "streamlit run" in " ".join(sys.argv):
    # Deshabilitar caché en desarrollo
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "poll"
    os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# Forzar recarga de módulos
import importlib
import Ventas as self_module
importlib.reload(self_module)
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
    
    # Agregar columna departamento si no existe
    try:
        c.execute("ALTER TABLE empleados ADD COLUMN departamento TEXT DEFAULT 'Droguería'")
    except:
        pass  # La columna ya existe
    
    # Tabla de usuarios
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
    
    # Insertar empleados por defecto con departamento
    empleados_default = [
        ("Angel Bonilla", "Droguería"),
        ("Claudia Parada", "Droguería"),
        ("Cristina Gomez", "Equipos Médicos"),
        ("Daniela Velasco", "Tienda"),
        ("Darcy Tovar", "Cajas"),
        ("Erika Salazar", "Droguería"),
        ("Estheiry Cardozo", "Equipos Médicos"),
        ("Janeth Jimenez", "Tienda"),
        ("Jessica Sanabria", "Cajas"),
        ("Johanna Cuervo", "Droguería"),
        ("Leonardo Vera", "Equipos Médicos"),
        ("Lucia Guerrero", "Tienda"),
        ("Luna Galindez", "Cajas"),
        ("Mariana Mejia", "Droguería"),
        ("Niyireth Silva", "Equipos Médicos"),
        ("Ruth Avila", "Tienda"),
        ("Valeria Delgado", "Cajas")
    ]
    
    for emp, depto in empleados_default:
        try:
            c.execute("INSERT OR IGNORE INTO empleados (nombre, departamento) VALUES (?, ?)", (emp, depto))
        except:
            pass
    
    # Insertar usuario admin
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
    """Carga los nombres de empleados desde la base de datos"""
    conn = get_connection()
    df = pd.read_sql("SELECT nombre FROM empleados WHERE activo = 1 ORDER BY nombre", conn)
    conn.close()
    return df['nombre'].tolist() if not df.empty else []

def cargar_empleados_con_departamento():
    """Carga los empleados con su departamento"""
    conn = get_connection()
    df = pd.read_sql("SELECT nombre, departamento FROM empleados WHERE activo = 1 ORDER BY nombre", conn)
    conn.close()
    return df

def guardar_empleado_db(nombre, departamento):
    """Guarda un nuevo empleado en la base de datos con su departamento"""
    conn = get_connection()
    c = conn.cursor()
    try:
        # Verificar si el empleado ya existe (activo o inactivo)
        c.execute("SELECT activo FROM empleados WHERE nombre = ?", (nombre,))
        resultado = c.fetchone()
        
        if resultado:
            if resultado[0] == 0:
                # Si existe pero está inactivo, lo reactivamos
                c.execute("UPDATE empleados SET activo = 1, departamento = ? WHERE nombre = ?", (departamento, nombre))
                conn.commit()
                return True
            else:
                # Si existe y está activo
                return False
        else:
            # Si no existe, lo insertamos
            c.execute("INSERT INTO empleados (nombre, departamento, activo) VALUES (?, ?, 1)", (nombre, departamento))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        st.error(f"Error: {e}")
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

def obtener_empleados_por_departamento():
    """Obtiene el conteo de empleados por departamento"""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT departamento, COUNT(*) as cantidad 
        FROM empleados 
        WHERE activo = 1 
        GROUP BY departamento 
        ORDER BY departamento
    """, conn)
    conn.close()
    return df

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
    
    if 'menu_visible' not in st.session_state:
        st.session_state.menu_visible = True
    
    if 'config' not in st.session_state:
        st.session_state.config = cargar_config()
    
    if 'usuario_actual' not in st.session_state:
        st.session_state.usuario_actual = "admin"
        actualizar_ultimo_acceso("admin")
    
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = "Empleados"

# Llamar a la función para inicializar
inicializar_estado()

# -------------------- FUNCIONES DE PÁGINAS --------------------
def pagina_empleados():
    st.title("👥 Empleados - Registro Diario de Ventas")
    
    # Crear pestañas
    tab_ventas, tab_admin, tab_departamentos = st.tabs(["📝 Registrar Ventas", "⚙️ Administrar Empleados", "📊 Por Departamento"])
    
    with tab_ventas:
        st.subheader("📝 Registro Diario de Ventas")
        
        col_fecha, col_nombre = st.columns(2)
        
        with col_fecha:
            fecha = st.date_input("📅 Fecha", key="fecha_registro")
        
        with col_nombre:
            if not st.session_state.empleados:
                st.warning("⚠️ No hay empleados registrados")
                empleado = st.selectbox("👤 Nombre", ["Sin empleados"])
            else:
                # Cargar empleados con departamento para mostrar información adicional
                empleados_df = cargar_empleados_con_departamento()
                if not empleados_df.empty:
                    # Crear opciones con nombre y departamento
                    opciones = [f"{row['nombre']} ({row['departamento']})" for _, row in empleados_df.iterrows()]
                    empleado_seleccionado = st.selectbox("👤 Nombre", opciones, key="empleado_select")
                    # Extraer solo el nombre para guardar en BD
                    empleado = empleado_seleccionado.split(" (")[0]
                else:
                    empleado = st.selectbox("👤 Nombre", ["Sin empleados"])
        
        # Campos de ventas en 2 columnas
        col1, col2 = st.columns(2)
        
        with col1:
            autoliquidable = st.number_input("Autoliquidable", min_value=0, step=1, key="auto")
            oferta = st.number_input("Oferta de la semana", min_value=0, step=1, key="ofer")
        
        with col2:
            marca_propia = st.number_input("Marca propia", min_value=0, step=1, key="marca")
            producto = st.number_input("Producto adicional", min_value=0, step=1, key="prod")
        
        # Botón de guardar
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
    
    with tab_admin:
        st.subheader("👥 Administración de Empleados")
        
        col_agregar, col_lista = st.columns([1, 1])
        
        with col_agregar:
            st.markdown("**➕ Agregar Nuevo Empleado**")
            
            # Formulario para agregar empleado
            with st.form("form_agregar_empleado"):
                nuevo_empleado = st.text_input("Nombre completo del empleado")
                departamento = st.selectbox(
                    "Departamento",
                    ["Droguería", "Equipos Médicos", "Tienda", "Cajas"],
                    key="depto_nuevo"
                )
                
                submitted = st.form_submit_button("Agregar empleado", use_container_width=True)
                
                if submitted:
                    if nuevo_empleado:
                        # Llamar a la función con ambos parámetros
                        if guardar_empleado_db(nuevo_empleado, departamento):
                            st.success(f"✅ Empleado '{nuevo_empleado}' agregado al departamento {departamento}")
                            # Actualizar la lista de empleados en el estado
                            st.session_state.empleados = cargar_empleados_db()
                            st.rerun()
                        else:
                            st.error("❌ El empleado ya existe o hubo un error")
                    else:
                        st.error("❌ Por favor ingresa un nombre")
        
        with col_lista:
            st.markdown("**📋 Lista de Empleados Activos**")
            
            # Cargar empleados con departamento
            empleados_df = cargar_empleados_con_departamento()
            
            if not empleados_df.empty:
                # Mostrar empleados en una tabla
                for i, row in empleados_df.iterrows():
                    col_emp, col_depto, col_btn = st.columns([3, 2, 1])
                    with col_emp:
                        st.write(f"• {row['nombre']}")
                    with col_depto:
                        # Asignar color según departamento
                        color = {
                            "Droguería": "🔵",
                            "Equipos Médicos": "🟢",
                            "Tienda": "🟠",
                            "Cajas": "🟣"
                        }.get(row['departamento'], "⚪")
                        st.write(f"{color} {row['departamento']}")
                    with col_btn:
                        if st.button("🗑️", key=f"eliminar_{i}", help=f"Eliminar a {row['nombre']}"):
                            eliminar_empleado_db(row['nombre'])
                            st.success(f"✅ Empleado '{row['nombre']}' eliminado")
                            # Actualizar la lista de empleados
                            st.session_state.empleados = cargar_empleados_db()
                            st.rerun()
            else:
                st.info("📭 No hay empleados registrados")
        
        # Mostrar estadísticas
        st.markdown("---")
        st.subheader("📊 Estadísticas de Empleados")
        
        col_total, col_activos = st.columns(2)
        
        with col_total:
            conn = get_connection()
            df_total = pd.read_sql("SELECT COUNT(*) as total FROM empleados", conn)
            total_empleados = df_total['total'].iloc[0] if not df_total.empty else 0
            conn.close()
            st.metric("Total empleados (histórico)", total_empleados)
        
        with col_activos:
            st.metric("Empleados activos", len(st.session_state.empleados))
    
    with tab_departamentos:
        st.subheader("📊 Empleados por Departamento")
        
        # Mostrar distribución por departamento
        deptos_df = obtener_empleados_por_departamento()
        
        if not deptos_df.empty:
            # Gráfico de barras con Plotly
            import plotly.express as px
            fig = px.bar(
                deptos_df, 
                x='departamento', 
                y='cantidad',
                title="Cantidad de Empleados por Departamento",
                color='departamento',
                color_discrete_map={
                    "Droguería": "#1f77b4",
                    "Equipos Médicos": "#2ca02c",
                    "Tienda": "#ff7f0e",
                    "Cajas": "#9467bd"
                }
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar tabla detallada
            st.subheader("📋 Detalle por Departamento")
            
            # Crear columnas para cada departamento
            cols = st.columns(4)
            departamentos = ["Droguería", "Equipos Médicos", "Tienda", "Cajas"]
            colores = {"Droguería": "#1f77b4", "Equipos Médicos": "#2ca02c", 
                      "Tienda": "#ff7f0e", "Cajas": "#9467bd"}
            
            for idx, depto in enumerate(departamentos):
                with cols[idx]:
                    cantidad = deptos_df[deptos_df['departamento'] == depto]['cantidad'].values
                    cantidad = cantidad[0] if len(cantidad) > 0 else 0
                    
                    st.markdown(f"""
                    <div style="
                        background-color: {colores[depto]}20;
                        padding: 15px;
                        border-radius: 10px;
                        border-left: 5px solid {colores[depto]};
                        margin-bottom: 10px;
                    ">
                        <h4 style="margin:0; color: {colores[depto]};">{depto}</h4>
                        <h2 style="margin:5px 0;">{cantidad}</h2>
                        <small>empleados</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Lista de empleados por departamento
            st.subheader("👥 Lista de Empleados por Departamento")
            
            empleados_df = cargar_empleados_con_departamento()
            
            for depto in departamentos:
                with st.expander(f"📌 {depto} ({len(empleados_df[empleados_df['departamento'] == depto])} empleados)"):
                    empleados_depto = empleados_df[empleados_df['departamento'] == depto]
                    if not empleados_depto.empty:
                        for _, row in empleados_depto.iterrows():
                            st.write(f"• {row['nombre']}")
                    else:
                        st.write("No hay empleados en este departamento")
        else:
            st.info("📭 No hay empleados registrados")

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

# -------------------- MENÚ LATERAL --------------------
with st.sidebar:
    # Botón para ocultar/mostrar menú
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 📋 Menú")
    with col2:
        if st.button("🔽" if st.session_state.menu_visible else "▶️", key="toggle_menu"):
            st.session_state.menu_visible = not st.session_state.menu_visible
            st.rerun()
    
    st.markdown("---")
    
    # Mostrar información del usuario en el sidebar
    deptos_df = obtener_empleados_por_departamento()
    deptos_text = ""
    if not deptos_df.empty:
        deptos_text = " • ".join([f"{row['departamento']}: {row['cantidad']}" for _, row in deptos_df.iterrows()])
    
    st.markdown(f"""
    <div style="
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <strong>👤 {st.session_state.usuario_actual}</strong><br>
        <small>{datetime.now().strftime('%H:%M')} - {datetime.now().strftime('%d/%m')}</small><br>
        <small>Total: {len(st.session_state.empleados)} empleados</small><br>
        <small style="font-size: 0.8em;">{deptos_text}</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Menú de navegación (visible u oculto)
    if st.session_state.menu_visible:
        # Definir las opciones del menú
        menu_options = {
            "Empleados": "👥",
            "Dashboard": "📊",
            "Config": "⚙️",
            "Usuarios": "👤",
            "Backup": "💾",
            "Sistema": "🖥️"
        }
        
        # Crear botones para cada opción
        for opcion, icono in menu_options.items():
            # Determinar si es la página actual
            es_activo = st.session_state.pagina_actual == opcion
            
            # Estilo para botón activo
            if es_activo:
                button_type = "primary"
            else:
                button_type = "secondary"
            
            if st.button(
                f"{icono} {opcion}",
                key=f"menu_{opcion}",
                use_container_width=True,
                type=button_type
            ):
                st.session_state.pagina_actual = opcion
                st.rerun()
        
        st.markdown("---")
        st.caption("© 2024 Locatel Restrepo")
    else:
        # Mostrar solo íconos cuando el menú está oculto
        st.markdown("### ")
        cols = st.columns(1)
        with cols[0]:
            # Versión mini con solo íconos
            menu_icons = {
                "Empleados": "👥",
                "Dashboard": "📊", 
                "Config": "⚙️",
                "Usuarios": "👤",
                "Backup": "💾",
                "Sistema": "🖥️"
            }
            
            for opcion, icono in menu_icons.items():
                if st.button(icono, key=f"mini_{opcion}", help=opcion):
                    st.session_state.pagina_actual = opcion
                    st.rerun()

# -------------------- CONTENIDO PRINCIPAL --------------------
# Mostrar el título de la página actual
st.markdown(f"# {st.session_state.pagina_actual}")

# Navegación
if st.session_state.pagina_actual == "Empleados":
    pagina_empleados()
elif st.session_state.pagina_actual == "Dashboard":
    pagina_dashboard()
elif st.session_state.pagina_actual == "Config":
    pagina_config()
elif st.session_state.pagina_actual == "Usuarios":
    pagina_usuarios()
elif st.session_state.pagina_actual == "Backup":
    pagina_backup()
elif st.session_state.pagina_actual == "Sistema":
    pagina_sistema()