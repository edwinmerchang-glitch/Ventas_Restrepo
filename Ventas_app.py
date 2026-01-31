# app.py - Sistema de Gestión Droguería Restrepo (ESTABLE STREAMLIT CLOUD)

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
import os
import time
from datetime import date, datetime

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


def verify_database_structure():
    """Verifica que todas las tablas y columnas existan"""
    try:
        conn = get_connection()
        if not conn:
            return False, "No se pudo conectar a la base de datos"
        
        c = conn.cursor()
        
        # Verificar tabla roles
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roles'")
        if not c.fetchone():
            conn.close()
            return False, "Tabla 'roles' no existe"
        
        # Verificar tabla usuarios
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if not c.fetchone():
            conn.close()
            return False, "Tabla 'usuarios' no existe"
        
        # Verificar tabla empleados
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='empleados'")
        if not c.fetchone():
            conn.close()
            return False, "Tabla 'empleados' no existe"
        
        # Verificar columnas de usuarios
        c.execute("PRAGMA table_info(usuarios)")
        user_columns = [col[1] for col in c.fetchall()]
        required_user_columns = ['id', 'username', 'nombre', 'password_hash', 'salt', 'rol_id', 'activo']
        
        missing_user_columns = set(required_user_columns) - set(user_columns)
        if missing_user_columns:
            conn.close()
            return False, f"Faltan columnas en 'usuarios': {missing_user_columns}"
        
        # Verificar columnas de empleados
        c.execute("PRAGMA table_info(empleados)")
        emp_columns = [col[1] for col in c.fetchall()]
        required_emp_columns = ['id', 'codigo', 'nombre', 'cargo', 'area', 'telefono', 'email', 'activo', 'fecha_ingreso']
        
        missing_emp_columns = set(required_emp_columns) - set(emp_columns)
        if missing_emp_columns:
            conn.close()
            return False, f"Faltan columnas en 'empleados': {missing_emp_columns}"
        
        conn.close()
        return True, "Estructura de base de datos correcta"
        
    except Exception as e:
        return False, f"Error verificando estructura: {str(e)}"


