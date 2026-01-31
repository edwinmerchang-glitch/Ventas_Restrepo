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
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt


def initialize_database():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        permisos TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        nombre TEXT,
        password_hash TEXT,
        salt TEXT,
        rol_id INTEGER,
        activo INTEGER DEFAULT 1
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        nombre TEXT,
        cargo TEXT,
        area TEXT,
        telefono TEXT,
        email TEXT,
        activo INTEGER DEFAULT 1,
        fecha_ingreso DATE DEFAULT CURRENT_DATE
    )
    """)

    # Roles
    c.execute("SELECT COUNT(*) FROM roles")
    if c.fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO roles (nombre, permisos) VALUES (?,?)",
            [
                ("admin", "all"),
                ("gerente", "manage_employees"),
                ("vendedor", "read")
            ]
        )

    # Usuario admin
    c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id FROM roles WHERE nombre='admin'")
        rol_id = c.fetchone()[0]
        pwd, salt = hash_password("admin123")
        c.execute("""
        INSERT INTO usuarios (username, nombre, password_hash, salt, rol_id)
        VALUES (?,?,?,?,?)
        """, ("admin", "Administrador", pwd, salt, rol_id))

    # Verificar y crear empleados de ejemplo si está vacío
    c.execute("SELECT COUNT(*) FROM empleados")
    if c.fetchone()[0] == 0:
        c.executemany(
            """INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email) 
            VALUES (?,?,?,?,?,?)""",
            [
                ("EMP001", "Juan Pérez", "Vendedor", "Ventas", "3001234567", "juan@empresa.com"),
                ("EMP002", "María Gómez", "Gerente", "Administración", "3109876543", "maria@empresa.com"),
                ("EMP003", "Carlos López", "Farmacéutico", "Farmacia", "3204567890", "carlos@empresa.com")
            ]
        )

    conn.commit()
    conn.close()


def check_database_ready():
    try:
        conn = get_connection()
        c = conn.cursor()
        # Verificar que existan las tres tablas principales
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('usuarios', 'roles', 'empleados')")
        tables = c.fetchall()
        conn.close()
        return len(tables) == 3
    except:
        return False

# =============================================================================
# AUTENTICACIÓN
# =============================================================================
def authenticate(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT u.*, r.nombre AS rol, r.permisos
    FROM usuarios u
    JOIN roles r ON u.rol_id = r.id
    WHERE u.username=? AND u.activo=1
    """, (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        return None

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


def has_permission(user, perm):
    if not user:
        return False
    return user["rol"] == "admin" or perm in user["permisos"]

# =============================================================================
# EMPLEADOS
# =============================================================================
def get_employees():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM empleados ORDER BY nombre", conn)
        return df
    except Exception as e:
        st.error(f"Error al cargar empleados: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def create_employee(codigo, nombre, cargo, area, telefono, email):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
        INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email)
        VALUES (?,?,?,?,?,?)
        """, (codigo, nombre, cargo, area, telefono, email))
        conn.commit()
        return True, "Empleado creado exitosamente"
    except sqlite3.IntegrityError:
        return False, "El código ya existe"
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()


def update_employee(empleado_id, codigo, nombre, cargo, area, telefono, email):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
        UPDATE empleados 
        SET codigo=?, nombre=?, cargo=?, area=?, telefono=?, email=?
        WHERE id=?
        """, (codigo, nombre, cargo, area, telefono, email, empleado_id))
        conn.commit()
        return True, "Empleado actualizado exitosamente"
    except sqlite3.IntegrityError:
        return False, "El código ya existe"
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()


