import streamlit as st
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime
import hashlib
import hmac
import logging
from functools import wraps
import plotly.express as px
import plotly.graph_objects as go
import random
import string
import gzip
import shutil
from pathlib import Path
# Al inicio de Ventas.py, después de los imports
#import sys
#st.write("Python version:", sys.version)
#st.write("Current directory:", os.getcwd())
#st.write("Files in directory:", os.listdir())

# -------------------- CONFIGURACIÓN INICIAL --------------------
st.set_page_config(
    page_title="Equipo Locatel Restrepo", 
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- CONFIGURACIÓN DE LOGGING --------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- FUNCIONES DE SEGURIDAD --------------------
def hash_password(password):
    """Hashea la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    """Verifica la contraseña de manera segura"""
    return hmac.compare_digest(hash_password(password), hashed)

# -------------------- DECORADOR PARA MANEJO DE ERRORES --------------------
def safe_db_operation(func):
    """Decorador para operaciones seguras de base de datos"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Error de base de datos: {e}")
            st.error(f"❌ Error de base de datos: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            st.error(f"❌ Error inesperado: {str(e)}")
            return None
    return wrapper

# -------------------- VERIFICACIÓN DE ENTORNO --------------------
def check_environment():
    """Verifica el entorno de ejecución"""
    issues = []
    
    # Verificar permisos de escritura
    try:
        test_file = 'test_write.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info("✅ Permisos de escritura OK")
    except Exception as e:
        issues.append(f"Sin permisos de escritura: {e}")
        logger.error(f"Error de permisos: {e}")
    
    return issues

# -------------------- INICIALIZACIÓN DE BASE DE DATOS --------------------
@st.cache_resource
def init_database():
    """Inicializa la base de datos con manejo de errores"""
    db_path = "ventas.db"
    
    # Verificar si la base de datos existe y no está corrupta
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        logger.info("✅ Base de datos verificada correctamente")
    except Exception as e:
        logger.error(f"Error con base de datos: {e}")
        # Si está corrupta, crear backup y nueva base
        if os.path.exists(db_path):
            backup_name = f"ventas_corrupta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            os.rename(db_path, backup_name)
            logger.info(f"Backup de BD corrupta creado: {backup_name}")
    
    return get_connection()

# -------------------- FUNCIONES DE BASE DE DATOS --------------------
def get_connection():
    """Obtiene conexión a la base de datos"""
    # Quita check_same_thread=False
    return sqlite3.connect("ventas.db", timeout=30)

@safe_db_operation
def create_tables():
    """Crea las tablas con mejor manejo de errores"""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Tabla de ventas
        c.execute("""
            CREATE TABLE IF NOT EXISTS registros_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE,
                empleado TEXT,
                autoliquidable INTEGER DEFAULT 0,
                oferta INTEGER DEFAULT 0,
                marca_propia INTEGER DEFAULT 0,
                producto_adicional INTEGER DEFAULT 0,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de empleados
        c.execute("""
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                activo INTEGER DEFAULT 1,
                departamento TEXT DEFAULT 'Droguería',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de usuarios con contraseñas hasheadas
        c.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                rol TEXT,
                empleado_id INTEGER,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP,
                FOREIGN KEY (empleado_id) REFERENCES empleados (id)
            )
        """)
        
        conn.commit()
        logger.info("✅ Tablas creadas/verificadas correctamente")
        
        # Insertar datos iniciales
        insertar_datos_iniciales(conn)
        
    except sqlite3.Error as e:
        logger.error(f"Error creando tablas: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
    
    return True

@safe_db_operation
def insertar_datos_iniciales(conn):
    """Inserta datos iniciales con manejo de errores"""
    c = conn.cursor()
    
    # Empleados por defecto
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
            c.execute(
                "INSERT OR IGNORE INTO empleados (nombre, departamento) VALUES (?, ?)", 
                (emp, depto)
            )
        except Exception as e:
            logger.warning(f"Error insertando empleado {emp}: {e}")
    
    # Usuario admin con contraseña hasheada
    admin_hash = hash_password("admin123")
    try:
        c.execute(
            "INSERT OR IGNORE INTO usuarios (username, password_hash, rol, activo) VALUES (?, ?, ?, ?)",
            ("admin", admin_hash, "Administrador", 1)
        )
    except Exception as e:
        logger.warning(f"Error insertando admin: {e}")
    
    # Usuario supervisor con contraseña hasheada
    sup_hash = hash_password("super123")
    try:
        c.execute(
            "INSERT OR IGNORE INTO usuarios (username, password_hash, rol, activo) VALUES (?, ?, ?, ?)",
            ("supervisor", sup_hash, "Supervisor", 1)
        )
    except Exception as e:
        logger.warning(f"Error insertando supervisor: {e}")
    
    conn.commit()
    logger.info("✅ Datos iniciales insertados")

# -------------------- FUNCIONES DE AUTENTICACIÓN --------------------
@safe_db_operation
def autenticar_usuario(username, password):
    """Verifica las credenciales usando hash"""
    conn = get_connection()
    c = conn.cursor()
    
    password_hash = hash_password(password)
    
    c.execute("""
        SELECT username, rol, empleado_id, activo 
        FROM usuarios 
        WHERE username = ? AND password_hash = ? AND activo = 1
    """, (username, password_hash))
    
    usuario = c.fetchone()
    conn.close()
    
    if usuario:
        logger.info(f"✅ Usuario autenticado: {username}")
        return {
            'username': usuario[0],
            'rol': usuario[1],
            'empleado_id': usuario[2],
            'activo': usuario[3]
        }
    
    logger.warning(f"❌ Intento fallido de login: {username}")
    return None

@safe_db_operation
def crear_usuario_db(username, password, rol):
    """Crea usuario con contraseña hasheada"""
    conn = get_connection()
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute(
            "INSERT INTO usuarios (username, password_hash, rol, activo) VALUES (?, ?, ?, 1)",
            (username, password_hash, rol)
        )
        conn.commit()
        logger.info(f"✅ Usuario creado: {username}")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"⚠️ Usuario ya existe: {username}")
        return False
    finally:
        conn.close()

@safe_db_operation
def actualizar_ultimo_acceso(username):
    """Actualiza la fecha de último acceso"""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE usuarios SET ultimo_acceso = ? WHERE username = ?",
        (datetime.now(), username)
    )
    conn.commit()
    conn.close()

# -------------------- FUNCIONES DE EMPLEADOS --------------------
@safe_db_operation
@st.cache_data(ttl=300)  # Cache por 5 minutos
def cargar_empleados_db():
    """Carga los nombres de empleados desde la base de datos"""
    conn = get_connection()
    df = pd.read_sql("SELECT nombre FROM empleados WHERE activo = 1 ORDER BY nombre", conn)
    conn.close()
    return df['nombre'].tolist() if not df.empty else []

@safe_db_operation
def cargar_empleados_con_departamento():
    """Carga los empleados con su departamento"""
    conn = get_connection()
    df = pd.read_sql("SELECT id, nombre, departamento FROM empleados WHERE activo = 1 ORDER BY nombre", conn)
    conn.close()
    return df

@safe_db_operation
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
                st.cache_data.clear()
                return True
            else:
                return False
        else:
            c.execute("INSERT INTO empleados (nombre, departamento, activo) VALUES (?, ?, 1)", (nombre, departamento))
            conn.commit()
            st.cache_data.clear()
            return True
    except Exception as e:
        logger.error(f"Error guardando empleado: {e}")
        return False
    finally:
        conn.close()

@safe_db_operation
def eliminar_empleado_db(nombre):
    """Elimina (desactiva) un empleado de la base de datos"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE empleados SET activo = 0 WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()
    st.cache_data.clear()

@safe_db_operation
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

# -------------------- FUNCIONES DE VENTAS --------------------
@safe_db_operation
@st.cache_data(ttl=60)  # Cache por 1 minuto
def obtener_ventas_recientes(empleado=None, limite=100):
    """Obtiene ventas recientes con caché"""
    conn = get_connection()
    if empleado:
        df = pd.read_sql("""
            SELECT * FROM registros_ventas 
            WHERE empleado = ? 
            ORDER BY fecha DESC, fecha_registro DESC 
            LIMIT ?
        """, conn, params=(empleado, limite))
    else:
        df = pd.read_sql("""
            SELECT * FROM registros_ventas 
            ORDER BY fecha DESC, fecha_registro DESC 
            LIMIT ?
        """, conn, params=(limite,))
    conn.close()
    return df

@safe_db_operation
def guardar_venta(fecha, empleado, autoliquidable, oferta, marca_propia, producto_adicional):
    """Guarda un registro de venta"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO registros_ventas
        (fecha, empleado, autoliquidable, oferta, marca_propia, producto_adicional)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fecha, empleado, autoliquidable, oferta, marca_propia, producto_adicional))
    conn.commit()
    conn.close()
    st.cache_data.clear()

@safe_db_operation
def obtener_resumen_hoy(empleado, fecha):
    """Obtiene resumen de ventas del día"""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT autoliquidable, oferta, marca_propia, producto_adicional
        FROM registros_ventas 
        WHERE empleado = ? AND fecha = ?
    """, conn, params=(empleado, fecha))
    conn.close()
    return df

