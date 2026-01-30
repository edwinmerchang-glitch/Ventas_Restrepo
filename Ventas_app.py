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

# CSS personalizado (mantenido igual)
st.markdown("""
<style>
    /* Estilos generales */
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        height: 100%;
        transition: transform 0.3s;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
    }
    
    .nav-button {
        width: 100%;
        margin: 0.3rem 0;
        padding: 0.5rem;
        text-align: left;
        border-radius: 5px;
        border: 1px solid #ddd;
        background: white;
        transition: all 0.2s;
    }
    
    .nav-button:hover {
        background: #f0f0f0;
    }
    
    .metric-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .product-item {
        background: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #667eea;
    }
    
    .total-box {
        background: #e8f5e9;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #4caf50;
        margin-top: 10px;
    }
    
    /* Estilos para autenticación */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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
    
    .role-inventario {
        background: #e3f2fd;
        color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SISTEMA DE AUTENTICACIÓN
# ============================================================================
def hash_password(password, salt=None):
    """Hash de contraseña con salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode('utf-8'))
    return hash_obj.hexdigest(), salt

def init_auth_database():
    """Inicializa las tablas de usuarios y roles"""
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
        
        # Insertar usuario admin por defecto si no existe
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if c.fetchone()[0] == 0:
            password_hash, salt = hash_password("admin123")
            c.execute("""
                INSERT INTO usuarios (username, nombre_completo, email, password_hash, salt, rol_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("admin", "Administrador Principal", "admin@drogueria.com", password_hash, salt, 1))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar autenticación: {e}")
        return False

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

def show_login():
    """Muestra la pantalla de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Gestión - Droguería Restrepo</h1>
        <h3>Iniciar Sesión</h3>
        <p>Acceso restringido al personal autorizado</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### 📝 Inicio de Sesión")
            
            with st.form("login_form"):
                username = st.text_input("Usuario", placeholder="Ingrese su nombre de usuario")
                password = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")
                
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
            
            st.divider()
            st.markdown("### ℹ️ Información")
            st.info("""
            **Credenciales por defecto:**
            - Usuario: `admin`
            - Contraseña: `admin123`
            
            **Nota:** Cambie estas credenciales después del primer inicio.
            """)
            
            st.markdown('</div>', unsafe_allow_html=True)

def show_user_management():
    """Gestión de usuarios (solo para administradores)"""
    if not has_permission(st.session_state.get('user'), 'manage_users'):
        st.error("⛔ No tiene permisos para acceder a esta sección")
        return
    
    st.title("👥 Gestión de Usuarios")
    
    # Tabs para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "➕ Nuevo Usuario", "⚙️ Roles y Permisos"])
    
    with tab1:
        try:
            conn = get_connection()
            usuarios = pd.read_sql("""
                SELECT 
                    u.id,
                    u.username,
                    u.nombre_completo,
                    u.email,
                    r.nombre as rol,
                    u.activo,
                    u.last_login,
                    u.created_at
                FROM usuarios u
                LEFT JOIN roles r ON u.rol_id = r.id
                ORDER BY u.created_at DESC
            """, conn)
            
            if not usuarios.empty:
                # Formatear columnas
                usuarios['Estado'] = usuarios['activo'].apply(lambda x: '✅ Activo' if x else '❌ Inactivo')
                usuarios['Último login'] = pd.to_datetime(usuarios['last_login']).dt.strftime('%Y-%m-%d %H:%M')
                usuarios['Creado'] = pd.to_datetime(usuarios['created_at']).dt.strftime('%Y-%m-%d')
                
                # Mostrar tabla
                st.dataframe(
                    usuarios[['username', 'nombre_completo', 'email', 'rol', 'Estado', 'Último login', 'Creado']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Opciones por usuario
                st.subheader("Acciones por Usuario")
                
                for idx, user in usuarios.iterrows():
                    with st.expander(f"Usuario: {user['username']} - {user['nombre_completo']}"):
                        col_u1, col_u2, col_u3 = st.columns(3)
                        
                        with col_u1:
                            if st.button(f"🔄 Cambiar Estado", key=f"toggle_{user['id']}"):
                                conn = get_connection()
                                c = conn.cursor()
                                nuevo_estado = 0 if user['activo'] else 1
                                c.execute(
                                    "UPDATE usuarios SET activo = ? WHERE id = ?",
                                    (nuevo_estado, user['id'])
                                )
                                conn.commit()
                                conn.close()
                                st.success(f"Estado actualizado para {user['username']}")
                                st.rerun()
                        
                        with col_u2:
                            if st.button(f"🔑 Resetear Contraseña", key=f"reset_{user['id']}"):
                                # Aquí iría la lógica para resetear contraseña
                                st.info(f"Funcionalidad para resetear contraseña de {user['username']}")
                        
                        with col_u3:
                            if user['id'] != st.session_state.user['id']:
                                if st.button(f"🗑️ Eliminar", key=f"delete_{user['id']}", type="secondary"):
                                    if st.checkbox(f"¿Confirmar eliminación de {user['username']}?"):
                                        conn = get_connection()
                                        c = conn.cursor()
                                        c.execute("DELETE FROM usuarios WHERE id = ?", (user['id'],))
                                        conn.commit()
                                        conn.close()
                                        st.success(f"Usuario {user['username']} eliminado")
                                        st.rerun()
            else:
                st.info("No hay usuarios registrados")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error al cargar usuarios: {e}")
    
    with tab2:
        st.subheader("➕ Registrar Nuevo Usuario")
        
        with st.form("new_user_form"):
            col_n1, col_n2 = st.columns(2)
            
            with col_n1:
                new_username = st.text_input("Nombre de usuario*", placeholder="ej: jperez")
                new_email = st.text_input("Email", placeholder="ej: juan@drogueria.com")
                new_password = st.text_input("Contraseña*", type="password")
            
            with col_n2:
                new_fullname = st.text_input("Nombre completo*", placeholder="ej: Juan Pérez")
                
                # Obtener roles disponibles
                conn = get_connection()
                roles_df = pd.read_sql("SELECT id, nombre, descripcion FROM roles", conn)
                roles_options = {row['nombre']: row['id'] for _, row in roles_df.iterrows()}
                conn.close()
                
                new_role = st.selectbox("Rol*", options=list(roles_options.keys()))
                new_active = st.checkbox("Usuario activo", value=True)
            
            if st.form_submit_button("💾 Crear Usuario", type="primary"):
                if not new_username or not new_fullname or not new_password:
                    st.error("Por favor complete los campos obligatorios (*)")
                else:
                    try:
                        # Verificar si el usuario ya existe
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM usuarios WHERE username = ?", (new_username,))
                        if c.fetchone()[0] > 0:
                            st.error("El nombre de usuario ya existe")
                        else:
                            # Hash de contraseña
                            password_hash, salt = hash_password(new_password)
                            
                            # Insertar nuevo usuario
                            c.execute("""
                                INSERT INTO usuarios 
                                (username, nombre_completo, email, password_hash, salt, rol_id, activo)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                new_username,
                                new_fullname,
                                new_email if new_email else None,
                                password_hash,
                                salt,
                                roles_options[new_role],
                                1 if new_active else 0
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Usuario {new_username} creado exitosamente!")
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"Error al crear usuario: {e}")
    
    with tab3:
        st.subheader("⚙️ Gestión de Roles")
        
        try:
            conn = get_connection()
            roles = pd.read_sql("SELECT * FROM roles", conn)
            
            if not roles.empty:
                for _, rol in roles.iterrows():
                    with st.expander(f"Rol: {rol['nombre']} - {rol['descripcion']}"):
                        st.write(f"**ID:** {rol['id']}")
                        st.write(f"**Permisos:** {rol['permisos']}")
                        
                        # Editar permisos (simplificado)
                        if rol['nombre'] != 'admin':  # No permitir editar admin
                            nuevos_permisos = st.text_area(
                                "Permisos (separados por coma)",
                                value=rol['permisos'],
                                key=f"permisos_{rol['id']}"
                            )
                            
                            if st.button("💾 Actualizar", key=f"update_{rol['id']}"):
                                c = conn.cursor()
                                c.execute(
                                    "UPDATE roles SET permisos = ? WHERE id = ?",
                                    (nuevos_permisos, rol['id'])
                                )
                                conn.commit()
                                st.success("Permisos actualizados")
                                st.rerun()
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error al cargar roles: {e}")

def show_profile():
    """Muestra y permite editar el perfil del usuario"""
    user = st.session_state.get('user')
    if not user:
        return
    
    st.title("👤 Mi Perfil")
    
    col_p1, col_p2 = st.columns([1, 2])
    
    with col_p1:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: #f0f2f6; border-radius: 10px;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">👤</div>
            <h3>{user['nombre']}</h3>
            <div class="role-badge role-{user['rol']}">{user['rol'].upper()}</div>
            <p style="margin-top: 1rem; color: #666;">{user['username']}</p>
            {f"<p>{user['email']}</p>" if user['email'] else ""}
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Estadísticas del usuario
        try:
            conn = get_connection()
            stats = pd.read_sql(f"""
                SELECT 
                    COUNT(*) as ventas_registradas,
                    COALESCE(SUM(cantidad_total), 0) as unidades_vendidas
                FROM ventas 
                WHERE empleado = ?
            """, conn, params=(user['nombre'],))
            
            if not stats.empty:
                st.markdown("### 📊 Mis Estadísticas")
                st.metric("Ventas Registradas", int(stats['ventas_registradas'].iloc[0]))
                st.metric("Unidades Vendidas", int(stats['unidades_vendidas'].iloc[0]))
            
            conn.close()
        except:
            pass
    
    with col_p2:
        st.subheader("✏️ Editar Perfil")
        
        with st.form("edit_profile_form"):
            # Obtener información actual del usuario
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT email FROM usuarios WHERE id = ?", (user['id'],))
            current_data = c.fetchone()
            conn.close()
            
            current_email = current_data['email'] if current_data else ""
            
            new_fullname = st.text_input("Nombre completo", value=user['nombre'])
            new_email = st.text_input("Email", value=current_email)
            
            st.subheader("🔒 Cambiar Contraseña")
            current_password = st.text_input("Contraseña actual", type="password")
            new_password = st.text_input("Nueva contraseña", type="password")
            confirm_password = st.text_input("Confirmar nueva contraseña", type="password")
            
            if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                updates = []
                params = []
                
                if new_fullname != user['nombre']:
                    updates.append("nombre_completo = ?")
                    params.append(new_fullname)
                
                if new_email != current_email:
                    updates.append("email = ?")
                    params.append(new_email)
                
                # Cambiar contraseña si se proporcionó
                if current_password and new_password:
                    if new_password != confirm_password:
                        st.error("Las nuevas contraseñas no coinciden")
                    else:
                        # Verificar contraseña actual
                        verified_user = check_authentication(user['username'], current_password)
                        if verified_user:
                            password_hash, salt = hash_password(new_password)
                            updates.append("password_hash = ?")
                            updates.append("salt = ?")
                            params.extend([password_hash, salt])
                        else:
                            st.error("Contraseña actual incorrecta")
                
                if updates:
                    try:
                        conn = get_connection()
                        c = conn.cursor()
                        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"
                        params.append(user['id'])
                        c.execute(query, params)
                        conn.commit()
                        conn.close()
                        
                        # Actualizar session_state
                        st.session_state.user['nombre'] = new_fullname
                        if new_email:
                            st.session_state.user['email'] = new_email
                        
                        st.success("✅ Perfil actualizado correctamente")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error al actualizar perfil: {e}")
                else:
                    st.info("No hay cambios para guardar")

# ============================================================================
# BASE DE DATOS - MODIFICADA PARA SOLO UNIDADES (con autenticación)
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

def init_database():
    """Inicializa la base de datos (crea tablas si no existen)"""
    try:
        conn = get_connection()
        if conn is None:
            return False
            
        c = conn.cursor()
        
        # Verificar si las tablas ya existen
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventas'")
        if c.fetchone() is None:
            # Primero crear tablas de autenticación
            if not init_auth_database():
                return False
            
            # Luego crear tablas de ventas
            create_tables(conn)
            st.success("✅ Base de datos inicializada correctamente")
        else:
            # Solo verificar/crear tablas de autenticación si no existen
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
            if c.fetchone() is None:
                init_auth_database()
            
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar la base de datos: {e}")
        return False

def create_tables(conn=None):
    """Crea las tablas necesarias - MODIFICADA PARA SOLO UNIDADES"""
    close_conn = False
    try:
        if conn is None:
            conn = get_connection()
            close_conn = True
            
        c = conn.cursor()
        
        # Tabla de ventas - SIN campo de valor monetario
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
        
        # Tabla de detalle de ventas (unidades por producto) - SIN subtotal
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
        
        # Tabla de productos/inventario - SIN precio
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
        
        # Insertar datos iniciales si las tablas están vacías
        insert_initial_data(conn)
            
    except Exception as e:
        st.error(f"Error al crear tablas: {e}")
    finally:
        if close_conn and conn:
            conn.close()

def insert_initial_data(conn):
    """Inserta datos iniciales en la base de datos - SIN PRECIOS"""
    try:
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
        
        # Insertar productos de ejemplo si la tabla está vacía - SIN PRECIO
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
        
    except Exception as e:
        st.error(f"Error al insertar datos iniciales: {e}")

def add_sample_sales():
    """Agrega ventas de ejemplo para pruebas - MODIFICADO SIN VALOR"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si ya hay ventas
        c.execute("SELECT COUNT(*) as count FROM ventas")
        if c.fetchone()[0] > 0:
            st.info("Ya existen ventas, omitiendo datos de ejemplo")
            return
        
        # Obtener empleados
        c.execute("SELECT nombre, cargo, area FROM empleados LIMIT 4")
        empleados = c.fetchall()
        
        # Obtener productos
        c.execute("SELECT codigo, nombre, categoria, unidad_medida FROM productos LIMIT 5")
        productos = c.fetchall()
        
        if not empleados or not productos:
            st.warning("No hay suficientes datos para crear ventas de ejemplo")
            return
        
        # Crear ventas de ejemplo para los últimos 30 días
        hoy = date.today()
        ticket_counter = 1000
        
        for i in range(30):
            venta_date = hoy - timedelta(days=i)
            for emp_idx, empleado in enumerate(empleados):
                ticket_base = ticket_counter
                ticket_counter += 1
                
                # Calcular cantidad total
                cantidad_total = 0
                
                # Crear venta principal SIN VALOR
                c.execute("""
                    INSERT INTO ventas 
                    (fecha, anio, mes, dia, empleado, cargo, area, 
                     tipo_venta, canal, ticket, cantidad_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    venta_date,
                    venta_date.year,
                    venta_date.strftime("%Y-%m"),
                    venta_date.day,
                    empleado[0],  # nombre
                    empleado[1],  # cargo
                    empleado[2],  # area
                    "Mostrador" if i % 3 == 0 else "Receta" if i % 3 == 1 else "Cross Selling",
                    "Presencial" if i % 2 == 0 else "Domicilio",
                    ticket_base,
                    0  # Se calculará después
                ))
                
                venta_id = c.lastrowid
                cantidad_total = 0
                
                # Agregar productos a la venta SIN PRECIO NI SUBTOTAL
                for prod_idx, producto in enumerate(productos[:3]):  # Máximo 3 productos por venta
                    cantidad = (emp_idx * 2) + prod_idx + 1
                    
                    c.execute("""
                        INSERT INTO ventas_detalle 
                        (venta_id, producto, categoria, unidad_medida, cantidad)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        venta_id,
                        producto[1],  # nombre
                        producto[2],  # categoria
                        producto[3],  # unidad_medida
                        cantidad
                    ))
                    
                    cantidad_total += cantidad
                
                # Actualizar la venta con el total de unidades
                c.execute("""
                    UPDATE ventas 
                    SET cantidad_total = ?
                    WHERE id = ?
                """, (cantidad_total, venta_id))
        
        conn.commit()
        st.success(f"✅ Ventas de ejemplo agregadas (solo unidades)")
        
    except Exception as e:
        st.error(f"Error al agregar ventas de ejemplo: {e}")
    finally:
        if conn:
            conn.close()

def get_products():
    """Obtiene la lista de productos disponibles - SIN PRECIO"""
    try:
        conn = get_connection()
        productos = pd.read_sql("""
            SELECT codigo, nombre, categoria, unidad_medida, stock 
            FROM productos 
            WHERE activo = 1
            ORDER BY categoria, nombre
        """, conn)
        conn.close()
        
        # Crear un diccionario para fácil acceso
        product_dict = {}
        for _, row in productos.iterrows():
            product_dict[row['codigo']] = {
                'nombre': row['nombre'],
                'categoria': row['categoria'],
                'unidad': row['unidad_medida'],
                'stock': row['stock']
            }
        
        return productos, product_dict
    except Exception as e:
        st.error(f"Error al obtener productos: {e}")
        return pd.DataFrame(), {}

# ============================================================================
# PÁGINA PRINCIPAL / INICIO - MODIFICADA CON AUTENTICACIÓN
# ============================================================================
def show_home():
    """Muestra la página de inicio - SOLO UNIDADES"""
    user = st.session_state.get('user')
    
    st.markdown(f"""
    <div class="main-header">
        <h1>🏥 Sistema de Gestión de Unidades Vendidas</h1>
        <h3>Droguería Restrepo</h3>
        <p>Bienvenido, <strong>{user['nombre']}</strong> | Rol: <span class="role-badge role-{user['rol']}">{user['rol'].upper()}</span></p>
        <p>Registro de <strong>UNIDADES</strong> vendidas por el equipo de trabajo</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Verificar estado de la base de datos
    if not check_database():
        st.warning("⚠️ **La base de datos no está inicializada**")
        
        with st.expander("🔧 Inicializar Base de Datos", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🛠️ Crear Base de Datos", type="primary", use_container_width=True):
                    if init_database():
                        st.rerun()
            
            with col2:
                if st.button("📊 Agregar Datos de Ejemplo", type="secondary", use_container_width=True):
                    add_sample_sales()
                    st.rerun()
        
        st.stop()
    
    # Estadísticas rápidas - SOLO UNIDADES
    st.header("📈 Estadísticas del Equipo (Unidades)")
    
    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Unidades Totales", f"{stats['unidades_total']:,}")
    
    with col2:
        st.metric("👥 Empleados Activos", stats['empleados_count'])
    
    with col3:
        if stats['unidades_total'] > 0:
            ventas_count = stats['ventas_count']
            if ventas_count > 0:
                prom_unidades = stats['unidades_total'] / ventas_count
                st.metric("📊 Prom. por Venta", f"{prom_unidades:.1f}")
            else:
                st.metric("📊 Prom. por Venta", "0.0")
        else:
            st.metric("📊 Prom. por Venta", "0.0")
    
    with col4:
        st.metric("📋 Ventas Registradas", stats['ventas_count'])
    
    # Top productos - SOLO CANTIDADES
    try:
        conn = get_connection()
        top_productos = pd.read_sql("""
            SELECT 
                producto,
                SUM(cantidad) as unidades_vendidas,
                COUNT(DISTINCT venta_id) as veces_vendido
            FROM ventas_detalle
            GROUP BY producto
            ORDER BY unidades_vendidas DESC
            LIMIT 5
        """, conn)
        
        if not top_productos.empty:
            st.header("🏆 Productos Más Vendidos (Unidades)")
            
            for idx, row in top_productos.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"**{row['producto']}**")
                with col2:
                    st.write(f"📦 {int(row['unidades_vendidas'])} unidades")
                with col3:
                    st.write(f"🔄 {int(row['veces_vendido'])} veces")
                st.divider()
        
        conn.close()
        
    except Exception as e:
        st.info("No hay datos de productos vendidos aún")

# ============================================================================
# PÁGINA DE REGISTRO DE VENTAS - MODIFICADA CON PERMISOS
# ============================================================================
def show_registro():
    """Muestra la página de registro de ventas con unidades - SIN PRECIOS"""
    if not has_permission(st.session_state.get('user'), 'write'):
        st.error("⛔ No tiene permisos para registrar ventas")
        return
    
    st.title("📝 Registro de Unidades Vendidas")
    
    # Inicializar lista de productos en session_state
    if 'productos_venta' not in st.session_state:
        st.session_state.productos_venta = []
    
    # Obtener productos disponibles
    productos_df, productos_dict = get_products()
    
    with st.form("form_registro_venta"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Información del Vendedor")
            
            fecha = st.date_input("Fecha de venta*", value=date.today())
            
            # Obtener empleados
            try:
                conn = get_connection()
                empleados_df = pd.read_sql("SELECT nombre, cargo, area FROM empleados", conn)
                conn.close()
                
                if not empleados_df.empty:
                    empleado = st.selectbox(
                        "Empleado*",
                        options=empleados_df['nombre'].tolist()
                    )
                    
                    # Mostrar información del empleado seleccionado
                    empleado_info = empleados_df[empleados_df['nombre'] == empleado].iloc[0]
                    cargo = empleado_info['cargo']
                    area = empleado_info['area']
                    
                    st.text_input("Cargo", value=cargo, disabled=True)
                    st.text_input("Área", value=area, disabled=True)
                else:
                    st.warning("No hay empleados registrados")
                    empleado = st.text_input("Nombre del empleado*")
                    cargo = st.text_input("Cargo*")
                    area = st.selectbox("Área*", ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Otro"])
                    
            except Exception as e:
                st.error(f"Error al cargar empleados: {e}")
                empleado = st.text_input("Nombre del empleado*")
                cargo = st.text_input("Cargo*")
                area = st.selectbox("Área*", ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Otro"])
        
        with col2:
            st.subheader("📋 Información de la Venta")
            
            tipo_venta = st.selectbox(
                "Tipo de venta*",
                ["Mostrador", "Receta", "Cross Selling", "Pedido especial", "Otro"]
            )
            
            canal = st.selectbox(
                "Canal de venta*",
                ["Presencial", "Domicilio", "WhatsApp", "Teléfono", "Online", "Otro"]
            )
            
            ticket = st.number_input(
                "Número de ticket*",
                min_value=1,
                step=1,
                help="Número único de comprobante"
            )
            
            # Verificar ticket único
            if ticket > 0:
                try:
                    conn = get_connection()
                    ticket_existente = pd.read_sql(
                        f"SELECT COUNT(*) as existe FROM ventas WHERE ticket = {ticket}",
                        conn
                    )
                    if ticket_existente['existe'].iloc[0] > 0:
                        st.error("⚠️ Este número de ticket ya está registrado")
                    conn.close()
                except:
                    pass
        
        st.divider()
        st.subheader("🛒 Productos Vendidos (Unidades)")
        
        # Selección de productos
        col_prod1, col_prod2, col_prod3 = st.columns(3)
        
        with col_prod1:
            if not productos_df.empty:
                producto_seleccionado = st.selectbox(
                    "Seleccionar producto",
                    options=productos_df['codigo'].tolist(),
                    format_func=lambda x: f"{x} - {productos_dict[x]['nombre']}"
                )
            else:
                st.warning("No hay productos disponibles")
                producto_seleccionado = None
        
        with col_prod2:
            if producto_seleccionado:
                producto_info = productos_dict[producto_seleccionado]
                st.text_input("Producto", value=producto_info['nombre'], disabled=True)
                st.text_input("Unidad de medida", value=producto_info['unidad'], disabled=True)
                st.text_input("Stock disponible", value=producto_info['stock'], disabled=True)
        
        with col_prod3:
            if producto_seleccionado:
                cantidad = st.number_input(
                    "Cantidad de unidades*",
                    min_value=1,
                    max_value=productos_dict[producto_seleccionado]['stock'],
                    step=1,
                    value=1
                )
                
                if st.button("➕ Agregar producto", type="secondary"):
                    producto_info = productos_dict[producto_seleccionado]
                    
                    nuevo_producto = {
                        'codigo': producto_seleccionado,
                        'nombre': producto_info['nombre'],
                        'categoria': producto_info['categoria'],
                        'unidad': producto_info['unidad'],
                        'cantidad': cantidad
                    }
                    
                    st.session_state.productos_venta.append(nuevo_producto)
                    st.success(f"✅ {cantidad} {producto_info['unidad']} de {producto_info['nombre']} agregados")
                    st.rerun()
        
        # Mostrar productos agregados
        if st.session_state.productos_venta:
            st.divider()
            st.subheader("📋 Resumen de productos agregados")
            
            total_unidades = 0
            
            for i, producto in enumerate(st.session_state.productos_venta):
                col_res1, col_res2, col_res3, col_res4 = st.columns([3, 2, 2, 1])
                
                with col_res1:
                    st.markdown(f"""
                    <div class="product-item">
                        <strong>{producto['nombre']}</strong><br>
                        <small>Categoría: {producto['categoria']} | Unidad: {producto['unidad']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_res2:
                    st.write(f"Unidades: {producto['cantidad']}")
                
                with col_res3:
                    st.write(f"Stock reducido en: {producto['cantidad']}")
                
                with col_res4:
                    if st.button("❌", key=f"eliminar_{i}"):
                        st.session_state.productos_venta.pop(i)
                        st.rerun()
                
                total_unidades += producto['cantidad']
            
            # Mostrar totales - SOLO UNIDADES
            st.markdown(f"""
            <div class="total-box">
                <h3>Total de la venta</h3>
                <p><strong>Unidades totales:</strong> {total_unidades}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Botón de registro
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            submitted = st.form_submit_button("💾 Registrar Venta", type="primary", use_container_width=True)
        
        with col_btn2:
            if st.form_submit_button("🔄 Limpiar productos", type="secondary", use_container_width=True):
                st.session_state.productos_venta = []
                st.rerun()
        
        if submitted:
            # Validaciones
            errores = []
            
            if not empleado or empleado.strip() == "":
                errores.append("El nombre del empleado es requerido")
            if ticket <= 0:
                errores.append("El número de ticket debe ser válido")
            if not st.session_state.productos_venta:
                errores.append("Debe agregar al menos un producto")
            
            if errores:
                for error in errores:
                    st.error(f"❌ {error}")
            else:
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    
                    # Registrar venta principal SIN VALOR
                    user_id = st.session_state.user['id']
                    c.execute("""
                        INSERT INTO ventas 
                        (fecha, anio, mes, dia, empleado, cargo, area, 
                         tipo_venta, canal, ticket, cantidad_total, usuario_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        fecha,
                        fecha.year,
                        fecha.strftime("%Y-%m"),
                        fecha.day,
                        empleado.strip(),
                        cargo,
                        area,
                        tipo_venta,
                        canal,
                        ticket,
                        total_unidades,
                        user_id
                    ))
                    
                    venta_id = c.lastrowid
                    
                    # Registrar detalles de productos SIN PRECIO NI SUBTOTAL
                    for producto in st.session_state.productos_venta:
                        c.execute("""
                            INSERT INTO ventas_detalle 
                            (venta_id, producto, categoria, unidad_medida, cantidad)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            venta_id,
                            producto['nombre'],
                            producto['categoria'],
                            producto['unidad'],
                            producto['cantidad']
                        ))
                        
                        # Actualizar stock
                        c.execute("""
                            UPDATE productos 
                            SET stock = stock - ?
                            WHERE codigo = ?
                        """, (producto['cantidad'], producto['codigo']))
                    
                    conn.commit()
                    conn.close()
                    
                    # Limpiar productos y mostrar éxito
                    st.session_state.productos_venta = []
                    st.success("✅ Venta registrada exitosamente!")
                    st.balloons()
                    
                    # Mostrar resumen
                    with st.expander("📋 Ver resumen detallado", expanded=True):
                        col_sum1, col_sum2 = st.columns(2)
                        
                        with col_sum1:
                            st.write("**Información general:**")
                            st.write(f"- **Fecha:** {fecha}")
                            st.write(f"- **Empleado:** {empleado}")
                            st.write(f"- **Cargo:** {cargo}")
                            st.write(f"- **Área:** {area}")
                            st.write(f"- **Ticket:** {ticket}")
                        
                        with col_sum2:
                            st.write("**Detalles de venta:**")
                            st.write(f"- **Tipo:** {tipo_venta}")
                            st.write(f"- **Canal:** {canal}")
                            st.write(f"- **Total unidades:** {total_unidades}")
                            st.write("- **Productos:**")
                            for producto in st.session_state.productos_venta:
                                st.write(f"  • {producto['nombre']}: {producto['cantidad']} {producto['unidad']}")
                    
                except Exception as e:
                    st.error(f"❌ Error al registrar: {str(e)}")

def check_database():
    """Verifica el estado de la base de datos"""
    try:
        conn = get_connection()
        if conn is None:
            return False
            
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventas'")
        exists = c.fetchone() is not None
        conn.close()
        return exists
    except:
        return False

def get_stats():
    """Obtiene estadísticas generales - SOLO UNIDADES"""
    stats = {
        'ventas_count': 0,
        'unidades_total': 0,
        'empleados_count': 0
    }
    
    try:
        conn = get_connection()
        if conn is None:
            return stats
            
        # Total de ventas
        df_ventas = pd.read_sql("SELECT COUNT(*) as total FROM ventas", conn)
        stats['ventas_count'] = int(df_ventas['total'].iloc[0])
        
        # Unidades totales
        df_unidades = pd.read_sql("SELECT COALESCE(SUM(cantidad_total), 0) as unidades FROM ventas", conn)
        stats['unidades_total'] = int(df_unidades['unidades'].iloc[0])
        
        # Empleados activos (que han registrado ventas)
        df_empleados = pd.read_sql("SELECT COUNT(DISTINCT empleado) as empleados FROM ventas", conn)
        stats['empleados_count'] = int(df_empleados['empleados'].iloc[0])
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error al obtener estadísticas: {e}")
        
    return stats

# ============================================================================
# CONTROL PRINCIPAL DE AUTENTICACIÓN
# ============================================================================
def main():
    """Función principal que controla la autenticación"""
    
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
    # SIDEBAR - NAVEGACIÓN PRINCIPAL - MODIFICADA CON AUTENTICACIÓN
    # ========================================================================
    with st.sidebar:
        user = st.session_state.user
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0;">
            <h2>🏥 Droguería Restrepo</h2>
            <p style="color: #666; font-size: 0.9rem;">Usuario: <strong>{user['nombre']}</strong></p>
            <div class="role-badge role-{user['rol']}" style="margin: 0.5rem auto;">{user['rol'].upper()}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Estado de la página
        st.markdown("### 📍 Navegación")
        
        col_nav1, col_nav2 = st.columns(2)
        
        with col_nav1:
            if st.button("🏠 Inicio", use_container_width=True, type="primary"):
                st.session_state.page = 'inicio'
                st.rerun()
        
        with col_nav2:
            if st.button("🔄 Recargar", use_container_width=True):
                st.rerun()
        
        st.divider()
        
        # Módulos principales
        st.markdown("### 📂 Módulos")
        
        if st.button("📝 Registrar Unidades", use_container_width=True, 
                     help="Registrar unidades vendidas por el equipo"):
            st.session_state.page = 'registro'
            st.rerun()
        
        if st.button("📊 Ver Informes", use_container_width=True,
                     help="Ver reportes de unidades"):
            st.session_state.page = 'informes'
            st.rerun()
        
        # Módulos de administración (solo para admin)
        if has_permission(user, 'manage_users'):
            st.divider()
            st.markdown("### ⚙️ Administración")
            
            if st.button("👥 Gestión de Usuarios", use_container_width=True):
                st.session_state.page = 'usuarios'
                st.rerun()
        
        # Perfil y cierre de sesión
        st.divider()
        st.markdown("### 👤 Mi Cuenta")
        
        col_acc1, col_acc2 = st.columns(2)
        
        with col_acc1:
            if st.button("👤 Perfil", use_container_width=True):
                st.session_state.page = 'perfil'
                st.rerun()
        
        with col_acc2:
            if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.session_state.page = 'inicio'
                st.rerun()
        
        st.divider()
        
        # Estadísticas del día - SOLO UNIDADES
        st.markdown("### 📊 Hoy (Unidades)")
        
        try:
            conn = get_connection()
            hoy = date.today().strftime("%Y-%m-%d")
            
            stats_hoy = pd.read_sql(f"""
                SELECT 
                    COUNT(*) as ventas,
                    COALESCE(SUM(cantidad_total), 0) as unidades
                FROM ventas 
                WHERE fecha = '{hoy}'
            """, conn)
            
            col_today1, col_today2 = st.columns(2)
            with col_today1:
                st.metric("Ventas", int(stats_hoy['ventas'].iloc[0]))
            with col_today2:
                st.metric("Unidades", int(stats_hoy['unidades'].iloc[0]))
                
            conn.close()
            
        except:
            st.info("No hay ventas hoy")
    
    # ========================================================================
    # CONTENIDO PRINCIPAL BASADO EN LA PÁGINA SELECCIONADA
    # ========================================================================
    if st.session_state.page == 'inicio':
        show_home()
    elif st.session_state.page == 'registro':
        show_registro()
    elif st.session_state.page == 'informes':
        st.title("📊 Informes de Unidades Vendidas")
        st.info("En desarrollo - Solo mostrará información de unidades")
    elif st.session_state.page == 'usuarios':
        show_user_management()
    elif st.session_state.page == 'perfil':
        show_profile()

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================
if __name__ == "__main__":
    main()

# ============================================================================
# FOOTER
# ============================================================================
if st.session_state.get('authenticated', False):
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p><strong>🏥 Sistema de Registro de Unidades Vendidas</strong></p>
        <p>Solo unidades - Con sistema de autenticación</p>
        <p>© 2024 | Versión 3.0 | Usuario: {}</p>
    </div>
    """.format(st.session_state.get('user', {}).get('nombre', '')), unsafe_allow_html=True)