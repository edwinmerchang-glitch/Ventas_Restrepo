# ventas_app.py - Aplicación completa con gestión de empleados corregida
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
</style>
""", unsafe_allow_html=True)

# ============================================================================
# BASE DE DATOS - CORREGIDA
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

def check_and_fix_database():
    """Verifica y repara la estructura de la base de datos"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si existe la tabla empleados
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='empleados'")
        if c.fetchone() is None:
            # La tabla no existe, crearla desde cero
            conn.close()
            return init_database_complete()
        
        # Verificar columnas de la tabla empleados
        c.execute("PRAGMA table_info(empleados)")
        columns = c.fetchall()
        column_names = [col[1] for col in columns]
        
        # Columnas necesarias
        required_columns = [
            'id', 'codigo', 'nombre', 'cargo', 'area', 
            'fecha_ingreso', 'telefono', 'email', 'activo',
            'ventas_totales', 'unidades_vendidas', 'created_at'
        ]
        
        # Verificar columnas faltantes
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            st.warning(f"⚠️ La tabla empleados necesita ser actualizada. Columnas faltantes: {missing_columns}")
            
            # Crear tabla temporal con estructura correcta
            c.execute("""
                CREATE TABLE IF NOT EXISTS empleados_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    cargo TEXT NOT NULL,
                    area TEXT NOT NULL,
                    fecha_ingreso DATE DEFAULT CURRENT_DATE,
                    telefono TEXT,
                    email TEXT,
                    activo BOOLEAN DEFAULT 1,
                    ventas_totales INTEGER DEFAULT 0,
                    unidades_vendidas INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migrar datos si existen
            try:
                # Obtener datos existentes
                c.execute("SELECT * FROM empleados")
                old_data = c.fetchall()
                
                if old_data:
                    # Insertar datos en nueva tabla
                    for row in old_data:
                        # Convertir a diccionario
                        row_dict = dict(row)
                        
                        # Generar código si no existe
                        codigo = row_dict.get('codigo', f"EMP{row_dict['id']:03d}")
                        
                        c.execute("""
                            INSERT INTO empleados_new 
                            (id, codigo, nombre, cargo, area, fecha_ingreso, telefono, email, activo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row_dict['id'],
                            codigo,
                            row_dict.get('nombre', ''),
                            row_dict.get('cargo', 'Vendedor'),
                            row_dict.get('area', 'Farmacia'),
                            row_dict.get('fecha_ingreso', date.today().isoformat()),
                            row_dict.get('telefono'),
                            row_dict.get('email'),
                            row_dict.get('activo', 1)
                        ))
            except:
                pass
            
            # Reemplazar tabla
            c.execute("DROP TABLE empleados")
            c.execute("ALTER TABLE empleados_new RENAME TO empleados")
            
            st.success("✅ Tabla empleados actualizada correctamente")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al verificar base de datos: {e}")
        return False