def delete_employee(empleado_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE empleados SET activo=0 WHERE id=?", (empleado_id,))
        conn.commit()
        return True, "Empleado desactivado exitosamente"
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()

# =============================================================================
# LOGIN
# =============================================================================
def show_login():
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Droguería Restrepo</h1>
        <p>Inicio de sesión</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        user = st.text_input("Usuario", value="admin")
        pwd = st.text_input("Contraseña", type="password", value="admin123")
        if st.button("Ingresar", use_container_width=True):
            u = authenticate(user, pwd)
            if u:
                st.session_state.authenticated = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# APP PRINCIPAL
# =============================================================================
def main():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "inicio")
    st.session_state.setdefault("edit_employee_id", None)

    # Inicializar BD SIEMPRE
    if not check_database_ready():
        initialize_database()

    if not st.session_state.authenticated:
        show_login()
        return

    user = st.session_state.user

    # SIDEBAR
    with st.sidebar:
        st.markdown(f"### 👤 {user['nombre']}")
        st.write(f"Rol: **{user['rol']}**")

        if st.button("🏠 Inicio"):
            st.session_state.page = "inicio"
            st.session_state.edit_employee_id = None
            st.rerun()

        if has_permission(user, "manage_employees"):
            if st.button("👥 Empleados"):
                st.session_state.page = "empleados"
                st.session_state.edit_employee_id = None
                st.rerun()

        if st.button("🚪 Cerrar sesión"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.edit_employee_id = None
            st.rerun()

    # CONTENIDO
    if st.session_state.page == "inicio":
        st.title("🏠 Panel Principal")
        st.success("Sistema funcionando correctamente ✅")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Usuarios activos", "1")
        with col2:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM empleados WHERE activo=1")
            count = c.fetchone()[0]
            conn.close()
            st.metric("Empleados activos", count)
        with col3:
            st.metric("Sistema", "Operativo")

    if st.session_state.page == "empleados":
        st.title("👥 Gestión de Empleados")

        # Pestañas para diferentes funcionalidades
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Empleados", "➕ Nuevo Empleado", "✏️ Editar Empleado"])
        
        with tab1:
            df = get_employees()
            
            if df.empty:
                st.info("No hay empleados registrados. Agrega el primero en la pestaña 'Nuevo Empleado'.")
            else:
                # Mostrar solo empleados activos
                df_activos = df[df['activo'] == 1]
                st.dataframe(df_activos, use_container_width=True, hide_index=True)
                
                # Opciones de edición/eliminación
                st.subheader("Acciones")
                col1, col2 = st.columns(2)
                
                with col1:
                    empleados_list = df_activos[['id', 'nombre', 'codigo']].to_dict('records')
                    if empleados_list:
                        empleado_seleccionado = st.selectbox(
                            "Seleccionar empleado para editar",
                            options=empleados_list,
                            format_func=lambda x: f"{x['codigo']} - {x['nombre']}"
                        )
                        
                        if empleado_seleccionado and st.button("✏️ Editar empleado"):
                            st.session_state.edit_employee_id = empleado_seleccionado['id']
                            st.rerun()
                
                with col2:
                    if empleados_list and st.button("🗑️ Desactivar empleado", type="secondary"):
                        empleado_seleccionado = empleados_list[0] if empleados_list else None
                        if empleado_seleccionado:
                            if st.warning(f"¿Estás seguro de desactivar a {empleado_seleccionado['nombre']}?"):
                                success, message = delete_employee(empleado_seleccionado['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
        
        with tab2:
            st.subheader("➕ Nuevo empleado")
            
            with st.form("nuevo_empleado_form"):
                codigo = st.text_input("Código *", placeholder="Ej: EMP001")
                nombre = st.text_input("Nombre completo *", placeholder="Ej: Juan Pérez")
                cargo = st.text_input("Cargo *", placeholder="Ej: Vendedor")
                area = st.text_input("Área/Dpto *", placeholder="Ej: Ventas")
                telefono = st.text_input("Teléfono", placeholder="Ej: 3001234567")
                email = st.text_input("Email", placeholder="Ej: empleado@empresa.com")
                
                submitted = st.form_submit_button("✅ Guardar empleado")
                
                if submitted:
                    if not all([codigo, nombre, cargo, area]):
                        st.error("Por favor complete todos los campos obligatorios (*)")
                    else:
                        success, message = create_employee(codigo, nombre, cargo, area, telefono, email)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        
        with tab3:
            st.subheader("✏️ Editar empleado")
            
            if st.session_state.edit_employee_id:
                # Obtener datos del empleado a editar
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM empleados WHERE id=?", (st.session_state.edit_employee_id,))
                empleado = c.fetchone()
                conn.close()
                
                if empleado:
                    with st.form("editar_empleado_form"):
                        codigo = st.text_input("Código *", value=empleado['codigo'])
                        nombre = st.text_input("Nombre completo *", value=empleado['nombre'])
                        cargo = st.text_input("Cargo *", value=empleado['cargo'])
                        area = st.text_input("Área/Dpto *", value=empleado['area'])
                        telefono = st.text_input("Teléfono", value=empleado['telefono'] or "")
                        email = st.text_input("Email", value=empleado['email'] or "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            submitted = st.form_submit_button("💾 Guardar cambios")
                        with col2:
                            cancel = st.form_submit_button("❌ Cancelar", type="secondary")
                        
                        if cancel:
                            st.session_state.edit_employee_id = None
                            st.rerun()
                        
                        if submitted:
                            if not all([codigo, nombre, cargo, area]):
                                st.error("Por favor complete todos los campos obligatorios (*)")
                            else:
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
                    st.warning("Empleado no encontrado")
                    st.session_state.edit_employee_id = None
            else:
                st.info("Selecciona un empleado para editar en la pestaña 'Lista de Empleados'")

# =============================================================================
# EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    main()