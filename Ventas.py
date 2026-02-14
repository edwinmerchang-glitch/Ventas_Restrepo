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
    """Página modernizada para que los vendedores registren sus ventas"""
    
    # Estilos CSS personalizados
    st.markdown("""
    <style>
    /* Tarjeta de bienvenida */
    .welcome-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    .welcome-card::before {
        content: '🏥';
        position: absolute;
        right: 20px;
        bottom: 20px;
        font-size: 5rem;
        opacity: 0.2;
        transform: rotate(-10deg);
    }
    .welcome-card h1 {
        font-size: 2.5rem;
        margin: 0;
        font-weight: 700;
    }
    .welcome-card p {
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Tarjetas de métricas */
    .metric-card-modern {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #f0f0f0;
        transition: transform 0.3s ease;
    }
    .metric-card-modern:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .metric-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .metric-value-modern {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label-modern {
        color: #666;
        font-size: 0.9rem;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Tarjeta de formulario */
    .form-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
    }
    .form-title {
        color: #333;
        font-size: 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .form-title::before {
        content: '📋';
        font-size: 2rem;
    }
    
    /* Inputs modernos */
    .modern-input {
        border: 2px solid #f0f0f0;
        border-radius: 12px;
        padding: 0.8rem;
        font-size: 1rem;
        transition: all 0.3s;
    }
    .modern-input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        outline: none;
    }
    
    /* Botón moderno */
    .modern-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2rem;
        font-size: 1.2rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .modern-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    .modern-button:active {
        transform: translateY(0);
    }
    
    /* Tarjeta de registro */
    .history-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border-left: 5px solid;
        transition: all 0.3s;
    }
    .history-card:hover {
        transform: translateX(5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .history-date {
        color: #667eea;
        font-weight: 600;
        font-size: 1.1rem;
    }
    .history-values {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 0.5rem;
    }
    .history-tag {
        background: #f8f9fa;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        color: #666;
    }
    .history-tag strong {
        color: #333;
        margin-right: 5px;
    }
    
    /* Animaciones */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .animate-in {
        animation: slideIn 0.5s ease forwards;
    }
    
    /* Estilo para los inputs de número */
    div[data-testid="stNumberInput"] label {
        font-weight: 600;
        color: #333;
        font-size: 1rem;
    }
    div[data-testid="stNumberInput"] input {
        border: 2px solid #f0f0f0;
        border-radius: 12px;
        padding: 0.8rem;
        font-size: 1.1rem;
    }
    div[data-testid="stNumberInput"] input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
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
            empleado_nombre = empleado['nombre']
            departamento = empleado['departamento']
            
            # Emoji según departamento
            depto_emoji = {
                "Droguería": "💊",
                "Equipos Médicos": "🏥",
                "Tienda": "🏪",
                "Cajas": "💰"
            }.get(departamento, "👤")
            
            # Tarjeta de bienvenida
            st.markdown(f"""
            <div class="welcome-card animate-in">
                <h1>¡Hola, {empleado_nombre}! 👋</h1>
                <p>{depto_emoji} {departamento} • {datetime.now().strftime('%A, %d de %B de %Y')}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("❌ No se encontró información del empleado")
            return
    else:
        st.error("❌ Usuario no asociado a un empleado")
        return
    
    # Layout principal con columnas
    col_registro, col_resumen = st.columns([1.2, 0.8])
    
    with col_registro:
        with st.container():
            st.markdown('<div class="form-card animate-in">', unsafe_allow_html=True)
            
            # Título del formulario
            st.markdown("""
            <div class="form-title">
                Registrar Ventas del Día
            </div>
            """, unsafe_allow_html=True)
            
            # Fecha con estilo
            col_fecha_icon, col_fecha_picker = st.columns([0.1, 0.9])
            with col_fecha_icon:
                st.markdown("### 📅")
            with col_fecha_picker:
                fecha = st.date_input(
                    "Fecha",
                    value=datetime.now(),
                    label_visibility="collapsed"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Grid de productos
            col1, col2 = st.columns(2)
            
            with col1:
                # Tarjeta Autoliquidable
                st.markdown("""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 15px; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.5rem;">💊</span>
                        <span style="font-weight: 600; color: #333;">Autoliquidable</span>
                    </div>
                """, unsafe_allow_html=True)
                autoliquidable = st.number_input(
                    "Autoliquidable",
                    min_value=0,
                    step=1,
                    value=0,
                    label_visibility="collapsed",
                    key="auto_input"
                )
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Tarjeta Marca Propia
                st.markdown("""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 15px; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.5rem;">⭐</span>
                        <span style="font-weight: 600; color: #333;">Marca Propia</span>
                    </div>
                """, unsafe_allow_html=True)
                marca_propia = st.number_input(
                    "Marca Propia",
                    min_value=0,
                    step=1,
                    value=0,
                    label_visibility="collapsed",
                    key="marca_input"
                )
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                # Tarjeta Oferta
                st.markdown("""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 15px; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.5rem;">🏷️</span>
                        <span style="font-weight: 600; color: #333;">Oferta Semana</span>
                    </div>
                """, unsafe_allow_html=True)
                oferta = st.number_input(
                    "Oferta Semana",
                    min_value=0,
                    step=1,
                    value=0,
                    label_visibility="collapsed",
                    key="oferta_input"
                )
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Tarjeta Producto Adicional
                st.markdown("""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 15px; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.5rem;">➕</span>
                        <span style="font-weight: 600; color: #333;">Producto Adicional</span>
                    </div>
                """, unsafe_allow_html=True)
                producto_adicional = st.number_input(
                    "Producto Adicional",
                    min_value=0,
                    step=1,
                    value=0,
                    label_visibility="collapsed",
                    key="prod_input"
                )
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Total del registro
            total_registro = autoliquidable + oferta + marca_propia + producto_adicional
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
                padding: 1rem;
                border-radius: 12px;
                margin: 1rem 0;
                text-align: center;
            ">
                <span style="color: #666; font-size: 1rem;">Total de unidades hoy</span>
                <h2 style="color: #667eea; margin: 0; font-size: 2.5rem;">{total_registro}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón de guardar moderno
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                if st.button("💾 GUARDAR REGISTRO", key="btn_guardar", use_container_width=True):
                    if total_registro > 0:
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
                    else:
                        st.warning("⚠️ Debes registrar al menos una venta")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col_resumen:
        # Resumen del día
        st.markdown("""
        <div class="form-card animate-in" style="margin-bottom: 1rem;">
            <div class="form-title" style="font-size: 1.2rem;">
                📊 Resumen de Hoy
            </div>
        """, unsafe_allow_html=True)
        
        hoy = datetime.now().date()
        conn = get_connection()
        df_hoy = pd.read_sql("""
            SELECT autoliquidable, oferta, marca_propia, producto_adicional
            FROM registros_ventas 
            WHERE empleado = ? AND fecha = ?
        """, conn, params=(empleado_nombre, hoy))
        conn.close()
        
        if not df_hoy.empty:
            total_auto = df_hoy['autoliquidable'].sum()
            total_ofer = df_hoy['oferta'].sum()
            total_marca = df_hoy['marca_propia'].sum()
            total_prod = df_hoy['producto_adicional'].sum()
            total_general = total_auto + total_ofer + total_marca + total_prod
            
            # Métricas en tarjetas modernas
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.markdown(f"""
                <div class="metric-card-modern">
                    <div class="metric-icon">💊</div>
                    <p class="metric-value-modern">{int(total_auto)}</p>
                    <p class="metric-label-modern">Autoliquidable</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card-modern">
                    <div class="metric-icon">⭐</div>
                    <p class="metric-value-modern">{int(total_marca)}</p>
                    <p class="metric-label-modern">Marca Propia</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m2:
                st.markdown(f"""
                <div class="metric-card-modern">
                    <div class="metric-icon">🏷️</div>
                    <p class="metric-value-modern">{int(total_ofer)}</p>
                    <p class="metric-label-modern">Oferta</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card-modern">
                    <div class="metric-icon">➕</div>
                    <p class="metric-value-modern">{int(total_prod)}</p>
                    <p class="metric-label-modern">Adicional</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Total general
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #00aa0020 0%, #00cc0020 100%);
                padding: 1rem;
                border-radius: 12px;
                margin-top: 1rem;
                text-align: center;
            ">
                <span style="color: #00aa00; font-size: 1rem;">TOTAL DEL DÍA</span>
                <h2 style="color: #00aa00; margin: 0; font-size: 2rem;">{int(total_general)}</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("""
            <div style="text-align: center; padding: 2rem;">
                <span style="font-size: 3rem;">📭</span>
                <p style="color: #666;">No hay registros hoy</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Últimos registros
        st.markdown("""
        <div class="form-card animate-in">
            <div class="form-title" style="font-size: 1.2rem;">
                📋 Últimos Registros
            </div>
        """, unsafe_allow_html=True)
        
        conn = get_connection()
        df_recientes = pd.read_sql("""
            SELECT fecha, autoliquidable, oferta, marca_propia, producto_adicional,
                   (autoliquidable + oferta + marca_propia + producto_adicional) as total
            FROM registros_ventas 
            WHERE empleado = ? 
            ORDER BY fecha DESC, fecha_registro DESC 
            LIMIT 5
        """, conn, params=(empleado_nombre,))
        conn.close()
        
        if not df_recientes.empty:
            for _, row in df_recientes.iterrows():
                fecha_str = datetime.strptime(row['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
                st.markdown(f"""
                <div class="history-card" style="border-left-color: #667eea;">
                    <div class="history-date">{fecha_str}</div>
                    <div class="history-values">
                        <span class="history-tag"><strong>💊</strong> {int(row['autoliquidable'])}</span>
                        <span class="history-tag"><strong>🏷️</strong> {int(row['oferta'])}</span>
                        <span class="history-tag"><strong>⭐</strong> {int(row['marca_propia'])}</span>
                        <span class="history-tag"><strong>➕</strong> {int(row['producto_adicional'])}</span>
                        <span class="history-tag"><strong>📊</strong> {int(row['total'])}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <p style="color: #999;">No hay registros anteriores</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

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
    
    # Estilos CSS personalizados
    st.markdown("""
    <style>
    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-card .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0;
    }
    
    /* Tarjetas de usuario */
    .user-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1rem;
        padding: 1rem 0;
    }
    .user-card-modern {
        background: white;
        border-radius: 15px;
        padding: 1.2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .user-card-modern:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
    }
    .user-card-modern::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
    }
    .user-card-modern.admin::before { background: linear-gradient(90deg, #ff4444, #ff8888); }
    .user-card-modern.supervisor::before { background: linear-gradient(90deg, #ffaa00, #ffcc00); }
    .user-card-modern.vendedor::before { background: linear-gradient(90deg, #00aa00, #44cc44); }
    
    /* Avatar */
    .user-avatar {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        margin-right: 1rem;
    }
    .avatar-admin { background: linear-gradient(135deg, #ff444420, #ff888820); color: #ff4444; }
    .avatar-supervisor { background: linear-gradient(135deg, #ffaa0020, #ffcc0020); color: #ffaa00; }
    .avatar-vendedor { background: linear-gradient(135deg, #00aa0020, #44cc4420); color: #00aa00; }
    
    /* Badges */
    .role-badge {
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-block;
    }
    .badge-admin { background: #ff444420; color: #ff4444; }
    .badge-supervisor { background: #ffaa0020; color: #ffaa00; }
    .badge-vendedor { background: #00aa0020; color: #00aa00; }
    
    .status-badge {
        padding: 0.2rem 0.8rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .status-active { background: #00aa0020; color: #00aa00; }
    .status-inactive { background: #ff444420; color: #ff4444; }
    
    /* Botones de acción */
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
        justify-content: flex-end;
    }
    .action-btn {
        border: none;
        background: none;
        padding: 0.5rem;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 1rem;
    }
    .action-btn:hover {
        background: #f0f0f0;
        transform: scale(1.1);
    }
    .action-btn.delete:hover { color: #ff4444; }
    .action-btn.deactivate:hover { color: #ffaa00; }
    .action-btn.activate:hover { color: #00aa00; }
    </style>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs([
        "📊 Dashboard Usuarios",
        "👥 Gestión de Usuarios",
        "➕ Usuario desde Empleado",
        "👑 Crear Admin/Supervisor"
    ])
    
    with tabs[0]:  # Dashboard
        col1, col2, col3, col4 = st.columns(4)
        
        usuarios_df = cargar_usuarios_db()
        if not usuarios_df.empty:
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <p class="metric-value">{len(usuarios_df)}</p>
                    <p class="metric-label">Total Usuarios</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                admin_count = len(usuarios_df[usuarios_df['rol'] == 'Administrador'])
                st.markdown(f"""
                <div class="metric-card" style="background: linear-gradient(135deg, #ff4444 0%, #ff8888 100%);">
                    <p class="metric-value">{admin_count}</p>
                    <p class="metric-label">Administradores</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                sup_count = len(usuarios_df[usuarios_df['rol'] == 'Supervisor'])
                st.markdown(f"""
                <div class="metric-card" style="background: linear-gradient(135deg, #ffaa00 0%, #ffcc00 100%);">
                    <p class="metric-value">{sup_count}</p>
                    <p class="metric-label">Supervisores</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                ven_count = len(usuarios_df[usuarios_df['rol'] == 'Vendedor'])
                st.markdown(f"""
                <div class="metric-card" style="background: linear-gradient(135deg, #00aa00 0%, #44cc44 100%);">
                    <p class="metric-value">{ven_count}</p>
                    <p class="metric-label">Vendedores</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Gráfico de distribución
            st.markdown("### 📊 Distribución por Rol")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                import plotly.express as px
                roles_df = usuarios_df['rol'].value_counts().reset_index()
                roles_df.columns = ['Rol', 'Cantidad']
                
                colors = {'Administrador': '#ff4444', 'Supervisor': '#ffaa00', 'Vendedor': '#00aa00'}
                fig = px.pie(roles_df, values='Cantidad', names='Rol', 
                           color='Rol', color_discrete_map=colors,
                           title="Distribución de Roles")
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col_chart2:
                # Activos vs Inactivos
                status_df = usuarios_df['activo'].value_counts().reset_index()
                status_df.columns = ['Estado', 'Cantidad']
                status_df['Estado'] = status_df['Estado'].map({1: 'Activos', 0: 'Inactivos'})
                
                fig2 = px.bar(status_df, x='Estado', y='Cantidad', 
                            color='Estado', 
                            color_discrete_map={'Activos': '#00aa00', 'Inactivos': '#ff4444'},
                            title="Estado de Usuarios")
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
    
    with tabs[1]:  # Gestión de Usuarios
        usuarios_df = cargar_usuarios_db()
        
        if not usuarios_df.empty:
            # Filtros
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                rol_filter = st.multiselect(
                    "Filtrar por Rol",
                    options=['Administrador', 'Supervisor', 'Vendedor'],
                    default=[]
                )
            with col_filter2:
                status_filter = st.multiselect(
                    "Filtrar por Estado",
                    options=['Activo', 'Inactivo'],
                    default=[]
                )
            with col_filter3:
                search = st.text_input("🔍 Buscar usuario", placeholder="Nombre de usuario...")
            
            # Aplicar filtros
            filtered_df = usuarios_df.copy()
            if rol_filter:
                filtered_df = filtered_df[filtered_df['rol'].isin(rol_filter)]
            if status_filter:
                status_map = {'Activo': 1, 'Inactivo': 0}
                filtered_df = filtered_df[filtered_df['activo'].isin([status_map[s] for s in status_filter])]
            if search:
                filtered_df = filtered_df[filtered_df['username'].str.contains(search, case=False)]
            
            # Mostrar usuarios en grid
            st.markdown(f"### 👥 Usuarios Encontrados ({len(filtered_df)})")
            
            # Crear grid de usuarios
            cols = st.columns(2)
            for idx, (_, row) in enumerate(filtered_df.iterrows()):
                with cols[idx % 2]:
                    # Determinar clase según rol
                    rol_class = row['rol'].lower()
                    avatar_class = f"avatar-{rol_class}"
                    
                    # Color del rol
                    colors = {
                        'Administrador': '#ff4444',
                        'Supervisor': '#ffaa00',
                        'Vendedor': '#00aa00'
                    }
                    color = colors.get(row['rol'], '#666')
                    
                    # Estado
                    estado = "Activo" if row['activo'] else "Inactivo"
                    estado_class = "status-active" if row['activo'] else "status-inactive"
                    
                    # Avatar (inicial del usuario)
                    avatar_letter = row['username'][0].upper() if row['username'] else '?'
                    
                    st.markdown(f"""
                    <div class="user-card-modern {rol_class}">
                        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                            <div class="user-avatar {avatar_class}">
                                {avatar_letter}
                            </div>
                            <div style="flex-grow: 1;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h3 style="margin: 0; font-size: 1.2rem;">{row['username']}</h3>
                                    <span class="role-badge badge-{rol_class}">{row['rol']}</span>
                                </div>
                                <p style="margin: 0.2rem 0 0 0; color: #666; font-size: 0.9rem;">
                                    {row['empleado'] if row['empleado'] else 'Sin empleado asociado'}
                                </p>
                            </div>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                            <div>
                                <span class="status-badge {estado_class}">{estado}</span>
                                <span style="color: #999; font-size: 0.8rem; margin-left: 0.5rem;">
                                    📅 {row['ultimo_acceso'][:10] if row['ultimo_acceso'] else 'Nunca'}
                                </span>
                            </div>
                            
                            <div class="action-buttons">
                    """, unsafe_allow_html=True)
                    
                    if row['username'] != 'admin':
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                        
                        with col_btn1:
                            if row['activo']:
                                if st.button("🔌", key=f"deact_{row['username']}", help="Desactivar usuario"):
                                    toggle_usuario_activo(row['username'], 0)
                                    st.rerun()
                            else:
                                if st.button("🔓", key=f"act_{row['username']}", help="Activar usuario"):
                                    toggle_usuario_activo(row['username'], 1)
                                    st.rerun()
                        
                        with col_btn2:
                            if st.button("🗑️", key=f"del_{row['username']}", help="Eliminar usuario"):
                                st.session_state[f"confirm_del_{row['username']}"] = True
                                st.rerun()
                        
                        with col_btn3:
                            if f"confirm_del_{row['username']}" in st.session_state:
                                st.markdown("""
                                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                                            background: white; padding: 2rem; border-radius: 15px;
                                            box-shadow: 0 10px 40px rgba(0,0,0,0.2); z-index: 1000;">
                                    <h4>¿Confirmar eliminación?</h4>
                                    <p style="color: #666;">Esta acción no se puede deshacer</p>
                                    <div style="display: flex; gap: 1rem; justify-content: center;">
                                """, unsafe_allow_html=True)
                                
                                if st.button("✅ Sí", key=f"conf_yes_{row['username']}"):
                                    if eliminar_usuario_db(row['username']):
                                        del st.session_state[f"confirm_del_{row['username']}"]
                                        st.rerun()
                                if st.button("❌ No", key=f"conf_no_{row['username']}"):
                                    del st.session_state[f"confirm_del_{row['username']}"]
                                    st.rerun()
                                
                                st.markdown("</div></div>", unsafe_allow_html=True)
                    
                    st.markdown("</div></div></div>", unsafe_allow_html=True)
        else:
            st.info("📭 No hay usuarios registrados")
    
    with tabs[2]:  # Usuario desde Empleado
        empleados_sin_usuario = obtener_empleados_sin_usuario()
        
        if empleados_sin_usuario:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                color: white;
                text-align: center;
            ">
                <h2 style="margin: 0; font-size: 2rem;">📋 Convertir Empleado en Usuario</h2>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
                    Asigna acceso al sistema a un empleado con rol de Vendedor
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col_form1, col_form2 = st.columns([1, 1])
            
            with col_form1:
                with st.form("form_usuario_empleado_modern"):
                    st.markdown("#### 📝 Datos del Usuario")
                    
                    empleado = st.selectbox(
                        "👤 Seleccionar Empleado",
                        empleados_sin_usuario,
                        help="Empleado que tendrá acceso al sistema"
                    )
                    
                    username = st.text_input(
                        "🔑 Nombre de Usuario",
                        placeholder="ej: jperez",
                        help="Nombre único para iniciar sesión"
                    )
                    
                    col_pass1, col_pass2 = st.columns([3, 1])
                    with col_pass1:
                        password = st.text_input(
                            "🔒 Contraseña",
                            type="password",
                            placeholder="********",
                            help="Mínimo 8 caracteres"
                        )
                    
                    with col_pass2:
                        import random
                        import string
                        if st.form_submit_button("🎲 Generar", help="Generar contraseña aleatoria"):
                            chars = string.ascii_letters + string.digits + "!@#$%"
                            suggested = ''.join(random.choice(chars) for _ in range(10))
                            st.session_state['suggested_pass'] = suggested
                    
                    if 'suggested_pass' in st.session_state:
                        st.info(f"🔑 Contraseña sugerida: `{st.session_state['suggested_pass']}`")
                    
                    st.markdown("---")
                    submitted = st.form_submit_button("🚀 Crear Usuario Vendedor", use_container_width=True)
                    
                    if submitted:
                        if username and password:
                            if len(password) >= 8:
                                exito, mensaje = crear_usuario_empleado(username, password, empleado)
                                if exito:
                                    st.success(f"✅ {mensaje}")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(f"❌ {mensaje}")
                            else:
                                st.error("❌ La contraseña debe tener al menos 8 caracteres")
                        else:
                            st.error("❌ Todos los campos son obligatorios")
            
            with col_form2:
                st.markdown("#### 📋 Empleados Disponibles")
                for emp in empleados_sin_usuario[:5]:  # Mostrar solo los primeros 5
                    st.markdown(f"""
                    <div style="
                        background: #f8f9fa;
                        padding: 0.8rem;
                        border-radius: 10px;
                        margin: 0.5rem 0;
                        border-left: 5px solid #667eea;
                    ">
                        <strong>{emp}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                
                if len(empleados_sin_usuario) > 5:
                    st.info(f"... y {len(empleados_sin_usuario) - 5} empleados más")
        else:
            st.success("""
            <div style="
                background: #00aa0020;
                padding: 4rem;
                border-radius: 20px;
                text-align: center;
                border: 3px dashed #00aa00;
                margin: 2rem 0;
            ">
                <h1 style="color: #00aa00; font-size: 3rem;">✅</h1>
                <h2 style="color: #00aa00;">¡Todos los empleados tienen usuario!</h2>
                <p style="color: #666;">No hay empleados pendientes de asignación</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[3]:  # Crear Admin/Supervisor
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #ff4444 0%, #ffaa00 100%);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        ">
            <h2 style="margin: 0; font-size: 2rem;">👑 Crear Usuario Administrativo</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
                Crea usuarios con permisos de Administrador o Supervisor
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col_admin1, col_admin2 = st.columns([1, 1])
        
        with col_admin1:
            with st.form("form_admin_modern"):
                st.markdown("#### 📝 Datos del Usuario")
                
                username = st.text_input(
                    "👤 Usuario",
                    placeholder="ej: admin2",
                    help="Nombre de usuario único"
                )
                
                password = st.text_input(
                    "🔒 Contraseña",
                    type="password",
                    placeholder="********",
                    help="Mínimo 8 caracteres"
                )
                
                # Medidor de fortaleza de contraseña
                if password:
                    strength = 0
                    if len(password) >= 8:
                        strength += 25
                    if any(c.isupper() for c in password):
                        strength += 25
                    if any(c.islower() for c in password):
                        strength += 25
                    if any(c in "!@#$%^&*" for c in password):
                        strength += 25
                    
                    st.progress(strength/100, text=f"Fortaleza: {strength}%")
                
                rol = st.selectbox(
                    "🎯 Rol",
                    ["Administrador", "Supervisor"],
                    help="Nivel de permisos del usuario"
                )
                
                st.markdown("---")
                submitted = st.form_submit_button("✨ Crear Usuario", use_container_width=True)
                
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
        
        with col_admin2:
            st.markdown("#### ℹ️ Información de Roles")
            
            st.markdown("""
            <div style="
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 15px;
            ">
                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #ff4444; margin: 0;">👑 Administrador</h4>
                    <p style="color: #666; margin: 0.5rem 0;">Acceso completo al sistema:</p>
                    <ul style="color: #666;">
                        <li>✓ Gestión de usuarios</li>
                        <li>✓ Configuración del sistema</li>
                        <li>✓ Backup y restauración</li>
                        <li>✓ Todos los módulos</li>
                    </ul>
                </div>
                
                <div>
                    <h4 style="color: #ffaa00; margin: 0;">👁️ Supervisor</h4>
                    <p style="color: #666; margin: 0.5rem 0;">Acceso de supervisión:</p>
                    <ul style="color: #666;">
                        <li>✓ Dashboard de ventas</li>
                        <li>✓ Gestión de empleados</li>
                        <li>✓ Ver registros de ventas</li>
                        <li>✓ Reportes</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

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