def init_database_complete():
    """Inicializa toda la base de datos con estructura corregida"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # 1. Tabla de roles (primero)
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
        
        # 3. Tabla de empleados (ESTRUCTURA CORREGIDA)
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
            ventas_totales INTEGER DEFAULT 0,
            unidades_vendidas INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 4. Otras tablas
        c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            anio INTEGER NOT NULL,
            mes TEXT NOT NULL,
            dia INTEGER NOT NULL,
            empleado_id INTEGER,
            empleado_nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            tipo_venta TEXT NOT NULL,
            canal TEXT NOT NULL,
            ticket INTEGER UNIQUE NOT NULL,
            cantidad_total INTEGER DEFAULT 0,
            usuario_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
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
        
        conn.commit()
        
        # Insertar datos iniciales
        insert_initial_data(conn)
        
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar base de datos: {e}")
        return False

def insert_initial_data(conn):
    """Inserta datos iniciales"""
    try:
        c = conn.cursor()
        
        # Insertar roles
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            roles = [
                ('admin', 'Administrador', 'read,write,delete,manage_users,manage_employees'),
                ('gerente', 'Gerente', 'read,write,manage_employees'),
                ('vendedor', 'Vendedor', 'read,write')
            ]
            c.executemany("INSERT OR IGNORE INTO roles (nombre, descripcion, permisos) VALUES (?, ?, ?)", roles)
        
        # Insertar usuario admin
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if c.fetchone()[0] == 0:
            c.execute("SELECT id FROM roles WHERE nombre = 'admin'")
            rol_id = c.fetchone()[0]
            
            password_hash, salt = hash_password("admin123")
            c.execute("""
                INSERT INTO usuarios (username, nombre_completo, password_hash, salt, rol_id)
                VALUES (?, ?, ?, ?, ?)
            """, ("admin", "Administrador", password_hash, salt, rol_id))
        
        # Insertar empleados de ejemplo
        c.execute("SELECT COUNT(*) FROM empleados")
        if c.fetchone()[0] == 0:
            empleados = [
                ("EMP001", "Carlos Restrepo", "Vendedor", "Farmacia"),
                ("EMP002", "Ana García", "Cajera", "Cajas"),
                ("EMP003", "Luis Fernández", "Asesor", "Equipos Médicos")
            ]
            c.executemany("""
                INSERT INTO empleados (codigo, nombre, cargo, area)
                VALUES (?, ?, ?, ?)
            """, empleados)
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Error al insertar datos: {e}")
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
            stored_hash = user['password_hash']
            salt = user['salt']
            input_hash, _ = hash_password(password, salt)
            
            if input_hash == stored_hash:
                # Actualizar último login
                conn = get_connection()
                c = conn.cursor()
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
# GESTIÓN DE EMPLEADOS - FUNCIONES SIMPLIFICADAS
# ============================================================================
def get_employees(filtro_activo=None):
    """Obtiene todos los empleados"""
    try:
        conn = get_connection()
        
        query = "SELECT * FROM empleados WHERE 1=1"
        params = []
        
        if filtro_activo is not None:
            query += " AND activo = ?"
            params.append(filtro_activo)
        
        query += " ORDER BY nombre"
        
        empleados = pd.read_sql(query, conn, params=params)
        conn.close()
        return empleados
    except Exception as e:
        st.error(f"Error al obtener empleados: {e}")
        return pd.DataFrame()

def create_employee(codigo, nombre, cargo, area, telefono=None, email=None):
    """Crea un nuevo empleado"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si el código ya existe
        c.execute("SELECT COUNT(*) FROM empleados WHERE codigo = ?", (codigo,))
        if c.fetchone()[0] > 0:
            return False, "El código de empleado ya existe"
        
        # Insertar nuevo empleado
        c.execute("""
            INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (codigo, nombre, cargo, area, telefono, email))
        
        conn.commit()
        conn.close()
        return True, "Empleado creado exitosamente"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_employee_status(employee_id, activo):
    """Actualiza el estado de un empleado"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("UPDATE empleados SET activo = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                 (activo, employee_id))
        
        conn.commit()
        conn.close()
        return True, "Estado actualizado"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_areas():
    """Obtiene áreas disponibles"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT area FROM empleados WHERE area IS NOT NULL ORDER BY area")
        areas = [row[0] for row in c.fetchall()]
        conn.close()
        
        if not areas:
            areas = ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Administración"]
        
        return areas
    except:
        return ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Administración"]

# ============================================================================
# GESTIÓN DE EMPLEADOS - INTERFAZ SIMPLIFICADA
# ============================================================================
def show_employee_management():
    """Muestra la gestión de empleados"""
    if not has_permission(st.session_state.get('user'), 'manage_employees'):
        st.error("⛔ No tiene permisos para acceder a esta sección")
        return
    
    st.title("👤 Gestión de Empleados")
    
    # Verificar y reparar base de datos primero
    if not check_and_fix_database():
        st.error("No se pudo inicializar la base de datos")
        return
    
    # Tabs principales
    tab1, tab2 = st.tabs(["📋 Lista de Empleados", "➕ Nuevo Empleado"])
    
    with tab1:
        show_employee_list()
    
    with tab2:
        show_new_employee_form()

def show_employee_list():
    """Muestra la lista de empleados"""
    st.subheader("📋 Lista de Empleados")
    
    # Filtro de estado
    filtro = st.selectbox("Filtrar por estado:", ["Todos", "Activos", "Inactivos"])
    
    # Convertir filtro
    if filtro == "Activos":
        filtro_activo = 1
    elif filtro == "Inactivos":
        filtro_activo = 0
    else:
        filtro_activo = None
    
    # Obtener empleados
    empleados = get_employees(filtro_activo=filtro_activo)
    
    if not empleados.empty:
        # Mostrar estadísticas
        total = len(empleados)
        activos = len(empleados[empleados['activo'] == 1])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Empleados", total)
        with col2:
            st.metric("Empleados Activos", activos)
        
        # Mostrar empleados
        for _, emp in empleados.iterrows():
            with st.container():
                col_emp1, col_emp2, col_emp3 = st.columns([3, 2, 1])
                
                with col_emp1:
                    st.markdown(f"""
                    <div class="employee-card">
                        <h4>{emp['nombre']}</h4>
                        <p><strong>Código:</strong> {emp['codigo']}</p>
                        <p><strong>Cargo:</strong> {emp['cargo']}</p>
                        <p><strong>Área:</strong> {emp['area']}</p>
                        <p><strong>Estado:</strong> {'✅ Activo' if emp['activo'] else '❌ Inactivo'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_emp2:
                    if emp.get('telefono'):
                        st.write(f"📞 {emp['telefono']}")
                    if emp.get('email'):
                        st.write(f"📧 {emp['email']}")
                    if emp.get('fecha_ingreso'):
                        st.write(f"📅 Ingreso: {emp['fecha_ingreso']}")
                
                with col_emp3:
                    # Botones de acción
                    if emp['activo']:
                        if st.button("❌ Desactivar", key=f"deact_{emp['id']}", use_container_width=True):
                            success, msg = update_employee_status(emp['id'], 0)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button("✅ Activar", key=f"act_{emp['id']}", use_container_width=True):
                            success, msg = update_employee_status(emp['id'], 1)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                
                st.divider()
    else:
        st.info("No hay empleados registrados")

def show_new_employee_form():
    """Muestra formulario para nuevo empleado"""
    st.subheader("➕ Registrar Nuevo Empleado")
    
    with st.form("nuevo_empleado"):
        col1, col2 = st.columns(2)
        
        with col1:
            codigo = st.text_input("Código*", placeholder="EMP001")
            nombre = st.text_input("Nombre completo*", placeholder="Juan Pérez")
            cargo = st.selectbox("Cargo*", ["Vendedor", "Cajero/a", "Asesor", "Gerente", "Almacenista"])
        
        with col2:
            areas = get_areas()
            area = st.selectbox("Área*", areas)
            telefono = st.text_input("Teléfono", placeholder="3001234567")
            email = st.text_input("Email", placeholder="empleado@drogueria.com")
        
        if st.form_submit_button("💾 Guardar Empleado", type="primary"):
            if not codigo or not nombre or not cargo or not area:
                st.error("Por favor complete los campos obligatorios (*)")
            else:
                success, message = create_employee(codigo, nombre, cargo, area, telefono, email)
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)

