# app.py - Sistema de Gestión Droguería Restrepo (ESTABLE STREAMLIT CLOUD)

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
import os
import time
from datetime import date

# =============================================================================
# CONFIGURACIÓN STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="Sistema de Gestión - Droguería Restrepo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# RUTA SEGURA BASE DE DATOS (STREAMLIT CLOUD)
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "ventas.db")

# =============================================================================
# ESTILOS
# =============================================================================
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-radius: 12px;
    margin-bottom: 2rem;
}
.login-box {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}
.stButton > button {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# BASE DE DATOS
# =============================================================================
def get_connection():
    """Crea y retorna una conexión a la base de datos"""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {str(e)}")
        return None


def hash_password(password, salt=None):
    """Hashea una contraseña con salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt


def initialize_database():
    """Inicializa la base de datos desde cero"""
    try:
        # Eliminar base de datos existente si hay problemas
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
                time.sleep(0.5)
            except:
                pass
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Tabla de roles
        c.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            permisos TEXT
        )
        ''')
        
        # Tabla de usuarios
        c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            rol_id INTEGER NOT NULL,
            activo INTEGER DEFAULT 1,
            FOREIGN KEY (rol_id) REFERENCES roles (id)
        )
        ''')
        
        # Tabla de empleados
        c.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            telefono TEXT,
            email TEXT,
            activo INTEGER DEFAULT 1,
            fecha_ingreso DATE DEFAULT (DATE('now'))
        )
        ''')
        
        # Insertar roles por defecto
        roles = [
            ('admin', 'all'),
            ('gerente', 'manage_employees,view_reports'),
            ('vendedor', 'view_own_data,make_sales')
        ]
        
        for rol in roles:
            try:
                c.execute('INSERT OR IGNORE INTO roles (nombre, permisos) VALUES (?, ?)', rol)
            except:
                pass
        
        # Obtener ID del rol admin
        c.execute('SELECT id FROM roles WHERE nombre = "admin"')
        admin_rol_id = c.fetchone()
        
        if admin_rol_id:
            admin_rol_id = admin_rol_id[0]
            
            # Crear usuario admin por defecto
            password = "admin123"
            password_hash, salt = hash_password(password)
            
            admin_user = ('admin', 'Administrador del Sistema', password_hash, salt, admin_rol_id)
            
            try:
                c.execute('''
                INSERT OR IGNORE INTO usuarios 
                (username, nombre, password_hash, salt, rol_id) 
                VALUES (?, ?, ?, ?, ?)
                ''', admin_user)
            except:
                pass
        
        # Insertar empleados de ejemplo
        empleados_ejemplo = [
            ('EMP001', 'Juan Pérez', 'Vendedor', 'Ventas', '3001234567', 'juan@empresa.com'),
            ('EMP002', 'María Gómez', 'Gerente', 'Administración', '3109876543', 'maria@empresa.com'),
            ('EMP003', 'Carlos López', 'Farmacéutico', 'Farmacia', '3204567890', 'carlos@empresa.com'),
            ('EMP004', 'Ana Rodríguez', 'Cajero', 'Caja', '3157890123', 'ana@empresa.com'),
            ('EMP005', 'Pedro Martínez', 'Almacenista', 'Almacén', '3184567890', 'pedro@empresa.com')
        ]
        
        for emp in empleados_ejemplo:
            try:
                c.execute('''
                INSERT OR IGNORE INTO empleados 
                (codigo, nombre, cargo, area, telefono, email) 
                VALUES (?, ?, ?, ?, ?, ?)
                ''', emp)
            except:
                pass
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        st.error(f"Error crítico al inicializar la base de datos: {str(e)}")
        return False


def check_database_tables():
    """Verifica si todas las tablas necesarias existen"""
    try:
        conn = get_connection()
        if not conn:
            return False
            
        c = conn.cursor()
        
        # Lista de tablas requeridas
        required_tables = ['roles', 'usuarios', 'empleados']
        
        # Verificar cada tabla
        for table in required_tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not c.fetchone():
                conn.close()
                return False
        
        # Verificar que haya datos en roles
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            conn.close()
            return False
        
        # Verificar que haya usuario admin
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
        if c.fetchone()[0] == 0:
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error verificando tablas: {str(e)}")
        return False


def force_database_initialization():
    """Fuerza la inicialización de la base de datos"""
    with st.spinner("🔄 Inicializando base de datos..."):
        success = initialize_database()
        if success:
            st.success("✅ Base de datos inicializada correctamente!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Error al inicializar la base de datos")
            return False
    return success

# =============================================================================
# AUTENTICACIÓN
# =============================================================================
def authenticate(username, password):
    """Autentica un usuario"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        c = conn.cursor()
        c.execute('''
        SELECT u.*, r.nombre as rol_nombre, r.permisos 
        FROM usuarios u 
        JOIN roles r ON u.rol_id = r.id 
        WHERE u.username = ? AND u.activo = 1
        ''', (username,))
        
        user_data = c.fetchone()
        
        if user_data:
            # Verificar contraseña
            stored_hash = user_data['password_hash']
            salt = user_data['salt']
            input_hash, _ = hash_password(password, salt)
            
            if input_hash == stored_hash:
                return {
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'nombre': user_data['nombre'],
                    'rol': user_data['rol_nombre'],
                    'permisos': user_data['permisos']
                }
        
        return None
        
    except Exception as e:
        st.error(f"Error en autenticación: {str(e)}")
        return None
    finally:
        conn.close()


def has_permission(user, required_permission):
    """Verifica si el usuario tiene un permiso específico"""
    if not user:
        return False
    
    if user['rol'] == 'admin':
        return True
    
    user_permissions = user.get('permisos', '')
    return required_permission in user_permissions.split(',')

# =============================================================================
# FUNCIONES DE EMPLEADOS
# =============================================================================
def get_employees():
    """Obtiene todos los empleados"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = '''
        SELECT id, codigo, nombre, cargo, area, telefono, email, activo,
               DATE(fecha_ingreso) as fecha_ingreso_formatted
        FROM empleados 
        ORDER BY nombre
        '''
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error obteniendo empleados: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()


def create_employee(codigo, nombre, cargo, area, telefono, email):
    """Crea un nuevo empleado"""
    conn = get_connection()
    if not conn:
        return False, "Error de conexión"
    
    try:
        c = conn.cursor()
        c.execute('''
        INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (codigo, nombre, cargo, area, telefono, email))
        
        conn.commit()
        return True, "✅ Empleado creado exitosamente"
    except sqlite3.IntegrityError:
        return False, "❌ El código ya existe"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
    finally:
        conn.close()


def update_employee(empleado_id, codigo, nombre, cargo, area, telefono, email):
    """Actualiza un empleado existente"""
    conn = get_connection()
    if not conn:
        return False, "Error de conexión"
    
    try:
        c = conn.cursor()
        c.execute('''
        UPDATE empleados 
        SET codigo = ?, nombre = ?, cargo = ?, area = ?, telefono = ?, email = ?
        WHERE id = ?
        ''', (codigo, nombre, cargo, area, telefono, email, empleado_id))
        
        conn.commit()
        return True, "✅ Empleado actualizado exitosamente"
    except sqlite3.IntegrityError:
        return False, "❌ El código ya existe"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
    finally:
        conn.close()


def delete_employee(empleado_id):
    """Desactiva un empleado (soft delete)"""
    conn = get_connection()
    if not conn:
        return False, "Error de conexión"
    
    try:
        c = conn.cursor()
        c.execute('UPDATE empleados SET activo = 0 WHERE id = ?', (empleado_id,))
        conn.commit()
        return True, "✅ Empleado desactivado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
    finally:
        conn.close()


def get_employee_by_id(empleado_id):
    """Obtiene un empleado por su ID"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM empleados WHERE id = ?', (empleado_id,))
        empleado = c.fetchone()
        return dict(empleado) if empleado else None
    except Exception as e:
        st.error(f"Error obteniendo empleado: {str(e)}")
        return None
    finally:
        conn.close()

# =============================================================================
# PANTALLA DE LOGIN
# =============================================================================
def show_login():
    """Muestra la pantalla de inicio de sesión"""
    st.markdown("""
    <div class="main-header">
        <h1>🏥 Sistema de Gestión - Droguería Restrepo</h1>
        <p>Control de Inventario y Ventas</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Inicio de Sesión")
        
        # Información de acceso
        with st.expander("📋 Credenciales de acceso"):
            st.info("""
            **Usuario:** admin  
            **Contraseña:** admin123
            
            *Nota: Esta es la cuenta de administrador por defecto.*
            """)
        
        # Formulario de login
        username = st.text_input("👤 Usuario", value="admin", key="login_username")
        password = st.text_input("🔒 Contraseña", type="password", value="admin123", key="login_password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🚀 **Iniciar Sesión**", use_container_width=True, type="primary"):
                if username and password:
                    with st.spinner("Verificando credenciales..."):
                        user = authenticate(username, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.page = "inicio"
                            st.success(f"✅ Bienvenido, {user['nombre']}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Usuario o contraseña incorrectos")
                else:
                    st.warning("⚠️ Por favor ingrese usuario y contraseña")
        
        with col_btn2:
            if st.button("🔄 **Reiniciar Sistema**", use_container_width=True, type="secondary"):
                st.warning("⚠️ Esta acción eliminará todos los datos y reiniciará el sistema.")
                if st.checkbox("Confirmar reinicio"):
                    if force_database_initialization():
                        st.success("✅ Sistema reiniciado correctamente")
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# PANTALLA PRINCIPAL
# =============================================================================
def main_app():
    """Aplicación principal después del login"""
    user = st.session_state.user
    
    # =========================================================================
    # SIDEBAR
    # =========================================================================
    with st.sidebar:
        st.markdown(f"### 👤 {user['nombre']}")
        st.markdown(f"**Rol:** {user['rol'].capitalize()}")
        st.divider()
        
        # Menú de navegación
        st.markdown("### 📱 Navegación")
        
        if st.button("🏠 **Inicio**", use_container_width=True):
            st.session_state.page = "inicio"
            st.session_state.edit_employee_id = None
            st.rerun()
        
        if has_permission(user, "manage_employees"):
            if st.button("👥 **Gestión de Empleados**", use_container_width=True):
                st.session_state.page = "empleados"
                st.session_state.edit_employee_id = None
                st.rerun()
        
        st.divider()
        
        # Estadísticas rápidas
        try:
            conn = get_connection()
            if conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM empleados WHERE activo = 1")
                total_empleados = c.fetchone()[0]
                conn.close()
                
                st.markdown(f"**📊 Empleados activos:** {total_empleados}")
        except:
            st.markdown("**📊 Empleados activos:** N/A")
        
        st.divider()
        
        if st.button("🚪 **Cerrar Sesión**", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # =========================================================================
    # CONTENIDO PRINCIPAL
    # =========================================================================
    
    # PÁGINA DE INICIO
    if st.session_state.page == "inicio":
        st.title("🏠 Panel de Control")
        
        # Tarjetas de métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👤 Usuario Activo", user['nombre'], user['rol'])
        
        with col2:
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM empleados WHERE activo = 1")
                total_emp = c.fetchone()[0]
                conn.close()
                st.metric("👥 Empleados Activos", total_emp)
            except:
                st.metric("👥 Empleados Activos", "N/A")
        
        with col3:
            st.metric("✅ Sistema", "Operativo", "Estable")
        
        st.divider()
        
        # Bienvenida y funcionalidades
        st.markdown(f"### 👋 ¡Bienvenido, {user['nombre']}!")
        
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.info("""
            **Funcionalidades disponibles:**
            
            ✅ **Gestión de Empleados**
            - Agregar nuevos empleados
            - Editar información existente
            - Desactivar empleados
            - Ver lista completa
            
            ✅ **Sistema Seguro**
            - Autenticación con hash
            - Roles y permisos
            - Base de datos SQLite
            """)
        
        with col_info2:
            st.success("""
            **Accesos rápidos:**
            
            👥 **Gestión de Empleados**
            - Solo para administradores y gerentes
            - Acceso desde el menú lateral
            
            🔐 **Seguridad**
            - Contraseñas encriptadas
            - Sesiones seguras
            - Control de acceso
            
            📊 **Próximamente**
            - Gestión de ventas
            - Control de inventario
            - Reportes y estadísticas
            """)
    
    # PÁGINA DE GESTIÓN DE EMPLEADOS
    elif st.session_state.page == "empleados":
        if not has_permission(user, "manage_employees"):
            st.error("❌ No tienes permisos para acceder a esta sección")
            return
        
        st.title("👥 Gestión de Empleados")
        
        # Pestañas para diferentes funcionalidades
        tab_lista, tab_nuevo, tab_editar = st.tabs([
            "📋 Lista de Empleados", 
            "➕ Nuevo Empleado", 
            "✏️ Editar Empleado"
        ])
        
        # TAB 1: Lista de empleados
        with tab_lista:
            st.subheader("📋 Empleados Registrados")
            
            df_empleados = get_employees()
            
            if df_empleados.empty:
                st.warning("📭 No hay empleados registrados en el sistema.")
                st.info("Usa la pestaña '➕ Nuevo Empleado' para agregar el primero.")
            else:
                # Filtrar empleados activos
                df_activos = df_empleados[df_empleados['activo'] == 1]
                df_inactivos = df_empleados[df_empleados['activo'] == 0]
                
                # Mostrar empleados activos
                if not df_activos.empty:
                    st.markdown(f"**Empleados activos ({len(df_activos)}):**")
                    
                    # Formatear dataframe para mostrar
                    display_df = df_activos[['codigo', 'nombre', 'cargo', 'area', 'telefono', 'email']].copy()
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'codigo': 'Código',
                            'nombre': 'Nombre',
                            'cargo': 'Cargo',
                            'area': 'Área',
                            'telefono': 'Teléfono',
                            'email': 'Email'
                        }
                    )
                else:
                    st.warning("⚠️ No hay empleados activos en el sistema.")
                
                # Mostrar estadísticas
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Total", len(df_empleados))
                with col_stat2:
                    st.metric("Activos", len(df_activos))
                with col_stat3:
                    st.metric("Inactivos", len(df_inactivos))
                
                # Opciones de acción
                if not df_activos.empty:
                    st.subheader("⚙️ Acciones")
                    
                    empleados_activos = df_activos[['id', 'codigo', 'nombre']].to_dict('records')
                    
                    col_act1, col_act2 = st.columns(2)
                    
                    with col_act1:
                        empleado_seleccionado = st.selectbox(
                            "Seleccionar empleado para editar:",
                            options=empleados_activos,
                            format_func=lambda x: f"{x['codigo']} - {x['nombre']}",
                            key="select_empleado_lista"
                        )
                        
                        if empleado_seleccionado and st.button(
                            "✏️ **Editar Empleado**", 
                            use_container_width=True,
                            key="btn_editar_lista"
                        ):
                            st.session_state.edit_employee_id = empleado_seleccionado['id']
                            st.rerun()
                    
                    with col_act2:
                        if empleado_seleccionado:
                            if st.button(
                                "🗑️ **Desactivar Empleado**", 
                                use_container_width=True,
                                type="secondary",
                                key="btn_desactivar_lista"
                            ):
                                st.warning(f"⚠️ ¿Desactivar a {empleado_seleccionado['nombre']}?")
                                col_conf1, col_conf2 = st.columns(2)
                                with col_conf1:
                                    if st.button("✅ Sí, desactivar", use_container_width=True):
                                        with st.spinner("Desactivando empleado..."):
                                            success, message = delete_employee(empleado_seleccionado['id'])
                                            if success:
                                                st.success(message)
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error(message)
                                with col_conf2:
                                    if st.button("❌ Cancelar", use_container_width=True):
                                        st.rerun()
        
        # TAB 2: Nuevo empleado
        with tab_nuevo:
            st.subheader("➕ Registrar Nuevo Empleado")
            
            with st.form("form_nuevo_empleado", clear_on_submit=True):
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    codigo = st.text_input(
                        "🔢 **Código** *", 
                        placeholder="Ej: EMP006",
                        help="Código único del empleado",
                        max_chars=20
                    )
                    nombre = st.text_input(
                        "👤 **Nombre Completo** *", 
                        placeholder="Ej: Laura Sánchez",
                        help="Nombre completo del empleado",
                        max_chars=100
                    )
                    cargo = st.text_input(
                        "💼 **Cargo** *", 
                        placeholder="Ej: Auxiliar de Farmacia",
                        help="Cargo o posición del empleado",
                        max_chars=50
                    )
                
                with col_f2:
                    area = st.text_input(
                        "🏢 **Área/Departamento** *", 
                        placeholder="Ej: Farmacia",
                        help="Área o departamento donde trabaja",
                        max_chars=50
                    )
                    telefono = st.text_input(
                        "📱 **Teléfono**", 
                        placeholder="Ej: 3001234567",
                        help="Número de contacto",
                        max_chars=15
                    )
                    email = st.text_input(
                        "📧 **Email**", 
                        placeholder="Ej: laura@empresa.com",
                        help="Correo electrónico",
                        max_chars=100
                    )
                
                st.markdown("(*) Campos obligatorios")
                
                submitted = st.form_submit_button(
                    "💾 **Guardar Empleado**", 
                    type="primary", 
                    use_container_width=True
                )
                
                if submitted:
                    if not all([codigo.strip(), nombre.strip(), cargo.strip(), area.strip()]):
                        st.error("❌ Por favor complete todos los campos obligatorios (*)")
                    else:
                        with st.spinner("Guardando empleado..."):
                            success, message = create_employee(
                                codigo.strip(),
                                nombre.strip(),
                                cargo.strip(),
                                area.strip(),
                                telefono.strip(),
                                email.strip()
                            )
                            if success:
                                st.success(message)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(message)
        
        # TAB 3: Editar empleado
        with tab_editar:
            st.subheader("✏️ Editar Empleado Existente")
            
            if st.session_state.get('edit_employee_id'):
                empleado_id = st.session_state.edit_employee_id
                empleado_data = get_employee_by_id(empleado_id)
                
                if empleado_data:
                    with st.form("form_editar_empleado"):
                        st.markdown(f"**Editando:** {empleado_data['nombre']} ({empleado_data['codigo']})")
                        
                        col_e1, col_e2 = st.columns(2)
                        
                        with col_e1:
                            codigo = st.text_input(
                                "🔢 **Código** *", 
                                value=empleado_data['codigo'],
                                max_chars=20
                            )
                            nombre = st.text_input(
                                "👤 **Nombre Completo** *", 
                                value=empleado_data['nombre'],
                                max_chars=100
                            )
                            cargo = st.text_input(
                                "💼 **Cargo** *", 
                                value=empleado_data['cargo'],
                                max_chars=50
                            )
                        
                        with col_e2:
                            area = st.text_input(
                                "🏢 **Área/Departamento** *", 
                                value=empleado_data['area'],
                                max_chars=50
                            )
                            telefono = st.text_input(
                                "📱 **Teléfono**", 
                                value=empleado_data['telefono'] or "",
                                max_chars=15
                            )
                            email = st.text_input(
                                "📧 **Email**", 
                                value=empleado_data['email'] or "",
                                max_chars=100
                            )
                        
                        st.markdown("(*) Campos obligatorios")
                        
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        
                        with col_btn1:
                            submitted = st.form_submit_button(
                                "💾 **Guardar Cambios**", 
                                type="primary", 
                                use_container_width=True
                            )
                        with col_btn2:
                            cancel = st.form_submit_button(
                                "❌ **Cancelar**", 
                                type="secondary", 
                                use_container_width=True
                            )
                        
                        if cancel:
                            st.session_state.edit_employee_id = None
                            st.rerun()
                        
                        if submitted:
                            if not all([codigo.strip(), nombre.strip(), cargo.strip(), area.strip()]):
                                st.error("❌ Por favor complete todos los campos obligatorios (*)")
                            else:
                                with st.spinner("Actualizando información..."):
                                    success, message = update_employee(
                                        empleado_id,
                                        codigo.strip(),
                                        nombre.strip(),
                                        cargo.strip(),
                                        area.strip(),
                                        telefono.strip(),
                                        email.strip()
                                    )
                                    if success:
                                        st.success(message)
                                        st.session_state.edit_employee_id = None
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(message)
                else:
                    st.error("❌ No se pudo cargar la información del empleado")
                    st.session_state.edit_employee_id = None
            else:
                st.info("ℹ️ Selecciona un empleado para editar en la pestaña '📋 Lista de Empleados'")

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal que controla el flujo de la aplicación"""
    
    # Inicializar variables de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = "inicio"
    if 'edit_employee_id' not in st.session_state:
        st.session_state.edit_employee_id = None
    
    # Verificar e inicializar base de datos
    if not check_database_tables():
        st.warning("⚠️ La base de datos necesita ser inicializada...")
        
        col_init1, col_init2, col_init3 = st.columns([1, 2, 1])
        with col_init2:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.markdown("### 🔧 Configuración Inicial")
            st.info("""
            Es la primera vez que ejecutas el sistema o la base de datos está corrupta.
            
            **Se crearán:**
            - Tablas de usuarios, roles y empleados
            - Usuario administrador (admin/admin123)
            - Empleados de ejemplo
            """)
            
            if st.button("🔄 **Inicializar Base de Datos**", use_container_width=True, type="primary"):
                if force_database_initialization():
                    st.success("✅ Base de datos inicializada correctamente!")
                    st.info("Por favor, recarga la página para continuar.")
                else:
                    st.error("❌ Error al inicializar la base de datos")
            
            st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Mostrar login si no está autenticado
    if not st.session_state.authenticated:
        show_login()
        return
    
    # Mostrar aplicación principal
    main_app()

# =============================================================================
# EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    main()