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
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "poll"
    os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

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
        pass
    
    # Tabla de usuarios
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            rol TEXT,
            empleado_id INTEGER,
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_acceso TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def actualizar_esquema_bd():
    """Actualiza el esquema de la base de datos si es necesario"""
    conn = get_connection()
    c = conn.cursor()
    
    # Verificar columnas en usuarios
    c.execute("PRAGMA table_info(usuarios)")
    columnas = [col[1] for col in c.fetchall()]
    
    if 'empleado_id' not in columnas:
        c.execute("ALTER TABLE usuarios ADD COLUMN empleado_id INTEGER")
    
    if 'activo' not in columnas:
        c.execute("ALTER TABLE usuarios ADD COLUMN activo INTEGER DEFAULT 1")
    
    conn.commit()
    conn.close()

def insertar_datos_iniciales():
    """Inserta datos iniciales en la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    
    # Insertar empleados por defecto
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
        c.execute("INSERT OR IGNORE INTO usuarios (username, password, rol, activo) VALUES (?, ?, ?, ?)",
                  ("admin", "admin123", "Administrador", 1))
    except:
        pass
    
    # Insertar usuario supervisor
    try:
        c.execute("INSERT OR IGNORE INTO usuarios (username, password, rol, activo) VALUES (?, ?, ?, ?)",
                  ("supervisor", "super123", "Supervisor", 1))
    except:
        pass
    
    conn.commit()
    conn.close()

# Crear tablas y datos iniciales
create_tables()
actualizar_esquema_bd()
insertar_datos_iniciales()

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
    df = pd.read_sql("SELECT id, nombre, departamento FROM empleados WHERE activo = 1 ORDER BY nombre", conn)
    conn.close()
    return df

def guardar_empleado_db(nombre, departamento):
    """Guarda un nuevo empleado en la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT activo FROM empleados WHERE nombre = ?", (nombre,))
        resultado = c.fetchone()
        
        if resultado:
            if resultado[0] == 0:
                c.execute("UPDATE empleados SET activo = 1, departamento = ? WHERE nombre = ?", (departamento, nombre))
                conn.commit()
                return True
            else:
                return False
        else:
            c.execute("INSERT INTO empleados (nombre, departamento, activo) VALUES (?, ?, 1)", (nombre, departamento))
            conn.commit()
            return True
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

# -------------------- FUNCIONES DE AUTENTICACIÓN Y USUARIOS --------------------
# -------------------- FUNCIONES DE AUTENTICACIÓN Y USUARIOS --------------------
def autenticar_usuario(username, password):
    """Verifica las credenciales del usuario"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT username, rol, empleado_id, activo 
        FROM usuarios 
        WHERE username = ? AND password = ? AND activo = 1
    """, (username, password))
    usuario = c.fetchone()
    conn.close()
    
    if usuario:
        return {
            'username': usuario[0],
            'rol': usuario[1],
            'empleado_id': usuario[2],
            'activo': usuario[3]
        }
    return None

def cargar_usuarios_db():
    """Carga los usuarios desde la base de datos"""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT u.username, u.rol, u.activo, u.ultimo_acceso, e.nombre as empleado
        FROM usuarios u
        LEFT JOIN empleados e ON u.empleado_id = e.id
        ORDER BY u.username
    """, conn)
    conn.close()
    return df

def crear_usuario_db(username, password, rol):
    """Crea un nuevo usuario en la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (username, password, rol, activo) VALUES (?, ?, ?, 1)",
                  (username, password, rol))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def crear_usuario_empleado(username, password, empleado_nombre):
    """Crea un usuario asociado a un empleado existente"""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute("SELECT id FROM empleados WHERE nombre = ? AND activo = 1", (empleado_nombre,))
        empleado = c.fetchone()
        
        if not empleado:
            return False, "El empleado no existe"
        
        c.execute("SELECT id FROM usuarios WHERE empleado_id = ?", (empleado[0],))
        if c.fetchone():
            return False, "El empleado ya tiene un usuario asignado"
        
        c.execute("""
            INSERT INTO usuarios (username, password, rol, empleado_id, activo) 
            VALUES (?, ?, ?, ?, 1)
        """, (username, password, 'Vendedor', empleado[0]))
        
        conn.commit()
        return True, "Usuario creado exitosamente"
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe"
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()