def create_database_from_scratch():
    """Crea la base de datos desde cero con la estructura correcta"""
    try:
        # Eliminar base de datos existente
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
            time.sleep(0.5)
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Tabla roles - versión simplificada
        c.execute('''
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            permisos TEXT
        )
        ''')
        
        # Insertar roles básicos
        roles = [
            ('admin', 'all'),
            ('gerente', 'manage_employees'),
            ('vendedor', 'view_own_data')
        ]
        c.executemany('INSERT INTO roles (nombre, permisos) VALUES (?, ?)', roles)
        
        # Tabla usuarios - versión simplificada
        c.execute('''
        CREATE TABLE usuarios (
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
        
        # Crear usuario admin
        admin_password = "admin123"
        password_hash, salt = hash_password(admin_password)
        c.execute('''
        INSERT INTO usuarios (username, nombre, password_hash, salt, rol_id)
        VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'Administrador', password_hash, salt, 1))
        
        # Tabla empleados - versión simplificada
        c.execute('''
        CREATE TABLE empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            telefono TEXT,
            email TEXT,
            activo INTEGER DEFAULT 1,
            fecha_ingreso DATE DEFAULT CURRENT_DATE
        )
        ''')
        
        # Insertar empleados de ejemplo
        empleados = [
            ('EMP001', 'Juan Pérez', 'Vendedor', 'Ventas', '3001234567', 'juan@empresa.com'),
            ('EMP002', 'María Gómez', 'Gerente', 'Administración', '3109876543', 'maria@empresa.com'),
            ('EMP003', 'Carlos López', 'Farmacéutico', 'Farmacia', '3204567890', 'carlos@empresa.com')
        ]
        c.executemany('''
        INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', empleados)
        
        conn.commit()
        conn.close()
        
        return True, "Base de datos creada exitosamente"
        
    except Exception as e:
        return False, f"Error creando base de datos: {str(e)}"


def force_database_initialization():
    """Fuerza la inicialización completa de la base de datos"""
    with st.spinner("🔄 Creando base de datos desde cero..."):
        success, message = create_database_from_scratch()
        if success:
            st.success(f"✅ {message}")
            time.sleep(2)
            st.rerun()
        else:
            st.error(f"❌ {message}")
        return success

# =============================================================================
# AUTENTICACIÓN - VERSIÓN SIMPLIFICADA Y ROBUSTA
# =============================================================================
def authenticate_simple(username, password):
    """Autentica un usuario de forma segura y simple"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        c = conn.cursor()
        
        # Primero verificar si el usuario existe
        c.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        user_data = c.fetchone()
        
        if not user_data:
            return None
        
        # Convertir a diccionario de forma segura
        user_dict = {}
        if isinstance(user_data, sqlite3.Row):
            # Si es un Row, convertir a dict
            user_dict = dict(user_data)
        else:
            # Si es una tupla, crear dict manualmente
            columns = ['id', 'username', 'nombre', 'password_hash', 'salt', 'rol_id', 'activo']
            for i, col in enumerate(columns):
                if i < len(user_data):
                    user_dict[col] = user_data[i]
        
        # Verificar contraseña
        stored_hash = user_dict.get('password_hash')
        salt = user_dict.get('salt')
        
        if not stored_hash or not salt:
            return None
        
        input_hash, _ = hash_password(password, salt)
        
        if input_hash == stored_hash:
            # Obtener información del rol
            c.execute('SELECT nombre, permisos FROM roles WHERE id = ?', (user_dict['rol_id'],))
            rol_data = c.fetchone()
            
            if rol_data:
                rol_nombre = rol_data[0] if isinstance(rol_data, tuple) else rol_data['nombre']
                permisos = rol_data[1] if isinstance(rol_data, tuple) else rol_data['permisos']
                
                return {
                    'id': user_dict['id'],
                    'username': user_dict['username'],
                    'nombre': user_dict['nombre'],
                    'rol': rol_nombre,
                    'permisos': permisos
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
               fecha_ingreso
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
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return False, "❌ El código ya existe"
        return False, f"❌ Error de integridad: {str(e)}"
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
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return False, "❌ El código ya existe"
        return False, f"❌ Error de integridad: {str(e)}"
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
        row = c.fetchone()
        
        if row:
            # Convertir a diccionario de forma segura
            if isinstance(row, sqlite3.Row):
                return dict(row)
            else:
                columns = ['id', 'codigo', 'nombre', 'cargo', 'area', 'telefono', 'email', 'activo', 'fecha_ingreso']
                return {columns[i]: row[i] for i in range(len(columns)) if i < len(row)}
        return None
        
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
        <p>Sistema de Gestión de Empleados</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Inicio de Sesión")
        
        # Información de acceso
        with st.expander("📋 Credenciales de acceso por defecto"):
            st.info("""
            **Usuario:** admin  
            **Contraseña:** admin123
            
            *Estas credenciales se crean automáticamente al inicializar el sistema.*
            """)
        
        # Formulario de login
        username = st.text_input("👤 Usuario", value="admin", key="login_username")
        password = st.text_input("🔒 Contraseña", type="password", value="admin123", key="login_password")
        
        if st.button("🚀 **Iniciar Sesión**", use_container_width=True, type="primary"):
            if username and password:
                with st.spinner("Verificando credenciales..."):
                    user = authenticate_simple(username, password)
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
        
        st.markdown("---")
        
        # Opción para crear base de datos si no existe
        if st.button("🆕 **Crear Base de Datos desde Cero**", use_container_width=True, type="secondary"):
            st.warning("⚠️ Esta acción creará una nueva base de datos con datos de ejemplo.")
            if st.checkbox("Confirmar creación", key="confirm_create"):
                if force_database_initialization():
                    st.success("✅ Base de datos creada exitosamente")
                    st.info("Ahora puede iniciar sesión con usuario: admin, contraseña: admin123")
                else:
                    st.error("❌ Error al crear la base de datos")
        
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
                
                # Mostrar empleados activos
                if not df_activos.empty:
                    st.markdown(f"**Empleados activos ({len(df_activos)}):**")
                    
                    # Mostrar tabla
                    st.dataframe(
                        df_activos[['codigo', 'nombre', 'cargo', 'area', 'telefono', 'email']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("⚠️ No hay empleados activos en el sistema.")
                
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
                                    if st.button("✅ Sí, desactivar", use_container_width=True, key="confirm_desactivar"):
                                        with st.spinner("Desactivando empleado..."):
                                            success, message = delete_employee(empleado_seleccionado['id'])
                                            if success:
                                                st.success(message)
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error(message)
                                with col_conf2:
                                    if st.button("❌ Cancelar", use_container_width=True, key="cancel_desactivar"):
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
                        max_chars=20
                    )
                    nombre = st.text_input(
                        "👤 **Nombre Completo** *", 
                        placeholder="Ej: Laura Sánchez",
                        max_chars=100
                    )
                    cargo = st.text_input(
                        "💼 **Cargo** *", 
                        placeholder="Ej: Auxiliar de Farmacia",
                        max_chars=50
                    )
                
                with col_f2:
                    area = st.text_input(
                        "🏢 **Área/Departamento** *", 
                        placeholder="Ej: Farmacia",
                        max_chars=50
                    )
                    telefono = st.text_input(
                        "📱 **Teléfono**", 
                        placeholder="Ej: 3001234567",
                        max_chars=15
                    )
                    email = st.text_input(
                        "📧 **Email**", 
                        placeholder="Ej: laura@empresa.com",
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
                        
                        col_btn1, col_btn2 = st.columns(2)
                        
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