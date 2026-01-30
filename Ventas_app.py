# ventas_app.py - Aplicación completa de gestión de ventas con autenticación
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import date

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
        margin: 2px;
    }
    .role-admin { background: #ffebee; color: #c62828; }
    .role-vendedor { background: #e8f5e9; color: #2e7d32; }
    .role-inventario { background: #e3f2fd; color: #1565c0; }
    .role-reportes { background: #f3e5f5; color: #7b1fa2; }
    
    .user-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
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

def init_database_complete():
    """Inicializa toda la base de datos"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # 1. Crear tabla de roles
        c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            permisos TEXT DEFAULT 'read'
        )
        """)
        
        # 2. Crear tabla de usuarios
        c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            rol_id INTEGER,
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (rol_id) REFERENCES roles(id)
        )
        """)
        
        # 3. Crear otras tablas del sistema
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
        
        # 4. Insertar datos iniciales
        insert_initial_data(conn)
        
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar base de datos: {e}")
        return False

def insert_initial_data(conn):
    """Inserta datos iniciales en todas las tablas"""
    try:
        c = conn.cursor()
        
        # Insertar roles si no existen
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            roles = [
                ('admin', 'Administrador del sistema', 'read,write,delete,manage_users'),
                ('vendedor', 'Vendedor', 'read,write'),
                ('inventario', 'Encargado de inventario', 'read,write,inventory'),
                ('reportes', 'Solo visualización', 'read')
            ]
            c.executemany(
                "INSERT OR IGNORE INTO roles (nombre, descripcion, permisos) VALUES (?, ?, ?)",
                roles
            )
        
        # Insertar usuario admin si no existe
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if c.fetchone()[0] == 0:
            # Obtener ID del rol admin
            c.execute("SELECT id FROM roles WHERE nombre = 'admin'")
            result = c.fetchone()
            if result:
                rol_id = result[0]
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
                    rol_id,
                    1
                ))
        
        # Insertar empleados de ejemplo
        c.execute("SELECT COUNT(*) FROM empleados")
        if c.fetchone()[0] == 0:
            empleados = [
                ("Carlos Restrepo", "Vendedor", "Farmacia"),
                ("Ana García", "Cajera", "Cajas"),
                ("Luis Fernández", "Asesor", "Equipos Médicos")
            ]
            c.executemany(
                "INSERT OR IGNORE INTO empleados (nombre, cargo, area) VALUES (?, ?, ?)",
                empleados
            )
        
        # Insertar productos de ejemplo
        c.execute("SELECT COUNT(*) FROM productos")
        if c.fetchone()[0] == 0:
            productos = [
                ("MED001", "Paracetamol 500mg", "Medicamentos", "Caja", 100),
                ("MED002", "Ibuprofeno 400mg", "Medicamentos", "Caja", 80),
                ("HIG001", "Jabón Antibacterial", "Higiene", "Unidad", 200)
            ]
            c.executemany(
                "INSERT OR IGNORE INTO productos (codigo, nombre, categoria, unidad_medida, stock) VALUES (?, ?, ?, ?, ?)",
                productos
            )
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Error al insertar datos iniciales: {e}")
        return False

def check_database_tables():
    """Verifica si las tablas principales existen"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar tabla de usuarios
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        usuarios_exists = c.fetchone() is not None
        
        conn.close()
        return usuarios_exists
        
    except:
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
# GESTIÓN DE USUARIOS - FUNCIONES CORREGIDAS
# ============================================================================
def get_roles_dict():
    """Obtiene los roles como diccionario {nombre: id}"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, nombre FROM roles ORDER BY nombre")
        roles = c.fetchall()
        conn.close()
        
        return {role['nombre']: role['id'] for role in roles}
    except:
        return {'admin': 1, 'vendedor': 2, 'inventario': 3, 'reportes': 4}

def create_user(username, nombre_completo, email, password, rol_nombre, activo=True):
    """Crea un nuevo usuario"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si el usuario ya existe
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = ?", (username,))
        if c.fetchone()[0] > 0:
            return False, "El nombre de usuario ya existe"
        
        # Obtener ID del rol
        roles_dict = get_roles_dict()
        if rol_nombre not in roles_dict:
            return False, "Rol no válido"
        
        rol_id = roles_dict[rol_nombre]
        
        # Hash de contraseña
        password_hash, salt = hash_password(password)
        
        # Insertar usuario
        c.execute("""
            INSERT INTO usuarios 
            (username, nombre_completo, email, password_hash, salt, rol_id, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            nombre_completo,
            email if email else None,
            password_hash,
            salt,
            rol_id,
            1 if activo else 0
        ))
        
        conn.commit()
        conn.close()
        return True, "Usuario creado exitosamente"
        
    except Exception as e:
        return False, f"Error al crear usuario: {str(e)}"

def get_all_users():
    """Obtiene todos los usuarios"""
    try:
        conn = get_connection()
        query = """
            SELECT 
                u.id,
                u.username,
                u.nombre_completo,
                u.email,
                r.nombre as rol,
                u.activo,
                u.created_at,
                u.last_login
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            ORDER BY u.created_at DESC
        """
        usuarios = pd.read_sql(query, conn)
        conn.close()
        return usuarios
    except:
        return pd.DataFrame()

def update_user_status(user_id, activo):
    """Actualiza el estado de un usuario"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (activo, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def delete_user(user_id):
    """Elimina un usuario"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

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
    
    # Verificar si la base de datos existe, si no, crearla
    if not check_database_tables():
        with st.spinner("Inicializando base de datos por primera vez..."):
            if init_database_complete():
                st.success("✅ Base de datos inicializada correctamente")
            else:
                st.error("❌ Error al inicializar la base de datos")
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### 📝 Inicio de Sesión")
            
            # Credenciales por defecto
            st.info("**Credenciales por defecto:**\n- Usuario: `admin`\n- Contraseña: `admin123`")
            
            with st.form("login_form"):
                username = st.text_input("Usuario", value="admin")
                password = st.text_input("Contraseña", type="password", value="admin123")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    login_submitted = st.form_submit_button("🚪 Ingresar", type="primary", use_container_width=True)
                
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
# GESTIÓN DE USUARIOS - INTERFAZ
# ============================================================================
def show_user_management():
    """Muestra la interfaz de gestión de usuarios"""
    if not has_permission(st.session_state.get('user'), 'manage_users'):
        st.error("⛔ No tiene permisos para acceder a esta sección")
        return
    
    st.title("👥 Gestión de Usuarios")
    
    # Tabs para diferentes funcionalidades
    tab1, tab2 = st.tabs(["📋 Lista de Usuarios", "➕ Crear Nuevo Usuario"])
    
    with tab1:
        st.subheader("Usuarios Registrados")
        
        usuarios = get_all_users()
        
        if not usuarios.empty:
            # Formatear columnas
            usuarios['Estado'] = usuarios['activo'].apply(lambda x: '✅ Activo' if x else '❌ Inactivo')
            usuarios['Creado'] = pd.to_datetime(usuarios['created_at']).dt.strftime('%Y-%m-%d')
            usuarios['Último login'] = pd.to_datetime(usuarios['last_login']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Mostrar tabla
            st.dataframe(
                usuarios[['username', 'nombre_completo', 'email', 'rol', 'Estado', 'Creado', 'Último login']],
                use_container_width=True,
                hide_index=True
            )
            
            # Acciones por usuario
            st.subheader("Acciones por Usuario")
            
            for _, user in usuarios.iterrows():
                with st.expander(f"Usuario: {user['username']} - {user['nombre_completo']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    # No permitir acciones sobre uno mismo
                    is_current_user = user['username'] == st.session_state.user['username']
                    
                    with col1:
                        if not is_current_user:
                            new_status = not user['activo']
                            status_text = "Desactivar" if user['activo'] else "Activar"
                            if st.button(f"🔄 {status_text}", key=f"toggle_{user['id']}"):
                                if update_user_status(user['id'], new_status):
                                    st.success(f"Usuario {status_text.lower()}do")
                                    st.rerun()
                    
                    with col2:
                        if st.button("✏️ Editar", key=f"edit_{user['id']}"):
                            st.info(f"Funcionalidad de edición para {user['username']} (en desarrollo)")
                    
                    with col3:
                        if not is_current_user:
                            if st.button("🗑️ Eliminar", key=f"delete_{user['id']}", type="secondary"):
                                if st.checkbox(f"¿Confirmar eliminación de {user['username']}?", key=f"confirm_delete_{user['id']}"):
                                    if delete_user(user['id']):
                                        st.success(f"Usuario {user['username']} eliminado")
                                        st.rerun()
        else:
            st.info("No hay usuarios registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Usuario")
        
        with st.form("new_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Nombre de usuario*", 
                                            placeholder="ej: jperez",
                                            help="Debe ser único")
                new_email = st.text_input("Email", 
                                         placeholder="ej: juan@drogueria.com")
                new_password = st.text_input("Contraseña*", 
                                            type="password",
                                            help="Mínimo 6 caracteres")
            
            with col2:
                new_fullname = st.text_input("Nombre completo*", 
                                            placeholder="ej: Juan Pérez")
                
                # Obtener roles disponibles
                roles_dict = get_roles_dict()
                rol_options = list(roles_dict.keys())
                
                new_role = st.selectbox("Rol*", 
                                       options=rol_options,
                                       help="Seleccione el rol del usuario")
                
                new_active = st.checkbox("Usuario activo", value=True)
            
            # Validar contraseña
            if new_password and len(new_password) < 6:
                st.warning("La contraseña debe tener al menos 6 caracteres")
            
            submitted = st.form_submit_button("💾 Crear Usuario", type="primary")
            
            if submitted:
                # Validaciones
                if not new_username or not new_fullname or not new_password:
                    st.error("Por favor complete los campos obligatorios (*)")
                elif len(new_password) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres")
                else:
                    success, message = create_user(
                        new_username,
                        new_fullname,
                        new_email,
                        new_password,
                        new_role,
                        new_active
                    )
                    
                    if success:
                        st.success(message)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(message)

# ============================================================================
# OTRAS PÁGINAS
# ============================================================================
def show_home():
    """Muestra la página de inicio"""
    user = st.session_state.get('user')
    
    st.markdown(f"""
    <div class="main-header">
        <h1>🏥 Sistema de Gestión de Unidades Vendidas</h1>
        <h3>Droguería Restrepo</h3>
        <p>Bienvenido, <strong>{user['nombre']}</strong> | 
        Rol: <span class="role-badge role-{user['rol']}">{user['rol'].upper()}</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar estadísticas rápidas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("👥 Total Usuarios", len(get_all_users()))
    
    with col2:
        usuarios = get_all_users()
        activos = usuarios[usuarios['activo'] == 1].shape[0] if not usuarios.empty else 0
        st.metric("✅ Usuarios Activos", activos)
    
    with col3:
        st.metric("🔐 Tu Rol", user['rol'].capitalize())

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
        
        st.write(f"**Nombre de usuario:** {user['username']}")
        st.write(f"**Nombre completo:** {user['nombre']}")
        st.write(f"**Rol:** {user['rol']}")
        
        if user.get('email'):
            st.write(f"**Email:** {user['email']}")
        
        st.write(f"**Permisos:**")
        for perm in user['permisos']:
            st.write(f"- {perm}")
        
        # Cambiar contraseña
        with st.expander("🔒 Cambiar Contraseña"):
            with st.form("change_password_form"):
                current_pass = st.text_input("Contraseña actual", type="password")
                new_pass = st.text_input("Nueva contraseña", type="password")
                confirm_pass = st.text_input("Confirmar nueva contraseña", type="password")
                
                if st.form_submit_button("💾 Cambiar Contraseña"):
                    if not current_pass or not new_pass or not confirm_pass:
                        st.error("Complete todos los campos")
                    elif new_pass != confirm_pass:
                        st.error("Las nuevas contraseñas no coinciden")
                    elif len(new_pass) < 6:
                        st.error("La contraseña debe tener al menos 6 caracteres")
                    else:
                        st.info("Funcionalidad en desarrollo")

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
        
        nav_options = [
            ("🏠 Inicio", "inicio"),
            ("📝 Registrar Ventas", "registro"),
            ("📊 Informes", "informes"),
        ]
        
        for icon_text, page in nav_options:
            if st.button(icon_text, use_container_width=True, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()
        
        # Módulos de administración (solo para admin)
        if has_permission(user, 'manage_users'):
            st.divider()
            st.markdown("### ⚙️ Administración")
            
            admin_options = [
                ("👥 Usuarios", "usuarios"),
                ("📦 Productos", "productos"),
                ("👤 Empleados", "empleados"),
            ]
            
            for icon_text, page in admin_options:
                if st.button(icon_text, use_container_width=True, key=f"admin_{page}"):
                    st.session_state.page = page
                    st.rerun()
        
        # Perfil y logout
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Perfil", use_container_width=True, key="btn_perfil"):
                st.session_state.page = 'perfil'
                st.rerun()
        with col2:
            if st.button("🚪 Salir", use_container_width=True, type="secondary", key="btn_logout"):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.session_state.page = 'inicio'
                st.rerun()
    
    # ========================================================================
    # CONTENIDO PRINCIPAL
    # ========================================================================
    if st.session_state.page == 'inicio':
        show_home()
    elif st.session_state.page == 'usuarios':
        show_user_management()
    elif st.session_state.page == 'perfil':
        show_profile()
    elif st.session_state.page == 'registro':
        st.title("📝 Registro de Ventas")
        st.info("Funcionalidad en desarrollo...")
    elif st.session_state.page == 'informes':
        st.title("📊 Informes")
        st.info("Funcionalidad en desarrollo...")
    elif st.session_state.page == 'productos':
        st.title("📦 Gestión de Productos")
        st.info("Funcionalidad en desarrollo...")
    elif st.session_state.page == 'empleados':
        st.title("👤 Gestión de Empleados")
        st.info("Funcionalidad en desarrollo...")

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    main()