# -------------------- FUNCIONES DE USUARIOS --------------------
@safe_db_operation
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

@safe_db_operation
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
        
        password_hash = hash_password(password)
        c.execute("""
            INSERT INTO usuarios (username, password_hash, rol, empleado_id, activo) 
            VALUES (?, ?, ?, ?, 1)
        """, (username, password_hash, 'Vendedor', empleado[0]))
        
        conn.commit()
        st.cache_data.clear()
        return True, "Usuario creado exitosamente"
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe"
    except Exception as e:
        logger.error(f"Error creando usuario empleado: {e}")
        return False, f"Error: {e}"
    finally:
        conn.close()

@safe_db_operation
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

@safe_db_operation
def toggle_usuario_activo(username, activo):
    """Activa o desactiva un usuario"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET activo = ? WHERE username = ?", (activo, username))
    conn.commit()
    conn.close()
    st.cache_data.clear()

@safe_db_operation
def eliminar_usuario_db(username):
    """Elimina permanentemente un usuario de la base de datos"""
    if username == "admin":
        return False, "No se puede eliminar el usuario admin"
    
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM usuarios WHERE username = ?", (username,))
        conn.commit()
        st.cache_data.clear()
        return True, "Usuario eliminado"
    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}")
        return False, f"Error: {e}"
    finally:
        conn.close()

# -------------------- FUNCIONES DE CONFIGURACIÓN --------------------
ARCHIVO_CONFIG = "config.json"

def cargar_config():
    """Carga la configuración desde el archivo JSON"""
    try:
        if os.path.exists(ARCHIVO_CONFIG):
            with open(ARCHIVO_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando config: {e}")
    
    return {
        "tema": "Claro",
        "idioma": "Español",
        "productos_adicionales": ["Producto 1", "Producto 2", "Producto 3", "Producto 4"],
        "productos_seleccionados": []
    }

def guardar_config(config):
    """Guarda la configuración en el archivo JSON"""
    try:
        with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error guardando config: {e}")
        return False

# -------------------- FUNCIONES DE BACKUP --------------------
def crear_backup():
    """Crea backup en memoria para descarga"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        if os.path.exists("ventas.db"):
            # Leer el archivo en memoria
            with open("ventas.db", "rb") as f:
                db_content = f.read()
            
            # Comprimir en memoria
            compressed = gzip.compress(db_content)
            
            return compressed, f"backup_ventas_{timestamp}.db.gz"
    except Exception as e:
        logger.error(f"Error creando backup: {e}")
        return None, None