def obtener_empleados_sin_usuario():
    """Obtiene lista de empleados que no tienen usuario asignado"""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT e.nombre 
        FROM empleados e 
        WHERE e.activo = 1 
        AND e.id NOT IN (
            SELECT u.empleado_id 
            FROM usuarios u 
            WHERE u.empleado_id IS NOT NULL AND u.activo = 1
        )
        ORDER BY e.nombre
    """, conn)
    conn.close()
    return df['nombre'].tolist() if not df.empty else []

def actualizar_ultimo_acceso(username):
    """Actualiza la fecha de último acceso del usuario"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET ultimo_acceso = ? WHERE username = ?",
              (datetime.now(), username))
    conn.commit()
    conn.close()

def toggle_usuario_activo(username, activo):
    """Activa o desactiva un usuario"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET activo = ? WHERE username = ?", (activo, username))
    conn.commit()
    conn.close()

# ========== NUEVA FUNCIÓN: AGREGAR AQUÍ ==========
def eliminar_usuario_db(username):
    """Elimina permanentemente un usuario de la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM usuarios WHERE username = ?", (username,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al eliminar usuario: {e}")
        return False
    finally:
        conn.close()
# ========== FIN DE LA NUEVA FUNCIÓN ==========

def cerrar_sesion():
    """Cierra la sesión del usuario actual"""
    for key in ['usuario_actual', 'usuario_rol', 'usuario_empleado_id', 'autenticado']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.pagina_actual = "Login"
    st.rerun()

def verificar_permiso(rol_requerido):
    """Verifica si el usuario tiene el rol requerido"""
    if 'usuario_rol' not in st.session_state:
        return False
    
    if rol_requerido == "Vendedor":
        return st.session_state.usuario_rol in ["Vendedor", "Supervisor", "Administrador"]
    elif rol_requerido == "Supervisor":
        return st.session_state.usuario_rol in ["Supervisor", "Administrador"]
    elif rol_requerido == "Administrador":
        return st.session_state.usuario_rol == "Administrador"
    return False

# -------------------- INICIALIZAR ESTADO DE LA SESIÓN --------------------
def inicializar_estado():
    """Inicializa todas las variables de sesión"""
    if 'empleados' not in st.session_state:
        st.session_state.empleados = cargar_empleados_db()
    
    if 'menu_visible' not in st.session_state:
        st.session_state.menu_visible = True
    
    if 'config' not in st.session_state:
        st.session_state.config = cargar_config()
    
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = "Login"
    
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

# Llamar a la función para inicializar
inicializar_estado()

