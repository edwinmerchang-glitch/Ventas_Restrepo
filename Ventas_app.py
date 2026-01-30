# ventas_app.py - Aplicación completa de gestión de ventas con autenticación
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
import secrets
from datetime import date, datetime, timedelta

# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================
st.set_page_config(
    page_title="Sistema de Unidades Vendidas Restrepo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .login-container {
        max-width: 400px;
        margin: 5rem auto;
        padding: 2rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .role-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .role-admin {
        background: #ffebee;
        color: #c62828;
    }
    .role-vendedor {
        background: #e8f5e9;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# BASE DE DATOS - INICIALIZACIÓN COMPLETA
# ============================================================================
DB_NAME = "ventas.db"

def get_connection():
    """Obtiene una conexión a la base de datos"""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Error al conectar a la base de datos: {e}")
        return None

def hash_password(password, salt=None):
    """Hash de contraseña con salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode('utf-8'))
    return hash_obj.hexdigest(), salt

def init_auth_tables():
    """Inicializa solo las tablas de autenticación"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Tabla de roles
        c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            permisos TEXT DEFAULT 'read'
        )
        """)
        
        # Tabla de usuarios
        c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            rol_id INTEGER,
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (rol_id) REFERENCES roles(id)
        )
        """)
        
        # Insertar roles por defecto si no existen
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            roles = [
                ('admin', 'Administrador del sistema', 'read,write,delete,manage_users'),
                ('vendedor', 'Vendedor', 'read,write'),
                ('inventario', 'Encargado de inventario', 'read,write,inventory'),
                ('reportes', 'Solo visualización', 'read')
            ]
            c.executemany(
                "INSERT INTO roles (nombre, descripcion, permisos) VALUES (?, ?, ?)",
                roles
            )
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar autenticación: {e}")
        return False

