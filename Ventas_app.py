# ventas_app.py - Aplicación completa con gestión de empleados FUNCIONAL
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
    .employee-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# BASE DE DATOS - VERSIÓN SIMPLIFICADA Y FUNCIONAL
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

def initialize_database():
    """Inicializa toda la base de datos de manera segura"""
    try:
        conn = get_connection()
        if conn is None:
            return False
            
        c = conn.cursor()
        
        # 1. Tabla de roles
        c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            permisos TEXT DEFAULT 'read'
        )
        """)
        
        # 2. Tabla de usuarios
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
        
        # 3. Tabla de empleados - ESTRUCTURA SIMPLIFICADA Y SEGURA
        c.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            fecha_ingreso DATE DEFAULT CURRENT_DATE,
            telefono TEXT,
            email TEXT,
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 4. Otras tablas (opcionales por ahora)
        c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            empleado_id INTEGER,
            empleado_nombre TEXT NOT NULL,
            cantidad_total INTEGER DEFAULT 0,
            usuario_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        
        # Insertar datos iniciales si las tablas están vacías
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            roles = [
                ('admin', 'Administrador', 'read,write,delete,manage_users,manage_employees'),
                ('gerente', 'Gerente', 'read,write,manage_employees'),
                ('vendedor', 'Vendedor', 'read,write')
            ]
            c.executemany("INSERT OR IGNORE INTO roles (nombre, descripcion, permisos) VALUES (?, ?, ?)", roles)
        
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if c.fetchone()[0] == 0:
            # Obtener ID del rol admin
            c.execute("SELECT id FROM roles WHERE nombre = 'admin'")
            rol_result = c.fetchone()
            if rol_result:
                rol_id = rol_result[0]
                password_hash, salt = hash_password("admin123")
                c.execute("""
                    INSERT INTO usuarios (username, nombre_completo, password_hash, salt, rol_id)
                    VALUES (?, ?, ?, ?, ?)
                """, ("admin", "Administrador Principal", password_hash, salt, rol_id))
        
        # Insertar empleados de ejemplo solo si la tabla está vacía
        c.execute("SELECT COUNT(*) FROM empleados")
        if c.fetchone()[0] == 0:
            empleados = [
                ("EMP001", "Carlos Restrepo", "Vendedor", "Farmacia", "2023-01-15", "3001234567", "carlos@drogueria.com"),
                ("EMP002", "Ana García", "Cajera", "Cajas", "2023-02-20", "3002345678", "ana@drogueria.com"),
                ("EMP003", "Luis Fernández", "Asesor", "Equipos Médicos", "2023-03-10", "3003456789", "luis@drogueria.com")
            ]
            for emp in empleados:
                try:
                    c.execute("""
                        INSERT INTO empleados (codigo, nombre, cargo, area, fecha_ingreso, telefono, email)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, emp)
                except sqlite3.IntegrityError:
                    # Si ya existe, continuar
                    pass
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar base de datos: {e}")
        return False

def check_database_ready():
    """Verifica si la base de datos está lista para usar"""
    try:
        conn = get_connection()
        if conn is None:
            return False
            
        c = conn.cursor()
        
        # Verificar tablas esenciales
        tables = ['usuarios', 'empleados', 'roles']
        for table in tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if c.fetchone() is None:
                conn.close()
                return False
        
        # Verificar columnas de empleados
        c.execute("PRAGMA table_info(empleados)")
        columns = [col[1] for col in c.fetchall()]
        required_columns = ['codigo', 'nombre', 'cargo', 'area', 'activo']
        
        for col in required_columns:
            if col not in columns:
                conn.close()
                return False
        
        conn.close()
        return True
        
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
        
        if user:
            stored_hash = user['password_hash']
            salt = user['salt']
            input_hash, _ = hash_password(password, salt)
            
            if input_hash == stored_hash:
                # Actualizar último login
                c.execute("UPDATE usuarios SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
                conn.commit()
                conn.close()
                
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'nombre': user['nombre_completo'],
                    'rol': user['rol_nombre'],
                    'permisos': user['permisos'].split(',') if user['permisos'] else []
                }
        
        conn.close()
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
# GESTIÓN DE EMPLEADOS - FUNCIONES FUNCIONALES
# ============================================================================
def get_employees(filtro_activo=None):
    """Obtiene todos los empleados de forma SEGURA"""
    try:
        conn = get_connection()
        
        # Consulta básica pero segura
        query = """
            SELECT 
                id,
                codigo,
                nombre,
                cargo,
                area,
                fecha_ingreso,
                telefono,
                email,
                activo,
                created_at
            FROM empleados
            WHERE 1=1
        """
        
        params = []
        
        if filtro_activo is not None:
            query += " AND activo = ?"
            params.append(filtro_activo)
        
        query += " ORDER BY nombre"
        
        empleados = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return empleados
        
    except Exception as e:
        st.markdown(f"""
        <div class="error-box">
            <strong>Error al obtener empleados:</strong><br>
            {str(e)}
        </div>
        """, unsafe_allow_html=True)
        return pd.DataFrame()