# -------------------- PÁGINA DE LOGIN --------------------
def pagina_login():
    """Página de inicio de sesión"""
    
    st.markdown("""
    <style>
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }
    .login-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        width: 100%;
        max-width: 400px;
        color: white;
    }
    .login-title {
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTextInput > div > div > input {
        background-color: rgba(255,255,255,0.9);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-box">
            <h2 class="login-title">🏥 Equipo Locatel Restrepo</h2>
            <h3 class="login-title">Sistema de Ventas</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
            password = st.text_input("🔑 Contraseña", type="password", placeholder="Ingresa tu contraseña")
            
            submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submitted:
                if username and password:
                    usuario = autenticar_usuario(username, password)
                    
                    if usuario:
                        st.session_state.usuario_actual = usuario['username']
                        st.session_state.usuario_rol = usuario['rol']
                        st.session_state.usuario_empleado_id = usuario['empleado_id']
                        st.session_state.autenticado = True
                        
                        actualizar_ultimo_acceso(username)
                        
                        if usuario['rol'] == 'Vendedor':
                            st.session_state.pagina_actual = "Registro Ventas"
                        else:
                            st.session_state.pagina_actual = "Empleados"
                        
                        st.success("✅ Login exitoso")
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
                else:
                    st.error("❌ Por favor ingresa usuario y contraseña")
        
        with st.expander("ℹ️ Credenciales de prueba"):
            st.markdown("""
            **Administrador:** admin / admin123<br>
            **Supervisor:** supervisor / super123
            """, unsafe_allow_html=True)

# -------------------- PÁGINA PARA VENDEDORES --------------------
def pagina_registro_ventas():
    """Página simplificada para que los vendedores registren sus ventas"""
    
    st.title("📝 Registro de Ventas - Locatel Restrepo")
    
    # Información del vendedor
    if st.session_state.usuario_empleado_id:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT nombre, departamento 
            FROM empleados 
            WHERE id = ? AND activo = 1
        """, conn, params=(st.session_state.usuario_empleado_id,))
        conn.close()
        
        if not df.empty:
            empleado = df.iloc[0]
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
                padding: 1.5rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                border-left: 5px solid #667eea;
            ">
                <h2 style="margin:0; color: #667eea;">👤 {empleado['nombre']}</h2>
                <p style="margin:5px 0 0 0; color: #666; font-size: 1.1em;">{empleado['departamento']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            empleado_nombre = empleado['nombre']
        else:
            st.error("❌ No se encontró información del empleado")
            return
    else:
        st.error("❌ Usuario no asociado a un empleado")
        return
    
    # Formulario de registro
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("form_registro_ventas"):
            st.subheader("📋 Registrar Ventas del Día")
            
            fecha = st.date_input("📅 Fecha", value=datetime.now())
            
            col_auto, col_ofer = st.columns(2)
            with col_auto:
                autoliquidable = st.number_input("💊 Autoliquidable", min_value=0, step=1, value=0)
            with col_ofer:
                oferta = st.number_input("🏷️ Oferta semana", min_value=0, step=1, value=0)
            
            col_marca, col_prod = st.columns(2)
            with col_marca:
                marca_propia = st.number_input("⭐ Marca propia", min_value=0, step=1, value=0)
            with col_prod:
                producto_adicional = st.number_input("➕ Producto adicional", min_value=0, step=1, value=0)
            
            submitted = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
            
            if submitted:
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    INSERT INTO registros_ventas
                    (fecha, empleado, autoliquidable, oferta, marca_propia, producto_adicional)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (fecha, empleado_nombre, autoliquidable, oferta, marca_propia, producto_adicional))
                conn.commit()
                conn.close()
                
                st.success("✅ ¡Ventas registradas exitosamente!")
                st.balloons()
                st.rerun()
    
    with col2:
        # Mostrar registros del día
        st.subheader("📊 Registros de Hoy")
        
        hoy = datetime.now().date()
        conn = get_connection()
        df_hoy = pd.read_sql("""
            SELECT autoliquidable, oferta, marca_propia, producto_adicional, fecha_registro
            FROM registros_ventas 
            WHERE empleado = ? AND fecha = ?
            ORDER BY fecha_registro DESC
        """, conn, params=(empleado_nombre, hoy))
        conn.close()
        
        if not df_hoy.empty:
            total_auto = df_hoy['autoliquidable'].sum()
            total_ofer = df_hoy['oferta'].sum()
            total_marca = df_hoy['marca_propia'].sum()
            total_prod = df_hoy['producto_adicional'].sum()
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.metric("Autoliquidable", int(total_auto))
                st.metric("Marca Propia", int(total_marca))
            with col_t2:
                st.metric("Oferta", int(total_ofer))
                st.metric("Producto Adic.", int(total_prod))
            
            with st.expander("Ver detalles"):
                st.dataframe(df_hoy, use_container_width=True)
        else:
            st.info("📭 No has registrado ventas hoy")
    
    # Registros recientes
    st.markdown("---")
    st.subheader("📈 Mis Últimos Registros")
    
    conn = get_connection()
    df_recientes = pd.read_sql("""
        SELECT fecha, autoliquidable, oferta, marca_propia, producto_adicional, 
               (autoliquidable + oferta + marca_propia + producto_adicional) as total
        FROM registros_ventas 
        WHERE empleado = ? 
        ORDER BY fecha DESC, fecha_registro DESC 
        LIMIT 10
    """, conn, params=(empleado_nombre,))
    conn.close()
    
    if not df_recientes.empty:
        st.dataframe(df_recientes, use_container_width=True, hide_index=True)
    else:
        st.info("📭 No tienes registros anteriores")