def init_sales_tables():
    """Inicializa las tablas de ventas"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Tabla de ventas
        c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            anio INTEGER NOT NULL,
            mes TEXT NOT NULL,
            dia INTEGER NOT NULL,
            empleado TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            tipo_venta TEXT NOT NULL,
            canal TEXT NOT NULL,
            ticket INTEGER UNIQUE NOT NULL,
            cantidad_total INTEGER DEFAULT 0,
            usuario_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
        """)
        
        # Tabla de detalle de ventas
        c.execute("""
        CREATE TABLE IF NOT EXISTS ventas_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_medida TEXT NOT NULL,
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
        )
        """)
        
        # Tabla de productos
        c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_medida TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Tabla de empleados
        c.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            activo BOOLEAN DEFAULT 1
        )
        """)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar tablas de ventas: {e}")
        return False

def create_default_admin():
    """Crea el usuario admin por defecto si no existe"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si existe el usuario admin
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if c.fetchone()[0] == 0:
            # Obtener ID del rol admin
            c.execute("SELECT id FROM roles WHERE nombre = 'admin'")
            rol_admin = c.fetchone()
            
            if rol_admin:
                password_hash, salt = hash_password("admin123")
                c.execute("""
                    INSERT INTO usuarios 
                    (username, nombre_completo, email, password_hash, salt, rol_id, activo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "admin",
                    "Administrador Principal",
                    "admin@drogueria.com",
                    password_hash,
                    salt,
                    rol_admin['id'],
                    1
                ))
                conn.commit()
                st.info("✅ Usuario admin creado por defecto")
        
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al crear usuario admin: {e}")
        return False

def insert_initial_data():
    """Inserta datos iniciales en las tablas de ventas"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Insertar empleados de ejemplo si la tabla está vacía
        c.execute("SELECT COUNT(*) as count FROM empleados")
        if c.fetchone()[0] == 0:
            empleados = [
                ("Carlos Restrepo", "Vendedor", "Farmacia"),
                ("Ana García", "Cajera", "Cajas"),
                ("Luis Fernández", "Asesor", "Equipos Médicos"),
                ("María Rodríguez", "Vendedor", "Pasillos"),
                ("Pedro Sánchez", "Gerente", "Farmacia"),
                ("Laura Martínez", "Cajera", "Cajas")
            ]
            c.executemany(
                "INSERT OR IGNORE INTO empleados (nombre, cargo, area) VALUES (?, ?, ?)",
                empleados
            )
        
        # Insertar productos de ejemplo si la tabla está vacía
        c.execute("SELECT COUNT(*) as count FROM productos")
        if c.fetchone()[0] == 0:
            productos = [
                ("MED001", "Paracetamol 500mg", "Medicamentos", "Caja", 100),
                ("MED002", "Ibuprofeno 400mg", "Medicamentos", "Caja", 80),
                ("MED003", "Amoxicilina 500mg", "Medicamentos", "Frasco", 50),
                ("HIG001", "Jabón Antibacterial", "Higiene", "Unidad", 200),
                ("HIG002", "Alcohol Antiséptico", "Higiene", "Botella", 150),
                ("HIG003", "Tapabocas N95", "Higiene", "Caja", 75),
                ("BEB001", "Agua Mineral 600ml", "Bebidas", "Botella", 300),
                ("BEB002", "Gatorade 500ml", "Bebidas", "Botella", 150),
                ("EQU001", "Termómetro Digital", "Equipos", "Unidad", 30),
                ("EQU002", "Tensiómetro", "Equipos", "Unidad", 15),
                ("COS001", "Protector Solar 50FPS", "Cosmética", "Tubo", 60),
                ("COS002", "Crema Hidratante", "Cosmética", "Frasco", 70)
            ]
            c.executemany(
                """INSERT OR IGNORE INTO productos 
                (codigo, nombre, categoria, unidad_medida, stock) 
                VALUES (?, ?, ?, ?, ?)""",
                productos
            )
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al insertar datos iniciales: {e}")
        return False

def check_and_init_database():
    """Verifica e inicializa toda la base de datos si es necesario"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si la tabla de usuarios existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        usuarios_exists = c.fetchone() is not None
        
        # Verificar si la tabla de ventas existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventas'")
        ventas_exists = c.fetchone() is not None
        
        conn.close()
        
        # Si no existe la tabla de usuarios, inicializar todo
        if not usuarios_exists:
            st.info("🔧 Inicializando sistema de autenticación...")
            if not init_auth_tables():
                return False
            
            # Crear usuario admin por defecto
            if not create_default_admin():
                return False
            
            st.success("✅ Sistema de autenticación inicializado")
        
        # Si no existe la tabla de ventas, inicializar
        if not ventas_exists:
            st.info("🛒 Inicializando sistema de ventas...")
            if not init_sales_tables():
                return False
            
            # Insertar datos iniciales
            if not insert_initial_data():
                return False
            
            st.success("✅ Sistema de ventas inicializado")
        
        return True
        
    except Exception as e:
        st.error(f"Error al verificar base de datos: {e}")
        return False

# ============================================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================================
def check_authentication(username, password):
    """Verifica las credenciales del usuario"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT u.*, r.nombre as rol_nombre, r.permisos 
            FROM usuarios u 
            LEFT JOIN roles r ON u.rol_id = r.id 
            WHERE u.username = ? AND u.activo = 1
        """, (username,))
        
        user = c.fetchone()
        conn.close()
        
        if user:
            # Verificar contraseña
            stored_hash = user['password_hash']
            salt = user['salt']
            input_hash, _ = hash_password(password, salt)
            
            if input_hash == stored_hash:
                # Actualizar último login
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    "UPDATE usuarios SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user['id'],)
                )
                conn.commit()
                conn.close()
                
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'nombre': user['nombre_completo'],
                    'rol': user['rol_nombre'],
                    'permisos': user['permisos'].split(',') if user['permisos'] else [],
                    'email': user['email']
                }
        
        return None
        
    except Exception as e:
        st.error(f"Error en autenticación: {e}")
        return None

def has_permission(user, required_permission):
    """Verifica si el usuario tiene el permiso requerido"""
    if not user:
        return False
    return required_permission in user['permisos'] or 'admin' in user['permisos']

# ============================================================================
# PANTALLA DE LOGIN
# ============================================================================
def show_login():
    """Muestra la pantalla de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Gestión - Droguería Restrepo</h1>
        <h3>Iniciar Sesión</h3>
        <p>Acceso restringido al personal autorizado</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Verificar e inicializar base de datos
    if not check_and_init_database():
        st.error("❌ Error al inicializar la base de datos. Revise los logs.")
        return
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### 📝 Inicio de Sesión")
            
            # Credenciales por defecto
            st.info("**Credenciales por defecto:**\n- Usuario: `admin`\n- Contraseña: `admin123`")
            
            with st.form("login_form"):
                username = st.text_input("Usuario", placeholder="admin")
                password = st.text_input("Contraseña", type="password", placeholder="admin123")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    login_submitted = st.form_submit_button("🚪 Ingresar", type="primary", use_container_width=True)
                with col_btn2:
                    if st.form_submit_button("🔄 Limpiar", type="secondary", use_container_width=True):
                        st.rerun()
                
                if login_submitted:
                    if not username or not password:
                        st.error("❌ Por favor complete todos los campos")
                    else:
                        with st.spinner("Verificando credenciales..."):
                            user = check_authentication(username, password)
                            if user:
                                st.session_state.user = user
                                st.session_state.authenticated = True
                                st.session_state.page = 'inicio'
                                st.success(f"✅ Bienvenido, {user['nombre']}!")
                                st.rerun()
                            else:
                                st.error("❌ Usuario o contraseña incorrectos")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE VENTAS (simplificadas para el ejemplo)
# ============================================================================
def get_stats():
    """Obtiene estadísticas generales"""
    stats = {
        'ventas_count': 0,
        'unidades_total': 0,
        'empleados_count': 0
    }
    
    try:
        conn = get_connection()
        
        # Total de ventas
        df_ventas = pd.read_sql("SELECT COUNT(*) as total FROM ventas", conn)
        stats['ventas_count'] = int(df_ventas['total'].iloc[0])
        
        # Unidades totales
        df_unidades = pd.read_sql("SELECT COALESCE(SUM(cantidad_total), 0) as unidades FROM ventas", conn)
        stats['unidades_total'] = int(df_unidades['unidades'].iloc[0])
        
        # Empleados activos
        df_empleados = pd.read_sql("SELECT COUNT(DISTINCT empleado) as empleados FROM ventas", conn)
        stats['empleados_count'] = int(df_empleados['empleados'].iloc[0])
        
        conn.close()
        
    except Exception as e:
        # No mostrar error si las tablas aún no tienen datos
        pass
        
    return stats

def show_home():
    """Muestra la página de inicio"""
    user = st.session_state.get('user')
    
    st.markdown(f"""
    <div class="main-header">
        <h1>🏥 Sistema de Gestión de Unidades Vendidas</h1>
        <h3>Droguería Restrepo</h3>
        <p>Bienvenido, <strong>{user['nombre']}</strong> | Rol: <span class="role-badge role-{user['rol']}">{user['rol'].upper()}</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Estadísticas
    st.header("📈 Estadísticas del Equipo")
    
    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Unidades Totales", f"{stats['unidades_total']:,}")
    with col2:
        st.metric("👥 Empleados", stats['empleados_count'])
    with col3:
        st.metric("📋 Ventas", stats['ventas_count'])
    with col4:
        st.metric("📊 Prom. por Venta", f"{stats['unidades_total']/max(stats['ventas_count'], 1):.1f}")

def show_registro():
    """Muestra la página de registro de ventas"""
    if not has_permission(st.session_state.get('user'), 'write'):
        st.error("⛔ No tiene permisos para registrar ventas")
        return
    
    st.title("📝 Registro de Ventas")
    st.info("Funcionalidad de registro en desarrollo...")

def show_user_management():
    """Gestión de usuarios"""
    if not has_permission(st.session_state.get('user'), 'manage_users'):
        st.error("⛔ No tiene permisos para acceder a esta sección")
        return
    
    st.title("👥 Gestión de Usuarios")
    
    try:
        conn = get_connection()
        usuarios = pd.read_sql("""
            SELECT 
                u.id,
                u.username,
                u.nombre_completo,
                u.email,
                r.nombre as rol,
                u.activo
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            ORDER BY u.created_at DESC
        """, conn)
        
        if not usuarios.empty:
            st.dataframe(usuarios, use_container_width=True)
        else:
            st.info("No hay usuarios registrados")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error: {e}")

def show_profile():
    """Muestra el perfil del usuario"""
    user = st.session_state.get('user')
    
    st.title("👤 Mi Perfil")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: #f0f2f6; border-radius: 10px;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">👤</div>
            <h3>{user['nombre']}</h3>
            <div class="role-badge role-{user['rol']}">{user['rol'].upper()}</div>
            <p style="margin-top: 1rem; color: #666;">{user['username']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("Información del Usuario")
        st.write(f"**Nombre completo:** {user['nombre']}")
        st.write(f"**Rol:** {user['rol']}")
        st.write(f"**Permisos:** {', '.join(user['permisos'])}")
        if user.get('email'):
            st.write(f"**Email:** {user['email']}")

# ============================================================================
# APLICACIÓN PRINCIPAL
# ============================================================================
def main():
    """Función principal"""
    
    # Inicializar estados de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'inicio'
    
    # Si no está autenticado, mostrar login
    if not st.session_state.authenticated:
        show_login()
        return
    
    # ========================================================================
    # SIDEBAR
    # ========================================================================
    with st.sidebar:
        user = st.session_state.user
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0;">
            <h2>🏥 Droguería Restrepo</h2>
            <p><strong>{user['nombre']}</strong></p>
            <div class="role-badge role-{user['rol']}">{user['rol'].upper()}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Navegación
        st.markdown("### 📍 Navegación")
        
        if st.button("🏠 Inicio", use_container_width=True):
            st.session_state.page = 'inicio'
            st.rerun()
        
        if st.button("📝 Registrar Ventas", use_container_width=True):
            st.session_state.page = 'registro'
            st.rerun()
        
        # Módulos de admin
        if has_permission(user, 'manage_users'):
            st.divider()
            if st.button("👥 Gestión de Usuarios", use_container_width=True):
                st.session_state.page = 'usuarios'
                st.rerun()
        
        # Perfil y logout
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Perfil", use_container_width=True):
                st.session_state.page = 'perfil'
                st.rerun()
        with col2:
            if st.button("🚪 Salir", use_container_width=True, type="secondary"):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()
    
    # ========================================================================
    # CONTENIDO PRINCIPAL
    # ========================================================================
    if st.session_state.page == 'inicio':
        show_home()
    elif st.session_state.page == 'registro':
        show_registro()
    elif st.session_state.page == 'usuarios':
        show_user_management()
    elif st.session_state.page == 'perfil':
        show_profile()

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    main()