def restaurar_backup(archivo):
    """Restaura un backup"""
    try:
        # Descomprimir si está comprimido
        if archivo.name.endswith('.gz'):
            with gzip.open(archivo, 'rb') as f_in:
                with open("ventas.db", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            with open("ventas.db", 'wb') as f_out:
                f_out.write(archivo.getbuffer())
        
        st.cache_data.clear()
        logger.info("✅ Backup restaurado correctamente")
        return True
    except Exception as e:
        logger.error(f"Error restaurando backup: {e}")
        return False

# -------------------- FUNCIONES DE UTILIDAD --------------------
def obtener_fecha_espanol(fecha):
    """Convierte una fecha a formato español"""
    dias_semana = {
        'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
        'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado',
        'Sunday': 'domingo'
    }
    meses = {
        'January': 'enero', 'February': 'febrero', 'March': 'marzo',
        'April': 'abril', 'May': 'mayo', 'June': 'junio',
        'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
        'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
    }
    
    dia_ingles = fecha.strftime('%A')
    mes_ingles = fecha.strftime('%B')
    
    dia_espanol = dias_semana.get(dia_ingles, dia_ingles).capitalize()
    mes_espanol = meses.get(mes_ingles, mes_ingles)
    
    return f"{dia_espanol}, {fecha.day} de {mes_espanol} de {fecha.year}"

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

def cerrar_sesion():
    """Cierra la sesión del usuario actual"""
    for key in ['usuario_actual', 'usuario_rol', 'usuario_empleado_id', 'autenticado']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.pagina_actual = "Login"
    st.cache_data.clear()
    st.rerun()

def init_session_state():
    """Inicializa el estado de sesión"""
    defaults = {
        'empleados': [],
        'menu_visible': True,
        'config': cargar_config(),
        'pagina_actual': "Login",
        'autenticado': False,
        'usuario_actual': None,
        'usuario_rol': None,
        'usuario_empleado_id': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# -------------------- PÁGINAS DE LA APLICACIÓN --------------------

def pagina_login():
    """Página de inicio de sesión"""
    st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 20px;
    }
    .login-box {
        background: white;
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        width: 100%;
        max-width: 450px;
        animation: slideUp 0.5s ease;
    }
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-header h1 {
        color: #667eea;
        font-size: 2rem;
        margin: 0;
    }
    .login-header p {
        color: #666;
        margin: 0.5rem 0 0 0;
    }
    .login-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="login-header">
        <div class="login-icon">🏥</div>
        <h1>Locatel Restrepo</h1>
        <p>Sistema de Gestión de Ventas</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input(
            "👤 Usuario",
            placeholder="Ingresa tu usuario",
            help="Usuario proporcionado por el administrador"
        )
        
        password = st.text_input(
            "🔑 Contraseña",
            type="password",
            placeholder="Ingresa tu contraseña",
            help="Contraseña segura"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "Iniciar Sesión",
                use_container_width=True,
                type="primary"
            )
        
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
                        st.session_state.pagina_actual = "Dashboard"
                    
                    st.success("✅ ¡Bienvenido!")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor ingresa todos los campos")
    
    with st.expander("ℹ️ Credenciales de prueba"):
        st.markdown("""
        **Administrador:** admin / admin123  
        **Supervisor:** supervisor / super123  
        **Vendedor:** (crear desde gestión de usuarios)
        """)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

def pagina_registro_ventas():
    """Página para registro de ventas"""
    if not verificar_permiso("Vendedor"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    # Obtener información del empleado
    if st.session_state.usuario_empleado_id:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT nombre, departamento 
            FROM empleados 
            WHERE id = ? AND activo = 1
        """, conn, params=(st.session_state.usuario_empleado_id,))
        conn.close()
        
        if df.empty:
            st.error("❌ No se encontró información del empleado")
            return
        
        empleado = df.iloc[0]
        empleado_nombre = empleado['nombre']
        departamento = empleado['departamento']
    else:
        st.error("❌ Usuario no asociado a un empleado")
        return
    
    # CSS personalizado
    st.markdown("""
    <style>
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
    .welcome-card::after {
        content: '🏥';
        position: absolute;
        right: 20px;
        bottom: 20px;
        font-size: 5rem;
        opacity: 0.2;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #f0f0f0;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .form-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        margin-bottom: 1rem;
    }
    .history-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 0.5rem;
        border-left: 4px solid #667eea;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Bienvenida
    fecha_espanol = obtener_fecha_espanol(datetime.now())
    depto_emoji = {
        "Droguería": "💊",
        "Equipos Médicos": "🏥",
        "Tienda": "🏪",
        "Cajas": "💰"
    }.get(departamento, "👤")
    
    st.markdown(f"""
    <div class="welcome-card">
        <h1>¡Hola, {empleado_nombre}! 👋</h1>
        <p>{depto_emoji} {departamento} • {fecha_espanol}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Layout principal
    col_registro, col_resumen = st.columns([1.2, 0.8])
    
    with col_registro:
        with st.container():
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            st.markdown("### 📝 Registrar Ventas del Día")
            
            fecha = st.date_input("📅 Fecha", value=datetime.now())
            
            col1, col2 = st.columns(2)
            
            with col1:
                autoliquidable = st.number_input(
                    "💊 Autoliquidable",
                    min_value=0,
                    step=1,
                    value=0,
                    help="Productos autoliquidables"
                )
                marca_propia = st.number_input(
                    "⭐ Marca Propia",
                    min_value=0,
                    step=1,
                    value=0,
                    help="Productos de marca propia"
                )
            
            with col2:
                oferta = st.number_input(
                    "🏷️ Oferta Semana",
                    min_value=0,
                    step=1,
                    value=0,
                    help="Productos en oferta"
                )
                producto_adicional = st.number_input(
                    "➕ Producto Adicional",
                    min_value=0,
                    step=1,
                    value=0,
                    help="Productos adicionales"
                )
            
            total = autoliquidable + oferta + marca_propia + producto_adicional
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
                padding: 1rem;
                border-radius: 10px;
                margin: 1rem 0;
                text-align: center;
            ">
                <h3 style="color: #667eea; margin: 0;">Total: {total} unidades</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("💾 Guardar Registro", use_container_width=True, type="primary"):
                if total > 0:
                    guardar_venta(
                        fecha, empleado_nombre,
                        autoliquidable, oferta,
                        marca_propia, producto_adicional
                    )
                    st.success("✅ ¡Ventas registradas exitosamente!")
                    st.balloons()
                    st.rerun()
                else:
                    st.warning("⚠️ Debes registrar al menos una venta")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col_resumen:
        # Resumen del día
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Resumen de Hoy")
        
        hoy = datetime.now().date()
        df_hoy = obtener_resumen_hoy(empleado_nombre, hoy)
        
        if not df_hoy.empty:
            total_auto = df_hoy['autoliquidable'].sum()
            total_ofer = df_hoy['oferta'].sum()
            total_marca = df_hoy['marca_propia'].sum()
            total_prod = df_hoy['producto_adicional'].sum()
            total_general = total_auto + total_ofer + total_marca + total_prod
            
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{int(total_auto)}</div>
                    <div class="metric-label">💊 Auto</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{int(total_marca)}</div>
                    <div class="metric-label">⭐ Marca</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{int(total_ofer)}</div>
                    <div class="metric-label">🏷️ Oferta</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{int(total_prod)}</div>
                    <div class="metric-label">➕ Adic</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #00aa0020 0%, #00cc0020 100%);
                padding: 1rem;
                border-radius: 10px;
                margin-top: 1rem;
                text-align: center;
            ">
                <h3 style="color: #00aa00; margin: 0;">Total Día: {int(total_general)}</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("📭 No hay registros hoy")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Últimos registros
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown("### 📋 Últimos Registros")
        
        df_recientes = obtener_ventas_recientes(empleado_nombre, 5)
        
        if not df_recientes.empty:
            for _, row in df_recientes.iterrows():
                fecha_str = datetime.strptime(row['fecha'], '%Y-%m-%d').strftime('%d/%m')
                st.markdown(f"""
                <div class="history-card">
                    <strong>{fecha_str}</strong><br>
                    💊 {int(row['autoliquidable'])} | 🏷️ {int(row['oferta'])} | 
                    ⭐ {int(row['marca_propia'])} | ➕ {int(row['producto_adicional'])}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay registros anteriores")
        
        st.markdown('</div>', unsafe_allow_html=True)

def pagina_dashboard():
    """Dashboard de ventas"""
    if not verificar_permiso("Supervisor"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("📊 Dashboard de Ventas")
    
    # Filtros
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        fecha_inicio = st.date_input("Fecha inicio", value=datetime.now().replace(day=1))
    
    with col_filtro2:
        fecha_fin = st.date_input("Fecha fin", value=datetime.now())
    
    with col_filtro3:
        empleados = cargar_empleados_db()
        empleados.insert(0, "Todos")
        empleado_filtro = st.selectbox("Empleado", empleados)
    
    # Obtener datos
    conn = get_connection()
    if empleado_filtro == "Todos":
        df = pd.read_sql("""
            SELECT * FROM registros_ventas 
            WHERE fecha BETWEEN ? AND ?
            ORDER BY fecha DESC
        """, conn, params=(fecha_inicio, fecha_fin))
    else:
        df = pd.read_sql("""
            SELECT * FROM registros_ventas 
            WHERE fecha BETWEEN ? AND ? AND empleado = ?
            ORDER BY fecha DESC
        """, conn, params=(fecha_inicio, fecha_fin, empleado_filtro))
    conn.close()
    
    if not df.empty:
        # Métricas principales
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Ventas", len(df))
        with col2:
            st.metric("💊 Autoliquidable", int(df['autoliquidable'].sum()))
        with col3:
            st.metric("🏷️ Oferta", int(df['oferta'].sum()))
        with col4:
            st.metric("⭐ Marca Propia", int(df['marca_propia'].sum()))
        with col5:
            st.metric("➕ Adicional", int(df['producto_adicional'].sum()))
        
        # Gráficos
        tab1, tab2, tab3 = st.tabs(["📊 Por Empleado", "📈 Tendencia", "📋 Detalle"])
        
        with tab1:
            ventas_empleado = df.groupby("empleado")[["autoliquidable", "oferta", "marca_propia", "producto_adicional"]].sum().reset_index()
            ventas_empleado['total'] = ventas_empleado[["autoliquidable", "oferta", "marca_propia", "producto_adicional"]].sum(axis=1)
            ventas_empleado = ventas_empleado.sort_values('total', ascending=True)
            
            fig = px.bar(
                ventas_empleado,
                y='empleado',
                x=['autoliquidable', 'oferta', 'marca_propia', 'producto_adicional'],
                title="Ventas por Empleado",
                labels={'value': 'Cantidad', 'empleado': 'Empleado', 'variable': 'Tipo'},
                barmode='stack'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            ventas_fecha = df.groupby("fecha")[["autoliquidable", "oferta", "marca_propia", "producto_adicional"]].sum().reset_index()
            
            fig = px.line(
                ventas_fecha,
                x='fecha',
                y=['autoliquidable', 'oferta', 'marca_propia', 'producto_adicional'],
                title="Tendencia de Ventas",
                labels={'value': 'Cantidad', 'fecha': 'Fecha', 'variable': 'Tipo'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.dataframe(
                df[['fecha', 'empleado', 'autoliquidable', 'oferta', 'marca_propia', 'producto_adicional']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("📭 No hay datos para el período seleccionado")

def pagina_empleados():
    """Administración de empleados"""
    if not verificar_permiso("Supervisor"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("👥 Administración de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["📝 Registrar Ventas", "➕ Agregar Empleado", "📊 Estadísticas"])
    
    with tab1:
        st.subheader("📝 Registro de Ventas para Empleados")
        
        col_fecha, col_emp = st.columns(2)
        
        with col_fecha:
            fecha = st.date_input("📅 Fecha", key="fecha_admin")
        
        with col_emp:
            empleados_df = cargar_empleados_con_departamento()
            if not empleados_df.empty:
                empleado = st.selectbox(
                    "👤 Empleado",
                    empleados_df['nombre'].tolist(),
                    key="emp_admin"
                )
            else:
                st.warning("No hay empleados registrados")
                empleado = None
        
        if empleado:
            col1, col2 = st.columns(2)
            
            with col1:
                autoliquidable = st.number_input("💊 Autoliquidable", min_value=0, step=1, key="auto_admin")
                oferta = st.number_input("🏷️ Oferta", min_value=0, step=1, key="ofer_admin")
            
            with col2:
                marca_propia = st.number_input("⭐ Marca Propia", min_value=0, step=1, key="marca_admin")
                producto = st.number_input("➕ Adicional", min_value=0, step=1, key="prod_admin")
            
            if st.button("💾 Guardar Registro", use_container_width=True, type="primary"):
                if (autoliquidable + oferta + marca_propia + producto) > 0:
                    guardar_venta(fecha, empleado, autoliquidable, oferta, marca_propia, producto)
                    st.success("✅ Registro guardado")
                    st.rerun()
                else:
                    st.warning("⚠️ Debe registrar al menos una venta")
    
    with tab2:
        st.subheader("➕ Agregar Nuevo Empleado")
        
        with st.form("form_empleado"):
            nuevo_empleado = st.text_input("Nombre completo", placeholder="Ej: Juan Pérez")
            departamento = st.selectbox(
                "Departamento",
                ["Droguería", "Equipos Médicos", "Tienda", "Cajas"]
            )
            
            if st.form_submit_button("Agregar Empleado", use_container_width=True):
                if nuevo_empleado:
                    if guardar_empleado_db(nuevo_empleado, departamento):
                        st.success(f"✅ Empleado '{nuevo_empleado}' agregado")
                        st.rerun()
                    else:
                        st.error("❌ El empleado ya existe")
                else:
                    st.warning("⚠️ Ingrese un nombre")
        
        st.markdown("---")
        st.subheader("📋 Empleados Activos")
        
        empleados_df = cargar_empleados_con_departamento()
        if not empleados_df.empty:
            for _, row in empleados_df.iterrows():
                col_emp, col_depto, col_btn = st.columns([3, 2, 1])
                
                with col_emp:
                    st.write(f"• {row['nombre']}")
                
                with col_depto:
                    color = {
                        "Droguería": "🔵",
                        "Equipos Médicos": "🟢",
                        "Tienda": "🟠",
                        "Cajas": "🟣"
                    }.get(row['departamento'], "⚪")
                    st.write(f"{color} {row['departamento']}")
                
                with col_btn:
                    if st.button("🗑️", key=f"del_{row['nombre']}"):
                        eliminar_empleado_db(row['nombre'])
                        st.success(f"✅ Empleado eliminado")
                        st.rerun()
        else:
            st.info("📭 No hay empleados activos")
    
    with tab3:
        st.subheader("📊 Estadísticas por Departamento")
        
        deptos_df = obtener_empleados_por_departamento()
        
        if not deptos_df.empty:
            col_graf, col_tabla = st.columns(2)
            
            with col_graf:
                fig = px.pie(
                    deptos_df,
                    values='cantidad',
                    names='departamento',
                    title="Distribución por Departamento",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col_tabla:
                st.dataframe(
                    deptos_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "departamento": "Departamento",
                        "cantidad": "Cantidad"
                    }
                )
        else:
            st.info("No hay datos de departamentos")

def pagina_usuarios():
    """Administración de usuarios"""
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("👤 Administración de Usuarios")
    
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👥 Gestión", "➕ Crear Usuario"])
    
    with tab1:
        usuarios_df = cargar_usuarios_db()
        
        if not usuarios_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Usuarios", len(usuarios_df))
            with col2:
                admin_count = len(usuarios_df[usuarios_df['rol'] == 'Administrador'])
                st.metric("Administradores", admin_count)
            with col3:
                sup_count = len(usuarios_df[usuarios_df['rol'] == 'Supervisor'])
                st.metric("Supervisores", sup_count)
            with col4:
                ven_count = len(usuarios_df[usuarios_df['rol'] == 'Vendedor'])
                st.metric("Vendedores", ven_count)
            
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                roles_df = usuarios_df['rol'].value_counts().reset_index()
                roles_df.columns = ['Rol', 'Cantidad']
                
                fig = px.pie(
                    roles_df,
                    values='Cantidad',
                    names='Rol',
                    title="Distribución por Rol",
                    color='Rol',
                    color_discrete_map={
                        'Administrador': '#ff4444',
                        'Supervisor': '#ffaa00',
                        'Vendedor': '#00aa00'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col_graf2:
                status_df = usuarios_df['activo'].value_counts().reset_index()
                status_df.columns = ['Estado', 'Cantidad']
                status_df['Estado'] = status_df['Estado'].map({1: 'Activos', 0: 'Inactivos'})
                
                fig = px.bar(
                    status_df,
                    x='Estado',
                    y='Cantidad',
                    title="Estado de Usuarios",
                    color='Estado',
                    color_discrete_map={'Activos': '#00aa00', 'Inactivos': '#ff4444'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        usuarios_df = cargar_usuarios_db()
        
        if not usuarios_df.empty:
            for _, row in usuarios_df.iterrows():
                with st.container():
                    cols = st.columns([2, 1, 1, 1, 1])
                    
                    with cols[0]:
                        st.write(f"**{row['username']}**")
                        if row['empleado']:
                            st.caption(f"👤 {row['empleado']}")
                    
                    with cols[1]:
                        rol_color = {
                            'Administrador': '🔴',
                            'Supervisor': '🟡',
                            'Vendedor': '🟢'
                        }.get(row['rol'], '⚪')
                        st.write(f"{rol_color} {row['rol']}")
                    
                    with cols[2]:
                        estado = "✅ Activo" if row['activo'] else "❌ Inactivo"
                        st.write(estado)
                    
                    with cols[3]:
                        if row['ultimo_acceso']:
                            fecha = row['ultimo_acceso'][:10]
                            st.write(f"📅 {fecha}")
                        else:
                            st.write("📅 Nunca")
                    
                    with cols[4]:
                        if row['username'] != 'admin':
                            if row['activo']:
                                if st.button("🔌", key=f"deact_{row['username']}", help="Desactivar"):
                                    toggle_usuario_activo(row['username'], 0)
                                    st.rerun()
                            else:
                                if st.button("🔓", key=f"act_{row['username']}", help="Activar"):
                                    toggle_usuario_activo(row['username'], 1)
                                    st.rerun()
                            
                            if st.button("🗑️", key=f"del_{row['username']}", help="Eliminar"):
                                exito, msg = eliminar_usuario_db(row['username'])
                                if exito:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    
                    st.divider()
        else:
            st.info("No hay usuarios registrados")
    
    with tab3:
        opcion = st.radio(
            "Tipo de usuario",
            ["Vendedor (desde empleado)", "Administrador/Supervisor"],
            horizontal=True
        )
        
        if opcion == "Vendedor (desde empleado)":
            empleados_sin_usuario = obtener_empleados_sin_usuario()
            
            if empleados_sin_usuario:
                with st.form("form_vendedor"):
                    empleado = st.selectbox("Seleccionar Empleado", empleados_sin_usuario)
                    username = st.text_input("Nombre de Usuario", placeholder="ej: jperez")
                    
                    col_pass1, col_pass2 = st.columns([3, 1])
                    with col_pass1:
                        password = st.text_input("Contraseña", type="password")
                    with col_pass2:
                        if st.form_submit_button("🎲 Generar"):
                            sugerida = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                            st.session_state['sugerida'] = sugerida
                    
                    if 'sugerida' in st.session_state:
                        st.info(f"Contraseña sugerida: `{st.session_state['sugerida']}`")
                    
                    if st.form_submit_button("Crear Usuario", use_container_width=True):
                        if username and password:
                            if len(password) >= 6:
                                exito, msg = crear_usuario_empleado(username, password, empleado)
                                if exito:
                                    st.success(msg)
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.error("La contraseña debe tener al menos 6 caracteres")
                        else:
                            st.warning("Todos los campos son obligatorios")
            else:
                st.success("✅ Todos los empleados tienen usuario")
        
        else:
            with st.form("form_admin"):
                username = st.text_input("Usuario", placeholder="ej: admin2")
                password = st.text_input("Contraseña", type="password")
                rol = st.selectbox("Rol", ["Administrador", "Supervisor"])
                
                if st.form_submit_button("Crear Usuario", use_container_width=True):
                    if username and password:
                        if len(password) >= 6:
                            if crear_usuario_db(username, password, rol):
                                st.success(f"✅ Usuario {username} creado")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ El usuario ya existe")
                        else:
                            st.error("La contraseña debe tener al menos 6 caracteres")
                    else:
                        st.warning("Todos los campos son obligatorios")

def pagina_config():
    """Configuración del sistema"""
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("⚙️ Configuración del Sistema")
    
    tab1, tab2 = st.tabs(["🎨 Apariencia", "📦 Productos"])
    
    with tab1:
        st.subheader("Configuración de Apariencia")
        
        col1, col2 = st.columns(2)
        
        with col1:
            tema = st.selectbox(
                "Tema",
                ["Claro", "Oscuro", "Sistema"],
                index=["Claro", "Oscuro", "Sistema"].index(
                    st.session_state.config.get("tema", "Claro")
                )
            )
        
        with col2:
            idioma = st.selectbox(
                "Idioma",
                ["Español", "Inglés"],
                index=["Español", "Inglés"].index(
                    st.session_state.config.get("idioma", "Español")
                )
            )
        
        if st.button("Guardar configuración de apariencia", use_container_width=True):
            st.session_state.config["tema"] = tema
            st.session_state.config["idioma"] = idioma
            if guardar_config(st.session_state.config):
                st.success("✅ Configuración guardada")
            else:
                st.error("❌ Error al guardar")
    
    with tab2:
        st.subheader("Productos Adicionales")
        
        productos = st.session_state.config.get("productos_adicionales", [])
        
        with st.form("form_productos"):
            nuevos_productos = st.text_area(
                "Lista de productos (uno por línea)",
                value="\n".join(productos),
                height=150,
                help="Ingresa un producto por línea"
            )
            
            if st.form_submit_button("Guardar productos", use_container_width=True):
                lista_productos = [p.strip() for p in nuevos_productos.split("\n") if p.strip()]
                st.session_state.config["productos_adicionales"] = lista_productos
                if guardar_config(st.session_state.config):
                    st.success(f"✅ {len(lista_productos)} productos guardados")
                else:
                    st.error("❌ Error al guardar")

def pagina_backup():
    """Backup y restauración"""
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("💾 Backup y Restauración")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📀 Crear Backup")
        st.write("Crea una copia de seguridad de la base de datos")
        
        if st.button("Crear Backup ahora", use_container_width=True, type="primary"):
            with st.spinner("Creando backup..."):
                backup_file = crear_backup()
                
                if backup_file and os.path.exists(backup_file):
                    with open(backup_file, "rb") as f:
                        btn = st.download_button(
                            label="📥 Descargar Backup",
                            data=f,
                            file_name=backup_file,
                            mime="application/gzip",
                            use_container_width=True
                        )
                    st.success(f"✅ Backup creado: {backup_file}")
                else:
                    st.error("❌ Error al crear backup")
    
    with col2:
        st.subheader("🔄 Restaurar Backup")
        st.write("Restaura una copia de seguridad existente")
        
        archivo = st.file_uploader(
            "Seleccionar archivo de backup",
            type=['db', 'gz'],
            help="Archivos .db o .gz"
        )
        
        if archivo is not None:
            if st.button("Restaurar", use_container_width=True, type="primary"):
                with st.spinner("Restaurando backup..."):
                    if restaurar_backup(archivo):
                        st.success("✅ Backup restaurado correctamente")
                        st.info("🔄 La aplicación se reiniciará")
                        st.rerun()
                    else:
                        st.error("❌ Error al restaurar backup")

def pagina_sistema():
    """Información del sistema"""
    if not verificar_permiso("Administrador"):
        st.error("❌ No tienes permisos para acceder a esta página")
        return
    
    st.title("🖥️ Información del Sistema")
    
    # Obtener estadísticas
    conn = get_connection()
    total_ventas = pd.read_sql("SELECT COUNT(*) as total FROM registros_ventas", conn)['total'].iloc[0]
    total_empleados = pd.read_sql("SELECT COUNT(*) as total FROM empleados WHERE activo = 1", conn)['total'].iloc[0]
    total_usuarios = pd.read_sql("SELECT COUNT(*) as total FROM usuarios", conn)['total'].iloc[0]
    conn.close()
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Versión", "2.0.0")
        st.metric("Python", "3.9+")
    
    with col2:
        st.metric("Streamlit", "1.28.1")
        st.metric("Base de datos", "SQLite 3")
    
    with col3:
        st.metric("Registros ventas", total_ventas)
        st.metric("Empleados activos", total_empleados)
    
    with col4:
        st.metric("Usuarios", total_usuarios)
        st.metric("Usuario actual", st.session_state.usuario_actual)
    
    # Información de archivos
    st.subheader("📁 Archivos del Sistema")
    
    col_files1, col_files2 = st.columns(2)
    
    with col_files1:
        if os.path.exists("ventas.db"):
            size_db = os.path.getsize("ventas.db") / 1024
            st.metric("Base de datos", f"{size_db:.1f} KB")
        
        if os.path.exists("app.log"):
            size_log = os.path.getsize("app.log") / 1024
            st.metric("Archivo de log", f"{size_log:.1f} KB")
    
    with col_files2:
        if os.path.exists("config.json"):
            size_config = os.path.getsize("config.json") / 1024
            st.metric("Configuración", f"{size_config:.1f} KB")
        
        backups = list(Path(".").glob("backup_*.gz"))
        st.metric("Backups disponibles", len(backups))
    
    # Ver logs
    with st.expander("📋 Ver logs del sistema"):
        if os.path.exists("app.log"):
            with open("app.log", "r") as f:
                lines = f.readlines()[-50:]  # Últimas 50 líneas
                st.code("".join(lines), language="text")
        else:
            st.info("No hay logs disponibles")

# -------------------- MENÚ LATERAL --------------------
def sidebar_menu():
    """Muestra el menú lateral"""
    with st.sidebar:
        # Información del usuario
        if st.session_state.autenticado:
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
            
            st.markdown("### 📋 Menú")
            st.markdown("---")
            
            # Definir menú según rol
            if st.session_state.usuario_rol == "Vendedor":
                menu_items = {
                    "Registro Ventas": "📝",
                }
            elif st.session_state.usuario_rol == "Supervisor":
                menu_items = {
                    "Registro Ventas": "📝",
                    "Dashboard": "📊",
                    "Empleados": "👥"
                }
            else:  # Administrador
                menu_items = {
                    "Dashboard": "📊",
                    "Empleados": "👥",
                    "Usuarios": "👤",
                    "Configuración": "⚙️",
                    "Backup": "💾",
                    "Sistema": "🖥️"
                }
            
            # Botones del menú
            for page, icon in menu_items.items():
                if st.button(
                    f"{icon} {page}",
                    key=f"menu_{page}",
                    use_container_width=True,
                    type="primary" if st.session_state.pagina_actual == page else "secondary"
                ):
                    st.session_state.pagina_actual = page
                    st.rerun()
            
            st.markdown("---")
            
            # Botón de reinicio (solo admin)
            if st.session_state.usuario_rol == "Administrador":
                if st.button("🔄 Reiniciar App", use_container_width=True):
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.rerun()
            
            # Cerrar sesión
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                cerrar_sesion()
            
            st.caption("© 2024 Locatel Restrepo")

# -------------------- MAIN --------------------
def main():
    """Función principal de la aplicación"""
    
    # Verificar entorno
    issues = check_environment()
    if issues:
        for issue in issues:
            st.warning(f"⚠️ {issue}")
    
    # Inicializar estado
    init_session_state()
    
    # Inicializar base de datos
    create_tables()
    
    # Mostrar menú lateral si está autenticado
    if st.session_state.autenticado:
        sidebar_menu()
    
    # Navegación
    if not st.session_state.autenticado:
        pagina_login()
    else:
        if st.session_state.pagina_actual == "Login":
            pagina_login()
        elif st.session_state.pagina_actual == "Registro Ventas":
            pagina_registro_ventas()
        elif st.session_state.pagina_actual == "Dashboard":
            pagina_dashboard()
        elif st.session_state.pagina_actual == "Empleados":
            pagina_empleados()
        elif st.session_state.pagina_actual == "Usuarios":
            pagina_usuarios()
        elif st.session_state.pagina_actual == "Configuración":
            pagina_config()
        elif st.session_state.pagina_actual == "Backup":
            pagina_backup()
        elif st.session_state.pagina_actual == "Sistema":
            pagina_sistema()

if __name__ == "__main__":
    main()