# -------------------- PÁGINAS EXISTENTES (modificadas con permisos) --------------------
def pagina_empleados():
    if not verificar_permiso("Supervisor"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("👥 Administración de Empleados")
    
    tab_ventas, tab_admin, tab_departamentos = st.tabs(["📝 Registrar Ventas", "⚙️ Admin Empleados", "📊 Por Departamento"])
    
    with tab_ventas:
        st.subheader("📝 Registro Diario de Ventas")
        
        col_fecha, col_nombre = st.columns(2)
        
        with col_fecha:
            fecha = st.date_input("📅 Fecha", key="fecha_registro_admin")
        
        with col_nombre:
            empleados_df = cargar_empleados_con_departamento()
            if not empleados_df.empty:
                opciones = [f"{row['nombre']} ({row['departamento']})" for _, row in empleados_df.iterrows()]
                empleado_seleccionado = st.selectbox("👤 Empleado", opciones, key="empleado_select_admin")
                empleado = empleado_seleccionado.split(" (")[0]
            else:
                empleado = st.selectbox("👤 Empleado", ["Sin empleados"])
        
        col1, col2 = st.columns(2)
        with col1:
            autoliquidable = st.number_input("Autoliquidable", min_value=0, step=1, key="auto_admin")
            oferta = st.number_input("Oferta de la semana", min_value=0, step=1, key="ofer_admin")
        with col2:
            marca_propia = st.number_input("Marca propia", min_value=0, step=1, key="marca_admin")
            producto = st.number_input("Producto adicional", min_value=0, step=1, key="prod_admin")
        
        if st.button("💾 Guardar registro", use_container_width=True):
            if empleados_df is not None and not empleados_df.empty:
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
            with st.form("form_agregar_empleado"):
                nuevo_empleado = st.text_input("Nombre completo del empleado")
                departamento = st.selectbox("Departamento", ["Droguería", "Equipos Médicos", "Tienda", "Cajas"])
                submitted = st.form_submit_button("Agregar empleado", use_container_width=True)
                
                if submitted and nuevo_empleado:
                    if guardar_empleado_db(nuevo_empleado, departamento):
                        st.success(f"✅ Empleado '{nuevo_empleado}' agregado")
                        st.session_state.empleados = cargar_empleados_db()
                        st.rerun()
                    else:
                        st.error("❌ El empleado ya existe")
        
        with col_lista:
            st.markdown("**📋 Empleados Activos**")
            empleados_df = cargar_empleados_con_departamento()
            
            if not empleados_df.empty:
                for i, row in empleados_df.iterrows():
                    col_emp, col_depto, col_btn = st.columns([3, 2, 1])
                    with col_emp:
                        st.write(f"• {row['nombre']}")
                    with col_depto:
                        color = {"Droguería": "🔵", "Equipos Médicos": "🟢", "Tienda": "🟠", "Cajas": "🟣"}.get(row['departamento'], "⚪")
                        st.write(f"{color} {row['departamento']}")
                    with col_btn:
                        if st.button("🗑️", key=f"eliminar_{i}"):
                            eliminar_empleado_db(row['nombre'])
                            st.success(f"✅ Empleado eliminado")
                            st.session_state.empleados = cargar_empleados_db()
                            st.rerun()
            else:
                st.info("📭 No hay empleados")
    
    with tab_departamentos:
        st.subheader("📊 Empleados por Departamento")
        deptos_df = obtener_empleados_por_departamento()
        
        if not deptos_df.empty:
            import plotly.express as px
            fig = px.bar(deptos_df, x='departamento', y='cantidad', 
                        title="Cantidad de Empleados por Departamento",
                        color='departamento')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def pagina_dashboard():
    if not verificar_permiso("Supervisor"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("📊 Dashboard de Ventas")
    
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM registros_ventas ORDER BY fecha DESC", conn)
    conn.close()
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Autoliquidable", int(df["autoliquidable"].sum()))
        col2.metric("Oferta", int(df["oferta"].sum()))
        col3.metric("Marca Propia", int(df["marca_propia"].sum()))
        col4.metric("Producto Adicional", int(df["producto_adicional"].sum()))
        
        st.subheader("📊 Ventas por Empleado")
        ventas_empleado = df.groupby("empleado")[["autoliquidable","oferta","marca_propia","producto_adicional"]].sum()
        st.bar_chart(ventas_empleado)
        
        st.subheader("📅 Ventas por Fecha")
        ventas_fecha = df.groupby("fecha")[["autoliquidable","oferta","marca_propia","producto_adicional"]].sum()
        st.line_chart(ventas_fecha)
        
        st.subheader("📋 Ventas Recientes")
        st.dataframe(df.head(20), use_container_width=True)
    else:
        st.info("📭 Aún no hay datos registrados")

def pagina_config():
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("⚙️ Configuración")
    
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
        st.session_state.config.update({
            "tema": tema,
            "idioma": idioma,
            "productos_seleccionados": productos_seleccionados
        })
        guardar_config(st.session_state.config)
        st.success("✅ Configuración guardada")

def pagina_usuarios():
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("👤 Administración de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["👥 Gestión de Usuarios", "➕ Usuario desde Empleado", "👑 Crear Admin/Supervisor"])
    
    with tab1:
        usuarios_df = cargar_usuarios_db()
        if not usuarios_df.empty:
            # Estilos personalizados para las tarjetas
            st.markdown("""
            <style>
            .user-card {
                background: white;
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-left: 5px solid;
                transition: transform 0.2s;
            }
            .user-card:hover {
                transform: translateX(5px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            .admin-card { border-left-color: #ff4444; }
            .supervisor-card { border-left-color: #ffaa00; }
            .vendedor-card { border-left-color: #00aa00; }
            </style>
            """, unsafe_allow_html=True)
            
            # Métricas rápidas
            col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
            with col_metric1:
                st.metric("Total Usuarios", len(usuarios_df))
            with col_metric2:
                st.metric("Administradores", len(usuarios_df[usuarios_df['rol'] == 'Administrador']))
            with col_metric3:
                st.metric("Supervisores", len(usuarios_df[usuarios_df['rol'] == 'Supervisor']))
            with col_metric4:
                st.metric("Vendedores", len(usuarios_df[usuarios_df['rol'] == 'Vendedor']))
            
            st.markdown("---")
            
            # Mostrar usuarios en tarjetas
            for idx, row in usuarios_df.iterrows():
                # Determinar clase CSS según rol
                rol_class = {
                    'Administrador': 'admin-card',
                    'Supervisor': 'supervisor-card',
                    'Vendedor': 'vendedor-card'
                }.get(row['rol'], '')
                
                # Color del rol para texto
                color_rol = {
                    'Administrador': '#ff4444',
                    'Supervisor': '#ffaa00',
                    'Vendedor': '#00aa00'
                }.get(row['rol'], '#666')
                
                # Estado badge
                estado_badge = "🟢 Activo" if row['activo'] else "🔴 Inactivo"
                
                with st.container():
                    st.markdown(f"""
                    <div class="user-card {rol_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="
                                    width: 40px;
                                    height: 40px;
                                    background: {color_rol}20;
                                    border-radius: 50%;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    color: {color_rol};
                                    font-size: 20px;
                                ">
                                    👤
                                </div>
                                <div>
                                    <strong style="font-size: 1.1em;">{row['username']}</strong><br>
                                    <span style="color: #666; font-size: 0.9em;">
                                        {row['empleado'] if row['empleado'] else 'Sin empleado asociado'}
                                    </span>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <span style="
                                    background: {color_rol}20;
                                    color: {color_rol};
                                    padding: 4px 12px;
                                    border-radius: 15px;
                                    font-size: 0.9em;
                                    font-weight: bold;
                                ">
                                    {row['rol']}
                                </span>
                                <div style="margin-top: 5px;">
                                    <span style="color: #666; font-size: 0.85em;">
                                        📅 {row['ultimo_acceso'][:10] if row['ultimo_acceso'] else 'Nunca'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botones de acción debajo de la tarjeta
                    if row['username'] != 'admin':  # No permitir eliminar al admin principal
                        col_acc1, col_acc2, col_acc3, col_acc4 = st.columns([1, 1, 1, 5])
                        with col_acc1:
                            # Botón de activar/desactivar con estilo
                            if row['activo']:
                                if st.button("🔌 Desactivar", key=f"deactivate_{row['username']}", 
                                           help="Desactivar usuario"):
                                    toggle_usuario_activo(row['username'], 0)
                                    st.rerun()
                            else:
                                if st.button("🔓 Activar", key=f"activate_{row['username']}",
                                           help="Activar usuario"):
                                    toggle_usuario_activo(row['username'], 1)
                                    st.rerun()
                        
                        with col_acc2:
                            # Botón de eliminar
                            if st.button("🗑️ Eliminar", key=f"delete_{row['username']}",
                                       help="Eliminar permanentemente"):
                                st.session_state[f"confirm_delete_{row['username']}"] = True
                                st.rerun()
                        
                        # Confirmación de eliminación
                        if f"confirm_delete_{row['username']}" in st.session_state:
                            st.warning(f"⚠️ ¿Eliminar usuario '{row['username']}' permanentemente?")
                            with col_acc3:
                                if st.button("✅ Sí", key=f"confirm_yes_{row['username']}"):
                                    if eliminar_usuario_db(row['username']):
                                        st.success(f"✅ Usuario eliminado")
                                        del st.session_state[f"confirm_delete_{row['username']}"]
                                        st.rerun()
                                if st.button("❌ No", key=f"confirm_no_{row['username']}"):
                                    del st.session_state[f"confirm_delete_{row['username']}"]
                                    st.rerun()
                    
                    st.markdown("<br>", unsafe_allow_html=True)
            
        else:
            st.info("📭 No hay usuarios registrados")
    
    with tab2:
        empleados_sin_usuario = obtener_empleados_sin_usuario()
        
        if empleados_sin_usuario:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            ">
                <h3 style="margin:0; color: #667eea;">📋 Crear Usuario para Empleado</h3>
                <p style="color: #666; margin-top: 5px;">
                    Convierte a un empleado en usuario del sistema con rol de Vendedor
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("form_usuario_empleado"):
                col1, col2 = st.columns(2)
                
                with col1:
                    empleado = st.selectbox(
                        "👤 Seleccionar empleado",
                        empleados_sin_usuario,
                        help="Selecciona el empleado que tendrá acceso al sistema"
                    )
                    username = st.text_input(
                        "🔑 Usuario",
                        placeholder="Ej: jperez",
                        help="Nombre de usuario para iniciar sesión"
                    )
                
                with col2:
                    password = st.text_input(
                        "🔒 Contraseña",
                        type="password",
                        placeholder="********",
                        help="Contraseña segura para el usuario"
                    )
                    
                    # Generador de contraseña simple
                    import random
                    import string
                    if st.form_submit_button("🎲 Generar contraseña", type="secondary"):
                        chars = string.ascii_letters + string.digits + "!@#$%"
                        suggested = ''.join(random.choice(chars) for _ in range(10))
                        st.session_state['suggested_password'] = suggested
                
                if st.form_submit_button("🚀 Crear usuario vendedor", use_container_width=True):
                    if username and password:
                        exito, mensaje = crear_usuario_empleado(username, password, empleado)
                        if exito:
                            st.success(f"✅ {mensaje}")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ {mensaje}")
                    else:
                        st.error("❌ Todos los campos son obligatorios")
                
                if 'suggested_password' in st.session_state:
                    st.info(f"🔑 Contraseña sugerida: `{st.session_state['suggested_password']}`")
        else:
            st.success("""
            <div style="
                background: #00aa0020;
                padding: 40px;
                border-radius: 10px;
                text-align: center;
                border: 2px dashed #00aa00;
            ">
                <h2 style="color: #00aa00;">✅ ¡Todos los empleados tienen usuario!</h2>
                <p style="color: #666;">No hay empleados pendientes de asignación</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #ff444420 0%, #ffaa0020 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        ">
            <h3 style="margin:0; color: #ff4444;">👑 Crear Usuario Administrativo</h3>
            <p style="color: #666; margin-top: 5px;">
                Crea usuarios con permisos de Administrador o Supervisor
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_admin"):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input(
                    "👤 Usuario",
                    placeholder="Ej: admin2",
                    help="Nombre de usuario único"
                )
                password = st.text_input(
                    "🔒 Contraseña",
                    type="password",
                    placeholder="********",
                    help="Mínimo 8 caracteres"
                )
            
            with col2:
                rol = st.selectbox(
                    "🎯 Rol",
                    ["Administrador", "Supervisor"],
                    help="Selecciona el nivel de permisos"
                )
                
                # Verificador de fortaleza de contraseña
                if password and len(password) >= 8:
                    st.success("✅ Contraseña fuerte")
                elif password:
                    st.warning("⚠️ Mínimo 8 caracteres")
            
            submitted = st.form_submit_button("✨ Crear usuario administrativo", use_container_width=True)
            
            if submitted:
                if username and password:
                    if len(password) >= 8:
                        if crear_usuario_db(username, password, rol):
                            st.success(f"✅ Usuario {username} creado exitosamente")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ El usuario ya existe")
                    else:
                        st.error("❌ La contraseña debe tener al menos 8 caracteres")
                else:
                    st.error("❌ Todos los campos son obligatorios")

def pagina_backup():
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("💾 Backup y Restauración")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📀 Crear backup")
        if st.button("Crear backup ahora", use_container_width=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_backup = f"backup_ventas_{timestamp}.db"
            
            import shutil
            shutil.copy2("ventas.db", nombre_backup)
            
            if os.path.exists("config.json"):
                shutil.copy2("config.json", f"backup_config_{timestamp}.json")
            
            st.success(f"✅ Backup creado: {nombre_backup}")
            
            with open(nombre_backup, "rb") as f:
                st.download_button("📥 Descargar backup", f, nombre_backup)
    
    with col2:
        st.subheader("🔄 Restaurar backup")
        archivo_backup = st.file_uploader("Seleccionar archivo de backup", type=['db'])
        if archivo_backup:
            if st.button("Restaurar", use_container_width=True):
                with open("ventas.db", "wb") as f:
                    f.write(archivo_backup.getbuffer())
                st.success("✅ Base de datos restaurada")
                st.rerun()

def pagina_sistema():
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("🖥️ Información del Sistema")
    
    conn = get_connection()
    total_ventas = pd.read_sql("SELECT COUNT(*) as total FROM registros_ventas", conn)['total'].iloc[0]
    total_empleados = pd.read_sql("SELECT COUNT(*) as total FROM empleados WHERE activo = 1", conn)['total'].iloc[0]
    total_usuarios = pd.read_sql("SELECT COUNT(*) as total FROM usuarios", conn)['total'].iloc[0]
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Versión", "2.0.0")
        st.metric("Base de datos", "SQLite")
        st.metric("Registros ventas", total_ventas)
    
    with col2:
        st.metric("Empleados activos", total_empleados)
        st.metric("Usuarios", total_usuarios)
        st.metric("Usuario actual", st.session_state.usuario_actual)
    
    with col3:
        st.metric("Rol", st.session_state.usuario_rol)
        st.metric("Espacio DB", f"{os.path.getsize('ventas.db')/1024:.1f} KB")
        st.metric("Estado", "✅ Online")

# -------------------- MENÚ LATERAL --------------------
with st.sidebar:
    if 'autenticado' not in st.session_state or not st.session_state.autenticado:
        st.markdown("### 🔐 Sistema de Ventas")
        st.markdown("---")
        st.caption("© 2024 Locatel Restrepo")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 📋 Menú")
        with col2:
            if st.button("🔽" if st.session_state.menu_visible else "▶️", key="toggle_menu"):
                st.session_state.menu_visible = not st.session_state.menu_visible
                st.rerun()
        
        st.markdown("---")
        
        # Información del usuario
        color_rol = {
            "Administrador": "#ff4444",
            "Supervisor": "#ffaa00", 
            "Vendedor": "#00aa00"
        }.get(st.session_state.usuario_rol, "#666")
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color_rol}20 0%, {color_rol}10 100%);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid {color_rol};
        ">
            <strong style="color: {color_rol};">👤 {st.session_state.usuario_actual}</strong><br>
            <span style="color: {color_rol};">{st.session_state.usuario_rol}</span><br>
            <small>{datetime.now().strftime('%H:%M')} - {datetime.now().strftime('%d/%m/%Y')}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Menú según rol
        if st.session_state.menu_visible:
            if st.session_state.usuario_rol == "Vendedor":
                menu_options = {"Registro Ventas": "📝"}
            elif st.session_state.usuario_rol == "Supervisor":
                menu_options = {"Registro Ventas": "📝", "Dashboard": "📊", "Empleados": "👥"}
            else:
                menu_options = {"Empleados": "👥", "Dashboard": "📊", "Config": "⚙️", 
                               "Usuarios": "👤", "Backup": "💾", "Sistema": "🖥️"}
            
            for opcion, icono in menu_options.items():
                es_activo = st.session_state.pagina_actual == opcion
                if st.button(f"{icono} {opcion}", key=f"menu_{opcion}", 
                           use_container_width=True, type="primary" if es_activo else "secondary"):
                    st.session_state.pagina_actual = opcion
                    st.rerun()
            
            st.markdown("---")
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                cerrar_sesion()
            st.caption("© 2024 Locatel Restrepo")
        else:
            menu_icons = {"Registro Ventas": "📝", "Dashboard": "📊", "Empleados": "👥", 
                         "Config": "⚙️", "Usuarios": "👤", "Backup": "💾", "Sistema": "🖥️"}
            for opcion, icono in menu_icons.items():
                if st.button(icono, key=f"mini_{opcion}", help=opcion):
                    st.session_state.pagina_actual = opcion
                    st.rerun()
            if st.button("🚪", key="mini_logout", help="Cerrar sesión"):
                cerrar_sesion()

# -------------------- NAVEGACIÓN PRINCIPAL --------------------
if 'autenticado' not in st.session_state or not st.session_state.autenticado:
    pagina_login()
else:
    if st.session_state.pagina_actual == "Login":
        pagina_login()
    elif st.session_state.pagina_actual == "Registro Ventas":
        pagina_registro_ventas()
    elif st.session_state.pagina_actual == "Empleados":
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