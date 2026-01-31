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

    conn.commit()
    conn.close()


def check_database_ready():
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        ok = c.fetchone() is not None
        conn.close()
        return ok
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
    df = pd.read_sql("SELECT * FROM empleados ORDER BY nombre", conn)
    conn.close()
    return df


def create_employee(codigo, nombre, cargo, area, telefono, email):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
        INSERT INTO empleados (codigo, nombre, cargo, area, telefono, email)
        VALUES (?,?,?,?,?,?)
        """, (codigo, nombre, cargo, area, telefono, email))
        conn.commit()
        return True
    except:
        return False
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
            st.rerun()

        if has_permission(user, "manage_employees"):
            if st.button("👥 Empleados"):
                st.session_state.page = "empleados"
                st.rerun()

        if st.button("🚪 Cerrar sesión"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    # CONTENIDO
    if st.session_state.page == "inicio":
        st.title("🏠 Panel Principal")
        st.success("Sistema funcionando correctamente ✅")

    if st.session_state.page == "empleados":
        st.title("👥 Gestión de Empleados")

        df = get_employees()
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("➕ Nuevo empleado")

        with st.form("nuevo"):
            codigo = st.text_input("Código")
            nombre = st.text_input("Nombre")
            cargo = st.text_input("Cargo")
            area = st.text_input("Área")
            telefono = st.text_input("Teléfono")
            email = st.text_input("Email")
            if st.form_submit_button("Guardar"):
                if create_employee(codigo, nombre, cargo, area, telefono, email):
                    st.success("Empleado creado")
                    st.rerun()
                else:
                    st.error("Error al crear empleado")

# =============================================================================
# EJECUCIÓN
# =============================================================================
if __name__ == "__main__":
    main()
