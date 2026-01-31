# app.py - Sistema de Gestión Droguería Restrepo (ESTABLE STREAMLIT CLOUD)

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
import os
from datetime import date

# =============================================================================
# CONFIGURACIÓN STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="Sistema de Unidades Vendidas Restrepo",
    page_icon="🏥",
    layout="wide"
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
</style>
""", unsafe_allow_html=True)

# =============================================================================
# BASE DE DATOS
# =============================================================================
def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt


def initialize_database():
    """Inicializa la base de datos y crea las tablas si no existen"""
    try:
        conn = get_connection()
        if conn is None:
            return False
            
        c = conn.cursor()

        # Tabla de roles
        c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            permisos TEXT
        )
        """)

        # Tabla de usuarios
        c.execute("""
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
        """)

        # Tabla de empleados
        c.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
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
        """)

        # Insertar roles básicos si no existen
        roles_existentes = c.execute("SELECT nombre FROM roles").fetchall()
        roles_existentes = [r[0] for r in roles_existentes]
        
        roles_base = [
            ("admin", "all"),
            ("gerente", "manage_employees"),
            ("vendedor", "read")
        ]
        
        for rol_nombre, permisos in roles_base:
            if rol_nombre not in roles_existentes:
                c.execute("INSERT INTO roles (nombre, permisos) VALUES (?, ?)", 
                         (rol_nombre, permisos))

        # Obtener ID del rol admin
        c.execute("SELECT id FROM roles WHERE nombre='admin'")
        rol_admin = c.fetchone()
        
        if rol_admin:
            rol_admin_id = rol_admin[0]
            
            # Crear usuario admin si no existe
            c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
            admin_exists = c.fetchone()[0]
            
            if admin_exists == 0:
                password_hash, salt = hash_password("admin123")
                c.execute("""
                INSERT INTO usuarios (username, nombre, password_hash, salt, rol_id)
                VALUES (?, ?, ?, ?, ?)
                """, ("admin", "Administrador", password_hash, salt, rol_admin_id))

        # Verificar si hay empleados, si no, crear algunos de ejemplo
        c.execute("SELECT COUNT(*) FROM empleados")
        if c.fetchone()[0] == 0:
            empleados_ejemplo = [
                ("EMP001", "Juan Pérez", "Vendedor", "Ventas", "3001234567", "juan@empresa.com"),
                ("EMP002", "María Gómez", "Gerente", "Administración", "3109876543", "maria@empresa.com"),
                ("EMP003", "Carlos López", "Farmacéutico", "Farmacia", "3204567890", "carlos@empresa.com")
            ]
            
            for emp in empleados_ejemplo:
                try:
                    c.execute("""
                    INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, emp)
                except sqlite3.IntegrityError:
                    continue

        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error inicializando base de datos: {e}")
        return False


def check_database_ready():
    """Verifica si la base de datos está lista"""
    try:
        conn = get_connection()
        if conn is None:
            return False
            
        c = conn.cursor()
        
        # Verificar que existan las tablas principales
        required_tables = ['usuarios', 'roles', 'empleados']
        existing_tables = []
        
        for table in required_tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if c.fetchone():
                existing_tables.append(table)
        
        conn.close()
        
        if len(existing_tables) == len(required_tables):
            return True
        else:
            st.warning(f"Faltan tablas: {set(required_tables) - set(existing_tables)}")
            return False
            
    except Exception as e:
        st.error(f"Error verificando base de datos: {e}")
        return False

# =============================================================================
# AUTENTICACIÓN
# =============================================================================
def authenticate(username, password):
    """Autentica un usuario"""
    conn = get_connection()
    if conn is None:
        return None
        
    try:
        c = conn.cursor()
        c.execute("""
        SELECT u.*, r.nombre AS rol, r.permisos
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.username = ? AND u.activo = 1
        """, (username,))
        
        user = c.fetchone()
        
        if not user:
            return None
            
        # Verificar contraseña
        check_hash, _ = hash_password(password, user["salt"])
        if check_hash == user["password_hash"]:
            return {
                "id": user["id"],
                "username": user["username"],
                "nombre": user["nombre"],
                "rol": user["rol"],
                "permisos": user["permisos"]
            }
        return None
        
    except Exception as e:
        st.error(f"Error en autenticación: {e}")
        return None
    finally:
        conn.close()