def create_employee_simple(codigo, nombre, cargo, area, telefono=None, email=None):
    """Crea un nuevo empleado de forma SEGURA"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Validar que el código no exista
        c.execute("SELECT id FROM empleados WHERE codigo = ?", (codigo,))
        if c.fetchone() is not None:
            return False, "❌ El código de empleado ya existe"
        
        # Validar que el nombre no esté vacío
        if not nombre or nombre.strip() == "":
            return False, "❌ El nombre es requerido"
        
        # Preparar valores para teléfono y email
        telefono_val = telefono.strip() if telefono and telefono.strip() else None
        email_val = email.strip() if email and email.strip() else None
        
        # Insertar nuevo empleado
        c.execute("""
            INSERT INTO empleados 
            (codigo, nombre, cargo, area, telefono, email, activo, fecha_ingreso)
            VALUES (?, ?, ?, ?, ?, ?, 1, DATE('now'))
        """, (
            codigo.strip(),
            nombre.strip(),
            cargo.strip(),
            area.strip(),
            telefono_val,
            email_val
        ))
        
        conn.commit()
        conn.close()
        return True, "✅ Empleado creado exitosamente"
        
    except sqlite3.IntegrityError as e:
        return False, f"❌ Error de integridad: {str(e)}"
    except Exception as e:
        return False, f"❌ Error al crear empleado: {str(e)}"

def update_employee_status_simple(employee_id, activo):
    """Actualiza el estado de un empleado"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("UPDATE empleados SET activo = ? WHERE id = ?", (activo, employee_id))
        
        if c.rowcount > 0:
            conn.commit()
            conn.close()
            return True, "✅ Estado actualizado correctamente"
        else:
            conn.close()
            return False, "❌ No se encontró el empleado"
            
    except Exception as e:
        return False, f"❌ Error al actualizar estado: {str(e)}"