# ============================================================================
# PANTALLA DE LOGIN SIMPLIFICADA
# ============================================================================
def show_login():
    """Muestra la pantalla de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Gestión - Droguería Restrepo</h1>
        <h3>Iniciar Sesión</h3>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.info("**Usuario:** admin | **Contraseña:** admin123")
            
            username = st.text_input("Usuario", value="admin")
            password = st.text_input("Contraseña", type="password", value="admin123")
            
            if st.button("🚪 Ingresar", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("Complete todos los campos")
                else:
                    with st.spinner("Verificando..."):
                        user = check_authentication(username, password)
                        if user:
                            st.session_state.user = user
                            st.session_state.authenticated = True
                            st.session_state.page = 'inicio'
                            st.success(f"Bienvenido, {user['nombre']}!")
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# APLICACIÓN PRINCIPAL SIMPLIFICADA
# ============================================================================
def main():
    """Función principal"""
    
    # Inicializar estados
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
    # SIDEBAR SIMPLIFICADO
    # ========================================================================
    with st.sidebar:
        user = st.session_state.user
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0;">
            <h2>🏥 Droguería Restrepo</h2>
            <p><strong>{user['nombre']}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Navegación
        if st.button("🏠 Inicio", use_container_width=True):
            st.session_state.page = 'inicio'
            st.rerun()
        
        if has_permission(user, 'manage_employees'):
            if st.button("👤 Empleados", use_container_width=True):
                st.session_state.page = 'empleados'
                st.rerun()
        
        if st.button("📝 Ventas", use_container_width=True):
            st.session_state.page = 'ventas'
            st.rerun()
        
        st.divider()
        
        if st.button("🚪 Salir", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # ========================================================================
    # CONTENIDO PRINCIPAL
    # ========================================================================
    if st.session_state.page == 'inicio':
        st.title("🏠 Inicio")
        st.write(f"Bienvenido, **{user['nombre']}**")
        
        # Mostrar estadísticas rápidas
        empleados = get_employees(filtro_activo=1)
        if not empleados.empty:
            st.metric("👥 Empleados Activos", len(empleados))
    
    elif st.session_state.page == 'empleados':
        show_employee_management()
    
    elif st.session_state.page == 'ventas':
        st.title("📝 Registro de Ventas")
        st.info("Funcionalidad en desarrollo...")

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    # Inicializar base de datos al inicio
    init_database_complete()
    main()