def has_permission(user, perm):
    """Verifica si un usuario tiene un permiso específico"""
    if not user:
        return False
    if user["rol"] == "admin":
        return True
    return perm in user.get("permisos", "")

# =============================================================================
# EMPLEADOS
# =============================================================================
def get_employees():
    """Obtiene todos los empleados"""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
        
    try:
        df = pd.read_sql("""
        SELECT id, codigo, nombre, cargo, area, telefono, email, activo, 
               DATE(fecha_ingreso) as fecha_ingreso
        FROM empleados 
        ORDER BY nombre
        """, conn)
        return df
    except Exception as e:
        st.error(f"Error al cargar empleados: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def create_employee(codigo, nombre, cargo, area, telefono, email):
    """Crea un nuevo empleado"""
    conn = get_connection()
    if conn is None:
        return False, "Error de conexión"
        
    try:
        c = conn.cursor()
        c.execute("""
        INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (codigo.strip(), nombre.strip(), cargo.strip(), area.strip(), telefono.strip(), email.strip()))
        
        conn.commit()
        return True, "✅ Empleado creado exitosamente"
        
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return False, "❌ El código ya existe"
        return False, f"❌ Error de integridad: {e}"
    except Exception as e:
        return False, f"❌ Error: {e}"
    finally:
        conn.close()


def update_employee(empleado_id, codigo, nombre, cargo, area, telefono, email):
    """Actualiza un empleado existente"""
    conn = get_connection()
    if conn is None:
        return False, "Error de conexión"
        
    try:
        c = conn.cursor()
        c.execute("""
        UPDATE empleados 
        SET codigo = ?, nombre = ?, cargo = ?, area = ?, telefono = ?, email = ?
        WHERE id = ?
        """, (codigo.strip(), nombre.strip(), cargo.strip(), area.strip(), telefono.strip(), email.strip(), empleado_id))
        
        conn.commit()
        return True, "✅ Empleado actualizado exitosamente"
        
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return False, "❌ El código ya existe"
        return False, f"❌ Error de integridad: {e}"
    except Exception as e:
        return False, f"❌ Error: {e}"
    finally:
        conn.close()


def delete_employee(empleado_id):
    """Desactiva un empleado (soft delete)"""
    conn = get_connection()
    if conn is None:
        return False, "Error de conexión"
        
    try:
        c = conn.cursor()
        c.execute("UPDATE empleados SET activo = 0 WHERE id = ?", (empleado_id,))
        conn.commit()
        return True, "✅ Empleado desactivado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {e}"
    finally:
        conn.close()

# =============================================================================
# LOGIN
# =============================================================================
def show_login():
    """Muestra la pantalla de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Gestión - Droguería Restrepo</h1>
        <p>Inicio de sesión</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Iniciar Sesión")
        
        # Información de acceso predeterminado
        with st.expander("ℹ️ Información de acceso"):
            st.info("""
            **Usuario:** admin  
            **Contraseña:** admin123  
            
            Este es el usuario administrador predeterminado.
            """)
        
        user = st.text_input("**Usuario**", value="admin", key="login_user")
        pwd = st.text_input("**Contraseña**", type="password", value="admin123", key="login_pwd")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚪 **Ingresar**", use_container_width=True, type="primary"):
                if not user or not pwd:
                    st.error("Por favor ingrese usuario y contraseña")
                else:
                    with st.spinner("Verificando credenciales..."):
                        u = authenticate(user, pwd)
                        if u:
                            st.session_state.authenticated = True
                            st.session_state.user = u
                            st.rerun()
                        else:
                            st.error("❌ Credenciales incorrectas")
        
        with col_btn2:
            if st.button("🔄 **Reiniciar BD**", use_container_width=True, type="secondary"):
                try:
                    if os.path.exists(DB_NAME):
                        os.remove(DB_NAME)
                        st.success("Base de datos reiniciada. Recargue la página.")
                    else:
                        st.info("No existe base de datos previa.")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# APP PRINCIPAL
# =============================================================================
def main():
    """Función principal de la aplicación"""
    
    # Inicializar estado de sesión
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "inicio"
    if "edit_employee_id" not in st.session_state:
        st.session_state.edit_employee_id = None
    
    # Inicializar base de datos SIEMPRE al inicio
    st.info("🔧 Inicializando sistema...")
    if not check_database_ready():
        success = initialize_database()
        if success:
            st.success("✅ Base de datos inicializada correctamente")
            st.rerun()
        else:
            st.error("❌ Error al inicializar la base de datos")
            return
    
    # Mostrar login si no está autenticado
    if not st.session_state.authenticated:
        show_login()
        return
    
    # Obtener usuario actual
    user = st.session_state.user
    
    # =========================================================================
    # SIDEBAR
    # =========================================================================
    with st.sidebar:
        st.markdown(f"### 👤 {user['nombre']}")
        st.markdown(f"**Rol:** {user['rol']}")
        st.divider()
        
        # Navegación
        st.markdown("### 📱 Navegación")
        
        if st.button("🏠 **Inicio**", use_container_width=True):
            st.session_state.page = "inicio"
            st.session_state.edit_employee_id = None
            st.rerun()
        
        if has_permission(user, "manage_employees"):
            if st.button("👥 **Empleados**", use_container_width=True):
                st.session_state.page = "empleados"
                st.session_state.edit_employee_id = None
                st.rerun()
        
        st.divider()
        
        if st.button("🚪 **Cerrar sesión**", use_container_width=True, type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.page = "inicio"
            st.session_state.edit_employee_id = None
            st.rerun()
    
    # =========================================================================
    # CONTENIDO PRINCIPAL
    # =========================================================================
    
    # PÁGINA DE INICIO
    if st.session_state.page == "inicio":
        st.title("🏠 Panel Principal")
        
        # Mostrar métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👤 Usuarios activos", "1", "Sistema")
        
        with col2:
            try:
                conn = get_connection()
                if conn:
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM empleados WHERE activo = 1")
                    count = c.fetchone()[0]
                    conn.close()
                    st.metric("👥 Empleados activos", count, "Registrados")
                else:
                    st.metric("👥 Empleados activos", "Error", "Conexión")
            except:
                st.metric("👥 Empleados activos", "N/A", "Error")
        
        with col3:
            st.metric("✅ Sistema", "Operativo", "Estable")
        
        st.divider()
        
        # Información del sistema
        st.markdown("### 📊 Información del Sistema")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.info("""
            **Funcionalidades disponibles:**
            - ✅ Gestión de usuarios
            - ✅ Gestión de empleados
            - ✅ Autenticación segura
            - ✅ Base de datos SQLite
            """)
        
        with info_col2:
            st.success("""
            **Acceso rápido:**
            - 👤 Usuario: admin
            - 🔐 Contraseña: admin123
            - 👥 Empleados: Ver sección correspondiente
            """)
    
    # PÁGINA DE EMPLEADOS
    elif st.session_state.page == "empleados":
        st.title("👥 Gestión de Empleados")
        
        # Verificar permisos
        if not has_permission(user, "manage_employees"):
            st.error("❌ No tienes permisos para gestionar empleados")
            return
        
        # Pestañas
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Empleados", "➕ Nuevo Empleado", "✏️ Editar Empleado"])
        
        # TAB 1: Lista de empleados
        with tab1:
            st.subheader("📋 Empleados Registrados")
            
            df = get_employees()
            
            if df.empty:
                st.info("📭 No hay empleados registrados. Agrega el primero en la pestaña 'Nuevo Empleado'.")
            else:
                # Filtrar solo activos
                df_activos = df[df['activo'] == 1]
                
                if df_activos.empty:
                    st.warning("⚠️ Todos los empleados están desactivados.")
                else:
                    # Mostrar tabla
                    st.dataframe(
                        df_activos[['codigo', 'nombre', 'cargo', 'area', 'telefono', 'email', 'fecha_ingreso']],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Estadísticas
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("Total empleados", len(df))
                    with col_stat2:
                        st.metric("Activos", len(df_activos))
                    with col_stat3:
                        st.metric("Inactivos", len(df) - len(df_activos))
                
                # Opciones de acción
                st.subheader("⚙️ Acciones")
                
                if not df_activos.empty:
                    # Seleccionar empleado para acciones
                    empleados_opciones = df_activos[['id', 'codigo', 'nombre']].to_dict('records')
                    
                    col_act1, col_act2 = st.columns(2)
                    
                    with col_act1:
                        empleado_seleccionado = st.selectbox(
                            "Seleccionar empleado:",
                            options=empleados_opciones,
                            format_func=lambda x: f"{x['codigo']} - {x['nombre']}",
                            key="select_empleado_edit"
                        )
                        
                        if empleado_seleccionado and st.button("✏️ **Editar empleado**", use_container_width=True):
                            st.session_state.edit_employee_id = empleado_seleccionado['id']
                            st.rerun()
                    
                    with col_act2:
                        if empleado_seleccionado and st.button("🗑️ **Desactivar empleado**", 
                                                             use_container_width=True, 
                                                             type="secondary"):
                            with st.spinner("Desactivando..."):
                                success, message = delete_employee(empleado_seleccionado['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
        
        # TAB 2: Nuevo empleado
        with tab2:
            st.subheader("➕ Registrar Nuevo Empleado")
            
            with st.form("form_nuevo_empleado", clear_on_submit=True):
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    codigo = st.text_input("Código *", placeholder="EMP001", max_chars=20)
                    nombre = st.text_input("Nombre completo *", placeholder="Juan Pérez", max_chars=100)
                    cargo = st.text_input("Cargo *", placeholder="Vendedor", max_chars=50)
                
                with col_f2:
                    area = st.text_input("Área/Departamento *", placeholder="Ventas", max_chars=50)
                    telefono = st.text_input("Teléfono", placeholder="3001234567", max_chars=15)
                    email = st.text_input("Email", placeholder="empleado@empresa.com", max_chars=100)
                
                st.markdown("(*) Campos obligatorios")
                
                submitted = st.form_submit_button("💾 **Guardar Empleado**", type="primary", use_container_width=True)
                
                if submitted:
                    if not all([codigo, nombre, cargo, area]):
                        st.error("❌ Por favor complete todos los campos obligatorios (*)")
                    else:
                        with st.spinner("Guardando empleado..."):
                            success, message = create_employee(codigo, nombre, cargo, area, telefono, email)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
        
        # TAB 3: Editar empleado
        with tab3:
            st.subheader("✏️ Editar Empleado")
            
            if st.session_state.edit_employee_id:
                # Obtener datos del empleado
                conn = get_connection()
                if conn:
                    try:
                        c = conn.cursor()
                        c.execute("SELECT * FROM empleados WHERE id = ?", (st.session_state.edit_employee_id,))
                        empleado = c.fetchone()
                        
                        if empleado:
                            with st.form("form_editar_empleado"):
                                col_e1, col_e2 = st.columns(2)
                                
                                with col_e1:
                                    codigo = st.text_input("Código *", value=empleado['codigo'], max_chars=20)
                                    nombre = st.text_input("Nombre completo *", value=empleado['nombre'], max_chars=100)
                                    cargo = st.text_input("Cargo *", value=empleado['cargo'], max_chars=50)
                                
                                with col_e2:
                                    area = st.text_input("Área/Departamento *", value=empleado['area'], max_chars=50)
                                    telefono = st.text_input("Teléfono", value=empleado['telefono'] or "", max_chars=15)
                                    email = st.text_input("Email", value=empleado['email'] or "", max_chars=100)
                                
                                st.markdown("(*) Campos obligatorios")
                                
                                col_btn1, col_btn2, col_btn3 = st.columns(3)
                                
                                with col_btn1:
                                    submitted = st.form_submit_button("💾 **Guardar Cambios**", type="primary", use_container_width=True)
                                with col_btn2:
                                    cancel = st.form_submit_button("❌ **Cancelar**", type="secondary", use_container_width=True)
                                
                                if cancel:
                                    st.session_state.edit_employee_id = None
                                    st.rerun()
                                
                                if submitted:
                                    if not all([codigo, nombre, cargo, area]):
                                        st.error("❌ Por favor complete todos los campos obligatorios (*)")
                                    else:
                                        with st.spinner("Actualizando empleado..."):
                                            success, message = update_employee(
                                                st.session_state.edit_employee_id,
                                                codigo, nombre, cargo, area, telefono, email
                                            )
                                            if success:
                                                st.success(message)
                                                st.session_state.edit_employee_id = None
                                                st.rerun()
                                            else:
                                                st.error(message)
                        else:
                            st.warning("⚠️ Empleado no encontrado")
                            st.session_state.edit_employee_id = None
                            
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                    finally:
                        conn.close()
                else:
                    st.error("❌ Error de conexión a la base de datos")
                    st.session_state.edit_employee_id = None
            else:
                st.info("ℹ️ Selecciona un empleado para editar en la pestaña 'Lista de Empleados'")

# =============================================================================
# EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    main()