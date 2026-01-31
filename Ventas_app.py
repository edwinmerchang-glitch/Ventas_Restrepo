# ventas_app.py - Aplicación completa de gestión de ventas con autenticación y gestión de empleados
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
    
    .employee-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .area-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .area-farmacia { background: #e3f2fd; color: #1565c0; }
    .area-cajas { background: #f3e5f5; color: #7b1fa2; }
    .area-equipos { background: #e8f5e9; color: #2e7d32; }
    .area-pasillos { background: #fff3e0; color: #ef6c00; }
    .status-active { color: #2e7d32; font-weight: bold; }
    .status-inactive { color: #c62828; font-weight: bold; }
    
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem 0;
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
        
        # 3. Crear tabla de empleados
        c.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT NOT NULL,
            fecha_ingreso DATE,
            telefono TEXT,
            email TEXT,
            activo BOOLEAN DEFAULT 1,
            ventas_totales INTEGER DEFAULT 0,
            unidades_vendidas INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 4. Crear otras tablas del sistema
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
        
        conn.commit()
        
        # 5. Insertar datos iniciales
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
                ('admin', 'Administrador del sistema', 'read,write,delete,manage_users,manage_employees'),
                ('vendedor', 'Vendedor', 'read,write'),
                ('inventario', 'Encargado de inventario', 'read,write,inventory'),
                ('reportes', 'Solo visualización', 'read'),
                ('gerente', 'Gerente', 'read,write,manage_employees')
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
                ("EMP001", "Carlos Restrepo", "Vendedor Senior", "Farmacia", "2023-01-15", "3001234567", "carlos@drogueria.com"),
                ("EMP002", "Ana García", "Cajera", "Cajas", "2023-02-20", "3002345678", "ana@drogueria.com"),
                ("EMP003", "Luis Fernández", "Asesor Técnico", "Equipos Médicos", "2023-03-10", "3003456789", "luis@drogueria.com"),
                ("EMP004", "María Rodríguez", "Vendedor", "Pasillos", "2023-04-05", "3004567890", "maria@drogueria.com"),
                ("EMP005", "Pedro Sánchez", "Gerente", "Farmacia", "2022-11-01", "3005678901", "pedro@drogueria.com"),
                ("EMP006", "Laura Martínez", "Cajera", "Cajas", "2023-05-15", "3006789012", "laura@drogueria.com"),
                ("EMP007", "Jorge López", "Almacenista", "Inventario", "2023-06-20", "3007890123", "jorge@drogueria.com"),
                ("EMP008", "Sofía Ramírez", "Vendedor", "Farmacia", "2023-07-01", "3008901234", "sofia@drogueria.com")
            ]
            c.executemany(
                """INSERT OR IGNORE INTO empleados 
                (codigo, nombre, cargo, area, fecha_ingreso, telefono, email) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                empleados
            )
        
        # Insertar productos de ejemplo
        c.execute("SELECT COUNT(*) FROM productos")
        if c.fetchone()[0] == 0:
            productos = [
                ("MED001", "Paracetamol 500mg", "Medicamentos", "Caja", 100),
                ("MED002", "Ibuprofeno 400mg", "Medicamentos", "Caja", 80),
                ("HIG001", "Jabón Antibacterial", "Higiene", "Unidad", 200),
                ("EQU001", "Termómetro Digital", "Equipos", "Unidad", 30)
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
# GESTIÓN DE EMPLEADOS - FUNCIONES COMPLETAS
# ============================================================================
def get_employees(filtro_activo=None, filtro_area=None):
    """Obtiene todos los empleados con opciones de filtro"""
    try:
        conn = get_connection()
        
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
                ventas_totales,
                unidades_vendidas,
                created_at
            FROM empleados
            WHERE 1=1
        """
        
        params = []
        
        if filtro_activo is not None:
            query += " AND activo = ?"
            params.append(filtro_activo)
        
        if filtro_area:
            query += " AND area = ?"
            params.append(filtro_area)
        
        query += " ORDER BY nombre"
        
        empleados = pd.read_sql(query, conn, params=params)
        conn.close()
        return empleados
    except Exception as e:
        st.error(f"Error al obtener empleados: {e}")
        return pd.DataFrame()

def get_employee_by_id(employee_id):
    """Obtiene un empleado por su ID"""
    try:
        conn = get_connection()
        query = """
            SELECT * FROM empleados WHERE id = ?
        """
        empleado = pd.read_sql(query, conn, params=(employee_id,))
        conn.close()
        
        if not empleado.empty:
            return empleado.iloc[0].to_dict()
        return None
    except:
        return None

def get_employee_by_code(codigo):
    """Obtiene un empleado por su código"""
    try:
        conn = get_connection()
        query = """
            SELECT * FROM empleados WHERE codigo = ?
        """
        empleado = pd.read_sql(query, conn, params=(codigo,))
        conn.close()
        
        if not empleado.empty:
            return empleado.iloc[0].to_dict()
        return None
    except:
        return None

def create_employee(codigo, nombre, cargo, area, fecha_ingreso=None, telefono=None, email=None):
    """Crea un nuevo empleado"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si el código ya existe
        c.execute("SELECT COUNT(*) FROM empleados WHERE codigo = ?", (codigo,))
        if c.fetchone()[0] > 0:
            return False, "El código de empleado ya existe"
        
        # Verificar si el nombre ya existe
        c.execute("SELECT COUNT(*) FROM empleados WHERE nombre = ?", (nombre,))
        if c.fetchone()[0] > 0:
            return False, "El nombre de empleado ya existe"
        
        # Insertar nuevo empleado
        c.execute("""
            INSERT INTO empleados 
            (codigo, nombre, cargo, area, fecha_ingreso, telefono, email, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            nombre,
            cargo,
            area,
            fecha_ingreso if fecha_ingreso else date.today().isoformat(),
            telefono,
            email,
            1  # Activo por defecto
        ))
        
        conn.commit()
        conn.close()
        return True, "Empleado creado exitosamente"
        
    except Exception as e:
        return False, f"Error al crear empleado: {str(e)}"

def update_employee(employee_id, **kwargs):
    """Actualiza los datos de un empleado"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Construir query dinámica
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if value is not None:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False, "No hay datos para actualizar"
        
        # Agregar timestamp de actualización
        fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # Agregar ID al final de los valores
        values.append(employee_id)
        
        query = f"UPDATE empleados SET {', '.join(fields)} WHERE id = ?"
        
        c.execute(query, values)
        conn.commit()
        
        # Verificar si se actualizó
        if c.rowcount > 0:
            conn.close()
            return True, "Empleado actualizado exitosamente"
        else:
            conn.close()
            return False, "No se encontró el empleado"
        
    except Exception as e:
        return False, f"Error al actualizar empleado: {str(e)}"

def delete_employee(employee_id):
    """Elimina un empleado (cambia estado a inactivo)"""
    try:
        # En lugar de eliminar, marcamos como inactivo
        success, message = update_employee(employee_id, activo=0)
        return success, message
    except Exception as e:
        return False, f"Error al eliminar empleado: {str(e)}"

def get_employee_stats():
    """Obtiene estadísticas de empleados"""
    try:
        conn = get_connection()
        
        # Estadísticas generales
        stats_query = """
            SELECT 
                COUNT(*) as total_empleados,
                SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos,
                SUM(CASE WHEN activo = 0 THEN 1 ELSE 0 END) as inactivos,
                COUNT(DISTINCT area) as areas_distintas,
                COALESCE(SUM(ventas_totales), 0) as ventas_totales,
                COALESCE(SUM(unidades_vendidas), 0) as unidades_totales
            FROM empleados
        """
        
        stats = pd.read_sql(stats_query, conn).iloc[0].to_dict()
        
        # Empleados por área
        area_query = """
            SELECT 
                area,
                COUNT(*) as cantidad,
                SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos
            FROM empleados
            GROUP BY area
            ORDER BY cantidad DESC
        """
        
        areas = pd.read_sql(area_query, conn)
        
        # Top vendedores
        top_vendedores_query = """
            SELECT 
                nombre,
                cargo,
                area,
                ventas_totales,
                unidades_vendidas
            FROM empleados
            WHERE ventas_totales > 0
            ORDER BY ventas_totales DESC
            LIMIT 5
        """
        
        top_vendedores = pd.read_sql(top_vendedores_query, conn)
        
        conn.close()
        
        return {
            'general': stats,
            'por_area': areas,
            'top_vendedores': top_vendedores
        }
        
    except Exception as e:
        st.error(f"Error al obtener estadísticas: {e}")
        return None

def get_areas():
    """Obtiene la lista de áreas disponibles"""
    try:
        conn = get_connection()
        query = "SELECT DISTINCT area FROM empleados WHERE area IS NOT NULL ORDER BY area"
        areas_df = pd.read_sql(query, conn)
        conn.close()
        
        areas = areas_df['area'].tolist()
        
        # Áreas por defecto si no hay ninguna
        if not areas:
            areas = ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Inventario", "Administración", "Otro"]
        
        return areas
    except:
        return ["Farmacia", "Cajas", "Equipos Médicos", "Pasillos", "Inventario", "Administración", "Otro"]

def get_cargos():
    """Obtiene la lista de cargos disponibles"""
    try:
        conn = get_connection()
        query = "SELECT DISTINCT cargo FROM empleados WHERE cargo IS NOT NULL ORDER BY cargo"
        cargos_df = pd.read_sql(query, conn)
        conn.close()
        
        cargos = cargos_df['cargo'].tolist()
        
        # Cargos por defecto si no hay ninguno
        if not cargos:
            cargos = [
                "Vendedor",
                "Vendedor Senior",
                "Cajero/a",
                "Asesor Técnico",
                "Gerente",
                "Almacenista",
                "Supervisor",
                "Auxiliar",
                "Otro"
            ]
        
        return cargos
    except:
        return ["Vendedor", "Vendedor Senior", "Cajero/a", "Asesor Técnico", "Gerente", "Almacenista", "Supervisor", "Auxiliar", "Otro"]

# ============================================================================
# GESTIÓN DE EMPLEADOS - INTERFAZ
# ============================================================================
def show_employee_management():
    """Muestra la interfaz de gestión de empleados"""
    if not has_permission(st.session_state.get('user'), 'manage_employees'):
        st.error("⛔ No tiene permisos para acceder a esta sección")
        return
    
    st.title("👤 Gestión de Empleados")
    
    # Tabs para diferentes funcionalidades
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Lista de Empleados", 
        "➕ Nuevo Empleado", 
        "📊 Estadísticas",
        "🔍 Buscar Empleado"
    ])
    
    with tab1:
        show_employee_list()
    
    with tab2:
        show_new_employee_form()
    
    with tab3:
        show_employee_stats()
    
    with tab4:
        show_employee_search()

def show_employee_list():
    """Muestra la lista de empleados"""
    st.subheader("📋 Lista de Empleados")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_estado = st.selectbox(
            "Filtrar por estado",
            ["Todos", "Activos", "Inactivos"],
            key="filtro_estado"
        )
    
    with col2:
        areas = get_areas()
        filtro_area = st.selectbox(
            "Filtrar por área",
            ["Todas"] + areas,
            key="filtro_area"
        )
    
    with col3:
        if st.button("🔄 Actualizar lista", use_container_width=True):
            st.rerun()
    
    # Convertir filtros
    estado_map = {
        "Todos": None,
        "Activos": 1,
        "Inactivos": 0
    }
    
    estado_filtro = estado_map[filtro_estado]
    area_filtro = None if filtro_area == "Todas" else filtro_area
    
    # Obtener empleados filtrados
    empleados = get_employees(
        filtro_activo=estado_filtro,
        filtro_area=area_filtro
    )
    
    if not empleados.empty:
        # Formatear datos para visualización
        empleados_display = empleados.copy()
        empleados_display['Estado'] = empleados_display['activo'].apply(
            lambda x: '<span class="status-active">✅ Activo</span>' if x else '<span class="status-inactive">❌ Inactivo</span>'
        )
        empleados_display['Fecha Ingreso'] = pd.to_datetime(empleados_display['fecha_ingreso']).dt.strftime('%Y-%m-%d')
        empleados_display['Creado'] = pd.to_datetime(empleados_display['created_at']).dt.strftime('%Y-%m-%d')
        
        # Mostrar en formato de tarjetas
        for _, emp in empleados.iterrows():
            with st.container():
                col_emp1, col_emp2, col_emp3 = st.columns([3, 2, 1])
                
                with col_emp1:
                    area_class = f"area-{emp['area'].lower().replace(' ', '-').replace('é', 'e').replace('ó', 'o')}"
                    st.markdown(f"""
                    <div class="employee-card">
                        <h4>{emp['nombre']}</h4>
                        <p><strong>Código:</strong> {emp['codigo']}</p>
                        <p><strong>Cargo:</strong> {emp['cargo']}</p>
                        <p><strong>Área:</strong> <span class="area-badge {area_class}">{emp['area']}</span></p>
                        <p><strong>Estado:</strong> {'<span class="status-active">✅ Activo</span>' if emp['activo'] else '<span class="status-inactive">❌ Inactivo</span>'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_emp2:
                    st.write(f"**Contacto:**")
                    if emp['telefono']:
                        st.write(f"📞 {emp['telefono']}")
                    if emp['email']:
                        st.write(f"📧 {emp['email']}")
                    st.write(f"**Ingreso:** {emp['fecha_ingreso']}")
                    st.write(f"**Ventas:** {emp['ventas_totales']}")
                    st.write(f"**Unidades:** {emp['unidades_vendidas']}")
                
                with col_emp3:
                    # Botones de acción
                    if st.button("✏️ Editar", key=f"edit_{emp['id']}", use_container_width=True):
                        st.session_state.edit_employee_id = emp['id']
                        st.session_state.page = 'editar_empleado'
                        st.rerun()
                    
                    if emp['activo']:
                        if st.button("❌ Desactivar", key=f"deactivate_{emp['id']}", type="secondary", use_container_width=True):
                            success, message = update_employee(emp['id'], activo=0)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    else:
                        if st.button("✅ Activar", key=f"activate_{emp['id']}", type="secondary", use_container_width=True):
                            success, message = update_employee(emp['id'], activo=1)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                
                st.divider()
        
        # Mostrar contador
        st.info(f"**Total empleados mostrados:** {len(empleados)}")
        
    else:
        st.info("No hay empleados registrados con los filtros seleccionados")

def show_new_employee_form():
    """Muestra el formulario para crear nuevo empleado"""
    st.subheader("➕ Registrar Nuevo Empleado")
    
    with st.form("new_employee_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Código único
            codigo = st.text_input(
                "Código de empleado*",
                placeholder="EMP009",
                help="Código único identificador"
            )
            
            # Nombre completo
            nombre = st.text_input(
                "Nombre completo*",
                placeholder="Juan Pérez"
            )
            
            # Cargo
            cargos = get_cargos()
            cargo = st.selectbox(
                "Cargo*",
                options=cargos
            )
            
            # Área
            areas = get_areas()
            area = st.selectbox(
                "Área*",
                options=areas
            )
        
        with col2:
            # Fecha de ingreso
            fecha_ingreso = st.date_input(
                "Fecha de ingreso",
                value=date.today()
            )
            
            # Teléfono
            telefono = st.text_input(
                "Teléfono",
                placeholder="3001234567"
            )
            
            # Email
            email = st.text_input(
                "Email",
                placeholder="empleado@drogueria.com"
            )
            
            # Estado (activo por defecto)
            activo = st.checkbox("Empleado activo", value=True)
        
        submitted = st.form_submit_button("💾 Registrar Empleado", type="primary", use_container_width=True)
        
        if submitted:
            # Validaciones
            if not codigo:
                st.error("El código de empleado es requerido")
            elif not nombre:
                st.error("El nombre completo es requerido")
            elif not cargo:
                st.error("El cargo es requerido")
            elif not area:
                st.error("El área es requerida")
            else:
                # Crear empleado
                success, message = create_employee(
                    codigo=codigo,
                    nombre=nombre,
                    cargo=cargo,
                    area=area,
                    fecha_ingreso=fecha_ingreso.isoformat(),
                    telefono=telefono if telefono else None,
                    email=email if email else None
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)

def show_employee_stats():
    """Muestra estadísticas de empleados"""
    st.subheader("📊 Estadísticas de Empleados")
    
    stats = get_employee_stats()
    
    if stats:
        # Estadísticas generales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <h3>👥</h3>
                <h2>{stats['general']['total_empleados']}</h2>
                <p>Total Empleados</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stats-card" style="background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);">
                <h3>✅</h3>
                <h2>{stats['general']['activos']}</h2>
                <p>Empleados Activos</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stats-card" style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);">
                <h3>📦</h3>
                <h2>{stats['general']['ventas_totales']}</h2>
                <p>Ventas Totales</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stats-card" style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);">
                <h3>📊</h3>
                <h2>{stats['general']['unidades_totales']}</h2>
                <p>Unidades Vendidas</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Distribución por área
        st.subheader("📈 Distribución por Área")
        
        if not stats['por_area'].empty:
            col_area1, col_area2 = st.columns(2)
            
            with col_area1:
                for _, row in stats['por_area'].iterrows():
                    area_class = f"area-{row['area'].lower().replace(' ', '-').replace('é', 'e').replace('ó', 'o')}"
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                        <p><strong>{row['area']}</strong></p>
                        <p>Total: {row['cantidad']} | Activos: {row['activos']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_area2:
                # Gráfico simple de barras
                try:
                    import plotly.express as px
                    fig = px.bar(
                        stats['por_area'],
                        x='area',
                        y='cantidad',
                        color='area',
                        title="Empleados por Área",
                        labels={'area': 'Área', 'cantidad': 'Cantidad'},
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.info("Instale plotly para ver gráficos: pip install plotly")
        
        # Top vendedores
        st.subheader("🏆 Top Vendedores")
        
        if not stats['top_vendedores'].empty:
            for idx, row in stats['top_vendedores'].iterrows():
                with st.container():
                    col_top1, col_top2, col_top3 = st.columns([3, 2, 2])
                    
                    with col_top1:
                        st.write(f"**{idx + 1}. {row['nombre']}**")
                        st.write(f"{row['cargo']} | {row['area']}")
                    
                    with col_top2:
                        st.metric("Ventas", row['ventas_totales'])
                    
                    with col_top3:
                        st.metric("Unidades", row['unidades_vendidas'])
                    
                    st.divider()
        else:
            st.info("No hay datos de ventas por empleado")

def show_employee_search():
    """Muestra interfaz de búsqueda de empleados"""
    st.subheader("🔍 Buscar Empleado")
    
    col_search1, col_search2 = st.columns(2)
    
    with col_search1:
        search_type = st.radio(
            "Buscar por:",
            ["Código", "Nombre", "Área"]
        )
    
    with col_search2:
        if search_type == "Código":
            search_term = st.text_input("Código del empleado", placeholder="EMP001")
        elif search_type == "Nombre":
            search_term = st.text_input("Nombre del empleado", placeholder="Carlos")
        else:  # Área
            areas = get_areas()
            search_term = st.selectbox("Seleccionar área", areas)
    
    if st.button("🔎 Buscar", type="primary", use_container_width=True):
        if search_term:
            try:
                conn = get_connection()
                
                if search_type == "Código":
                    query = "SELECT * FROM empleados WHERE codigo LIKE ?"
                    params = (f"%{search_term}%",)
                elif search_type == "Nombre":
                    query = "SELECT * FROM empleados WHERE nombre LIKE ?"
                    params = (f"%{search_term}%",)
                else:  # Área
                    query = "SELECT * FROM empleados WHERE area = ?"
                    params = (search_term,)
                
                resultados = pd.read_sql(query, conn, params=params)
                conn.close()
                
                if not resultados.empty:
                    st.success(f"✅ Encontrados {len(resultados)} empleados")
                    
                    for _, emp in resultados.iterrows():
                        with st.container():
                            st.markdown(f"""
                            <div class="employee-card">
                                <h4>{emp['nombre']} ({emp['codigo']})</h4>
                                <p><strong>Cargo:</strong> {emp['cargo']}</p>
                                <p><strong>Área:</strong> {emp['area']}</p>
                                <p><strong>Estado:</strong> {'✅ Activo' if emp['activo'] else '❌ Inactivo'}</p>
                                <p><strong>Teléfono:</strong> {emp['telefono'] or 'No registrado'}</p>
                                <p><strong>Email:</strong> {emp['email'] or 'No registrado'}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_act1, col_act2 = st.columns(2)
                            with col_act1:
                                if st.button("✏️ Editar", key=f"edit_result_{emp['id']}"):
                                    st.session_state.edit_employee_id = emp['id']
                                    st.session_state.page = 'editar_empleado'
                                    st.rerun()
                            with col_act2:
                                if st.button("📊 Ver ventas", key=f"sales_{emp['id']}"):
                                    st.info(f"Ventas de {emp['nombre']} (en desarrollo)")
                            
                            st.divider()
                else:
                    st.warning("No se encontraron empleados con los criterios de búsqueda")
                    
            except Exception as e:
                st.error(f"Error en la búsqueda: {e}")

def show_edit_employee():
    """Muestra el formulario para editar un empleado"""
    if 'edit_employee_id' not in st.session_state:
        st.error("No se ha seleccionado un empleado para editar")
        st.button("⬅️ Volver", on_click=lambda: setattr(st.session_state, 'page', 'empleados'))
        return
    
    employee_id = st.session_state.edit_employee_id
    empleado = get_employee_by_id(employee_id)
    
    if not empleado:
        st.error("Empleado no encontrado")
        st.button("⬅️ Volver", on_click=lambda: setattr(st.session_state, 'page', 'empleados'))
        return
    
    st.title(f"✏️ Editar Empleado: {empleado['nombre']}")
    
    with st.form("edit_employee_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Código (no editable)
            st.text_input("Código", value=empleado['codigo'], disabled=True)
            
            # Nombre
            nombre = st.text_input("Nombre completo*", value=empleado['nombre'])
            
            # Cargo
            cargos = get_cargos()
            cargo = st.selectbox(
                "Cargo*",
                options=cargos,
                index=cargos.index(empleado['cargo']) if empleado['cargo'] in cargos else 0
            )
            
            # Área
            areas = get_areas()
            area = st.selectbox(
                "Área*",
                options=areas,
                index=areas.index(empleado['area']) if empleado['area'] in areas else 0
            )
        
        with col2:
            # Fecha de ingreso
            fecha_ingreso = st.date_input(
                "Fecha de ingreso",
                value=pd.to_datetime(empleado['fecha_ingreso']).date()
            )
            
            # Teléfono
            telefono = st.text_input(
                "Teléfono",
                value=empleado['telefono'] if empleado['telefono'] else ""
            )
            
            # Email
            email = st.text_input(
                "Email",
                value=empleado['email'] if empleado['email'] else ""
            )
            
            # Estado
            activo = st.checkbox("Empleado activo", value=bool(empleado['activo']))
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            submitted = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
        
        with col_btn2:
            if st.form_submit_button("❌ Cancelar", type="secondary", use_container_width=True):
                st.session_state.page = 'empleados'
                st.rerun()
        
        if submitted:
            # Validaciones
            if not nombre:
                st.error("El nombre completo es requerido")
            else:
                # Actualizar empleado
                success, message = update_employee(
                    employee_id,
                    nombre=nombre,
                    cargo=cargo,
                    area=area,
                    fecha_ingreso=fecha_ingreso.isoformat(),
                    telefono=telefono if telefono else None,
                    email=email if email else None,
                    activo=1 if activo else 0
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                    st.session_state.page = 'empleados'
                    st.rerun()
                else:
                    st.error(message)

# ============================================================================
# PANTALLA DE LOGIN (simplificada)
# ============================================================================
def show_login():
    """Muestra la pantalla de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Gestión - Droguería Restrepo</h1>
        <h3>Iniciar Sesión</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if not check_database_tables():
        with st.spinner("Inicializando base de datos..."):
            init_database_complete()
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### 📝 Inicio de Sesión")
            st.info("**Credenciales:** Usuario: `admin` | Contraseña: `admin123`")
            
            with st.form("login_form"):
                username = st.text_input("Usuario", value="admin")
                password = st.text_input("Contraseña", type="password", value="admin123")
                
                if st.form_submit_button("🚪 Ingresar", type="primary", use_container_width=True):
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
# OTRAS PÁGINAS SIMPLIFICADAS
# ============================================================================
def show_home():
    """Muestra la página de inicio"""
    user = st.session_state.get('user')
    
    st.markdown(f"""
    <div class="main-header">
        <h1>🏥 Sistema de Gestión - Droguería Restrepo</h1>
        <p>Bienvenido, <strong>{user['nombre']}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        empleados = get_employees(filtro_activo=1)
        st.metric("👥 Empleados Activos", len(empleados) if not empleados.empty else 0)
    
    with col2:
        st.metric("📊 Tu Rol", user['rol'].capitalize())
    
    with col3:
        st.metric("🔑 Permisos", len(user['permisos']))

def show_profile():
    """Muestra el perfil del usuario"""
    user = st.session_state.get('user')
    st.title("👤 Mi Perfil")
    st.write(f"**Usuario:** {user['username']}")
    st.write(f"**Nombre:** {user['nombre']}")
    st.write(f"**Rol:** {user['rol']}")
    st.write(f"**Permisos:** {', '.join(user['permisos'])}")

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
        
        # Módulos de administración
        if has_permission(user, 'manage_employees') or has_permission(user, 'manage_users'):
            st.divider()
            st.markdown("### ⚙️ Administración")
            
            admin_options = []
            
            if has_permission(user, 'manage_users'):
                admin_options.append(("👥 Usuarios", "usuarios"))
            
            if has_permission(user, 'manage_employees'):
                admin_options.append(("👤 Empleados", "empleados"))
            
            admin_options.append(("📦 Productos", "productos"))
            
            for icon_text, page in admin_options:
                if st.button(icon_text, use_container_width=True, key=f"admin_{page}"):
                    st.session_state.page = page
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
    elif st.session_state.page == 'empleados':
        show_employee_management()
    elif st.session_state.page == 'editar_empleado':
        show_edit_employee()
    elif st.session_state.page == 'usuarios':
        st.title("👥 Gestión de Usuarios")
        st.info("Funcionalidad en desarrollo...")
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

# ============================================================================
# EJECUCIÓN
# ============================================================================
if __name__ == "__main__":
    main()