def get_areas_from_db():
    """Obtiene áreas disponibles desde la base de datos"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("SELECT DISTINCT area FROM empleados WHERE area IS NOT NULL AND area != '' ORDER BY area")
        areas = [row[0] for row in c.fetchall()]
        conn.close()
        
        # Si no hay áreas en la BD, usar algunas por defecto
        if not areas:
            areas = ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Administración", "Inventario"]
        
        return areas
    except:
        return ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Administración", "Inventario"]

# ============================================================================
# GESTIÓN DE EMPLEADOS - INTERFAZ FUNCIONAL
# ============================================================================
def show_employee_management():
    """Muestra la gestión de empleados - VERSIÓN FUNCIONAL"""
    if not has_permission(st.session_state.get('user'), 'manage_employees'):
        st.error("⛔ No tiene permisos para acceder a esta sección")
        return
    
    st.title("👤 Gestión de Empleados")
    
    # Verificar estado de la base de datos
    if not check_database_ready():
        st.warning("⚠️ La base de datos necesita ser inicializada...")
        if st.button("🛠️ Inicializar Base de Datos", type="primary"):
            with st.spinner("Inicializando..."):
                if initialize_database():
                    st.success("✅ Base de datos inicializada correctamente")
                    st.rerun()
                else:
                    st.error("❌ Error al inicializar la base de datos")
        return
    
    # Tabs principales
    tab1, tab2 = st.tabs(["📋 Lista de Empleados", "➕ Nuevo Empleado"])
    
    with tab1:
        show_employee_list_simple()
    
    with tab2:
        show_new_employee_form_simple()

def show_employee_list_simple():
    """Muestra la lista de empleados - VERSIÓN SIMPLE Y FUNCIONAL"""
    st.subheader("📋 Lista de Empleados")
    
    # Filtro simple
    filtro = st.radio("Mostrar:", ["Todos", "Solo Activos", "Solo Inactivos"], horizontal=True)
    
    # Convertir filtro
    if filtro == "Solo Activos":
        filtro_activo = 1
    elif filtro == "Solo Inactivos":
        filtro_activo = 0
    else:
        filtro_activo = None
    
    # Obtener empleados
    empleados = get_employees(filtro_activo=filtro_activo)
    
    if not empleados.empty:
        # Estadísticas
        total = len(empleados)
        activos = len(empleados[empleados['activo'] == 1])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", total)
        with col2:
            st.metric("Activos", activos)
        with col3:
            st.metric("Inactivos", total - activos)
        
        st.divider()
        
        # Mostrar empleados en una tabla simple
        for idx, emp in empleados.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"""
                **{emp['nombre']}** ({emp['codigo']})  
                *{emp['cargo']} - {emp['area']}*  
                Estado: {'✅ Activo' if emp['activo'] else '❌ Inactivo'}
                """)
            
            with col2:
                if pd.notna(emp['telefono']):
                    st.write(f"📞 {emp['telefono']}")
                if pd.notna(emp['email']):
                    st.write(f"📧 {emp['email']}")
                if pd.notna(emp['fecha_ingreso']):
                    st.write(f"📅 {emp['fecha_ingreso']}")
            
            with col3:
                # Botones de acción
                if emp['activo']:
                    if st.button("❌ Desactivar", key=f"deact_{emp['id']}", use_container_width=True):
                        success, msg = update_employee_status_simple(emp['id'], 0)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    if st.button("✅ Activar", key=f"act_{emp['id']}", use_container_width=True):
                        success, msg = update_employee_status_simple(emp['id'], 1)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            
            st.divider()
    else:
        st.info("📭 No hay empleados registrados. Agrega el primero usando la pestaña 'Nuevo Empleado'.")

def show_new_employee_form_simple():
    """Muestra formulario para nuevo empleado - VERSIÓN SIMPLE Y FUNCIONAL"""
    st.subheader("➕ Registrar Nuevo Empleado")
    
    with st.form("form_nuevo_empleado", clear_on_submit=True):
        st.markdown("**Información básica del empleado:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            codigo = st.text_input(
                "Código de empleado*",
                placeholder="EMP001",
                help="Código único para identificar al empleado"
            )
            
            nombre = st.text_input(
                "Nombre completo*",
                placeholder="Juan Pérez Rodríguez",
                help="Nombre y apellidos del empleado"
            )
            
            cargo = st.selectbox(
                "Cargo*",
                ["Vendedor", "Cajero/a", "Asesor", "Gerente", "Almacenista", "Supervisor", "Auxiliar", "Otro"]
            )
        
        with col2:
            # Obtener áreas existentes o usar por defecto
            areas = get_areas_from_db()
            area = st.selectbox("Área*", areas)
            
            telefono = st.text_input(
                "Teléfono",
                placeholder="3001234567",
                help="Teléfono de contacto (opcional)",
                value=""
            )
            
            email = st.text_input(
                "Email",
                placeholder="empleado@drogueria.com",
                help="Correo electrónico (opcional)",
                value=""
            )
        
        # Botón de envío
        submitted = st.form_submit_button(
            "💾 Guardar Empleado", 
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validaciones básicas
            if not codigo.strip():
                st.error("❌ El código de empleado es obligatorio")
            elif not nombre.strip():
                st.error("❌ El nombre completo es obligatorio")
            elif not cargo:
                st.error("❌ El cargo es obligatorio")
            elif not area:
                st.error("❌ El área es obligatoria")
            else:
                with st.spinner("Guardando empleado..."):
                    # Convertir campos vacíos a None
                    telefono_val = telefono if telefono.strip() else None
                    email_val = email if email.strip() else None
                    
                    success, message = create_employee_simple(
                        codigo, nombre, cargo, area, telefono_val, email_val
                    )
                    
                    if success:
                        st.markdown(f"""
                        <div class="success-box">
                            {message}
                        </div>
                        """, unsafe_allow_html=True)
                        st.balloons()
                        st.rerun()
                    else:
                        st.markdown(f"""
                        <div class="error-box">
                            {message}
                        </div>
                        """, unsafe_allow_html=True)

# ============================================================================
# PANTALLA DE LOGIN
# ============================================================================
def show_login():
    """Muestra la pantalla de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Gestión - Droguería Restrepo</h1>
        <h3>Iniciar Sesión</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar base de datos si es necesario
    if not check_database_ready():
        with st.spinner("Preparando sistema..."):
            if not initialize_database():
                st.error("No se pudo inicializar el sistema. Contacte al administrador.")
                return
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### 📝 Inicio de Sesión")
            st.info("**Credenciales por defecto:**\n- Usuario: `admin`\n- Contraseña: `admin123`")
            
            username = st.text_input("Usuario", value="admin", key="login_user")
            password = st.text_input("Contraseña", type="password", value="admin123", key="login_pass")
            
            if st.button("🚪 Ingresar al Sistema", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("Por favor complete ambos campos")
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
# APLICACIÓN PRINCIPAL
# ============================================================================
def main():
    """Función principal de la aplicación"""
    
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
            <p style="color: #666; font-size: 0.9rem;">Rol: {user['rol']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Navegación principal
        st.markdown("### 📍 Navegación Principal")
        
        if st.button("🏠 Inicio / Dashboard", use_container_width=True, type="primary"):
            st.session_state.page = 'inicio'
            st.rerun()
        
        if st.button("📝 Registrar Ventas", use_container_width=True):
            st.session_state.page = 'ventas'
            st.rerun()
        
        if st.button("📊 Ver Reportes", use_container_width=True):
            st.session_state.page = 'reportes'
            st.rerun()
        
        # Módulos de administración
        if has_permission(user, 'manage_employees'):
            st.divider()
            st.markdown("### ⚙️ Administración")
            
            if st.button("👤 Gestión de Empleados", use_container_width=True):
                st.session_state.page = 'empleados'
                st.rerun()
        
        # Perfil y salir
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Mi Perfil", use_container_width=True):
                st.session_state.page = 'perfil'
                st.rerun()
        with col2:
            if st.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()
    
    # ========================================================================
    # CONTENIDO PRINCIPAL
    # ========================================================================
    if st.session_state.page == 'inicio':
        st.title("🏠 Panel de Control")
        st.write(f"Bienvenido, **{user['nombre']}**")
        
        # Estadísticas rápidas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            empleados = get_employees(filtro_activo=1)
            st.metric("👥 Empleados Activos", len(empleados) if not empleados.empty else 0)
        
        with col2:
            st.metric("🔑 Tu Rol", user['rol'].capitalize())
        
        with col3:
            st.metric("📊 Accesos", len(user['permisos']))
        
        # Acciones rápidas
        st.divider()
        st.subheader("⚡ Acciones Rápidas")
        
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button("➕ Agregar Empleado", use_container_width=True):
                st.session_state.page = 'empleados'
                st.rerun()
        
        with col_act2:
            if st.button("📝 Nueva Venta", use_container_width=True):
                st.session_state.page = 'ventas'
                st.rerun()
        
        with col_act3:
            if st.button("📊 Ver Estadísticas", use_container_width=True):
                st.session_state.page = 'reportes'
                st.rerun()
    
    elif st.session_state.page == 'empleados':
        show_employee_management()
    
    elif st.session_state.page == 'ventas':
        st.title("📝 Registro de Ventas")
        st.info("Esta funcionalidad estará disponible pronto. Mientras tanto, puedes gestionar empleados.")
        
        if st.button("👤 Ir a Gestión de Empleados"):
            st.session_state.page = 'empleados'
            st.rerun()
    
    elif st.session_state.page == 'reportes':
        st.title("📊 Reportes y Estadísticas")
        st.info("Módulo de reportes en desarrollo.")
    
    elif st.session_state.page == 'perfil':
        st.title("👤 Mi Perfil")
        st.write(f"**Usuario:** {user['username']}")
        st.write(f"**Nombre:** {user['nombre']}")
        st.write(f"**Rol:** {user['rol']}")
        st.write(f"**Permisos:** {', '.join(user['permisos'])}")

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    main()