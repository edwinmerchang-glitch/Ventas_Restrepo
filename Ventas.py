import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3
import hashlib
import plotly.express as px
import plotly.graph_objects as go
import os

# ================= CONFIG =================
st.set_page_config(page_title="Sistema Comercial PRO", page_icon="📊", layout="wide")

# ================= ESTILO =================
st.markdown("""
<style>
    .big-title {font-size:40px;font-weight:700; margin-bottom:0;}
    .subtitle {color:gray;font-size:18px; margin-top:0;}
    .card {
        padding: 20px;
        border-radius: 10px;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        margin-bottom: 20px;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #0066cc;
    }
    .metric-label {
        font-size: 14px;
        color: #6c757d;
    }
    .success-message {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
</style>
""", unsafe_allow_html=True)

# ================= DB =================
def get_connection():
    return sqlite3.connect("ventas_pro_empresarial.db", check_same_thread=False)

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def crear_db():
    conn = get_connection()
    c = conn.cursor()

    # Tabla empleados (vendedores)
    c.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        email TEXT UNIQUE,
        departamento TEXT,
        area TEXT,
        fecha_registro DATE DEFAULT CURRENT_DATE
    )""")

    # Tabla ventas (adaptada al formulario de Forms)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATE,
        empleado_id INTEGER,
        vendedor TEXT,
        tipo_producto TEXT,
        numero_parte TEXT,
        unidades INTEGER,
        comentarios TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (empleado_id) REFERENCES empleados (id)
    )""")

    # Tabla usuarios
    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        empleado_id INTEGER UNIQUE,
        es_admin INTEGER DEFAULT 0,
        FOREIGN KEY (empleado_id) REFERENCES empleados (id)
    )""")

    # Tabla metas
    c.execute("""
    CREATE TABLE IF NOT EXISTS metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER,
        mes INTEGER,
        anio INTEGER,
        meta_unidades INTEGER,
        UNIQUE(empleado_id, mes, anio),
        FOREIGN KEY (empleado_id) REFERENCES empleados (id)
    )""")

    # Insertar admin si no existe
    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (username, password, es_admin) VALUES (?,?,1)",
                  ("admin", hash_password("admin123")))

    conn.commit()
    conn.close()

crear_db()

# ================= DATA FUNCTIONS =================
def get_empleados():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM empleados ORDER BY nombre", conn)
    conn.close()
    return df

def get_empleado_by_user(username):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT e.* FROM empleados e
        JOIN usuarios u ON e.id = u.empleado_id
        WHERE u.username = ?
    """, conn, params=(username,))
    conn.close()
    return df.iloc[0] if not df.empty else None

def get_usuarios():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT u.*, e.nombre as empleado_nombre 
        FROM usuarios u
        LEFT JOIN empleados e ON u.empleado_id = e.id
    """, conn)
    conn.close()
    return df

def validar_login(user, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password, es_admin, empleado_id FROM usuarios WHERE username=?",
        (user,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, None, None

    if row[0] == hash_password(password):
        return True, bool(row[1]), row[2]

    return False, None, None

def registrar_venta(fecha, empleado_id, vendedor, tipo_producto, numero_parte, unidades, comentarios=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO ventas 
        (fecha, empleado_id, vendedor, tipo_producto, numero_parte, unidades, comentarios)
        VALUES (?,?,?,?,?,?,?)
    """, (fecha, empleado_id, vendedor, tipo_producto, numero_parte, unidades, comentarios))
    conn.commit()
    conn.close()

def get_ventas(empleado_id=None, fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    query = """
        SELECT v.*, e.departamento, e.area 
        FROM ventas v
        JOIN empleados e ON v.empleado_id = e.id
        WHERE 1=1
    """
    params = []
    
    if empleado_id:
        query += " AND v.empleado_id = ?"
        params.append(empleado_id)
    
    if fecha_inicio:
        query += " AND v.fecha >= ?"
        params.append(fecha_inicio)
    
    if fecha_fin:
        query += " AND v.fecha <= ?"
        params.append(fecha_fin)
    
    query += " ORDER BY v.fecha DESC, v.fecha_registro DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def get_resumen_ventas(mes=None, anio=None):
    conn = get_connection()
    query = """
        SELECT 
            e.nombre,
            e.departamento,
            COUNT(DISTINCT v.id) as num_ventas,
            SUM(v.unidades) as total_unidades,
            v.tipo_producto,
            v.fecha
        FROM ventas v
        JOIN empleados e ON v.empleado_id = e.id
    """
    params = []
    
    if mes and anio:
        query += " WHERE strftime('%m', v.fecha) = ? AND strftime('%Y', v.fecha) = ?"
        params.append(f"{mes:02d}")
        params.append(str(anio))
    
    query += " GROUP BY e.nombre, v.tipo_producto"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def set_meta(emp_id, mes, anio, meta):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO metas (empleado_id, mes, anio, meta_unidades)
    VALUES (?,?,?,?)
    """, (emp_id, mes, anio, meta))
    conn.commit()
    conn.close()

def get_metas(mes, anio):
    conn = get_connection()
    df = pd.read_sql("""
    SELECT m.*, e.nombre, e.departamento 
    FROM metas m
    JOIN empleados e ON m.empleado_id = e.id
    WHERE mes=? AND anio=?
    ORDER BY e.nombre
    """, conn, params=(mes, anio))
    conn.close()
    return df

def crear_empleado(nombre, email, departamento, area):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO empleados (nombre, email, departamento, area)
            VALUES (?,?,?,?)
        """, (nombre, email, departamento, area))
        conn.commit()
        return True, c.lastrowid
    except sqlite3.IntegrityError:
        return False, None
    finally:
        conn.close()

def crear_usuario(username, password, empleado_id, es_admin=0):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO usuarios (username, password, empleado_id, es_admin)
            VALUES (?,?,?,?)
        """, (username, hash_password(password), empleado_id, es_admin))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ================= SESIÓN =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.admin = False
    st.session_state.username = None
    st.session_state.emp_id = None
    st.session_state.emp_data = None
    st.session_state.page = "Registro"

# ================= LOGIN =================
if not st.session_state.login:
    st.markdown('<div class="big-title">🔐 Sistema de Registro de Ventas</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Plataforma Empresarial - Equipo Comercial</div>', unsafe_allow_html=True)
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("### Iniciar Sesión")
            u = st.text_input("Usuario", placeholder="Ingresa tu usuario")
            p = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
            btn = st.form_submit_button("Ingresar", use_container_width=True)

        if btn:
            ok, adm, eid = validar_login(u, p)
            if ok:
                st.session_state.login = True
                st.session_state.admin = adm
                st.session_state.username = u
                st.session_state.emp_id = eid
                
                # Cargar datos del empleado
                if eid:
                    empleado = get_empleado_by_user(u)
                    st.session_state.emp_data = empleado
                
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

        with st.expander("🔑 Credenciales de prueba"):
            st.info("👑 **Admin:** usuario: admin | contraseña: admin123")
            st.info("👤 **Vendedor:** usuario: vendedor1 | contraseña: pass123 (si existe)")

    st.stop()

# ================= HEADER =================
st.markdown(f'<div class="big-title">📊 Sistema de Registro de Ventas</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">Usuario: {st.session_state.username} | {"👑 Administrador" if st.session_state.admin else "👤 Vendedor"}</div>', unsafe_allow_html=True)
st.divider()

# ================= FUNCIONES DE PÁGINAS =================
def pagina_registro_ventas():
    st.markdown("### 📝 Registrar Nueva Venta")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    with st.form("form_venta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha = st.date_input("📅 Fecha de la venta", value=date.today())
            
            # El vendedor se autocompleta si es empleado normal
            if st.session_state.admin:
                empleados = get_empleados()
                vendedor = st.selectbox("👤 Vendedor", empleados["nombre"].tolist() if not empleados.empty else [])
            else:
                vendedor = st.text_input("👤 Tu nombre", value=st.session_state.emp_data["nombre"] if st.session_state.emp_data is not None else "", disabled=True)
        
        with col2:
            tipo_producto = st.selectbox(
                "📦 Tipo de Producto",
                ["Selecciona un tipo", "RX", "Generador", "Batería", "Otro"],
                index=0
            )
            
            numero_parte = st.text_input("🔢 Número de Parte", placeholder="Ej: RX-2024-001")
        
        unidades = st.number_input("📊 Unidades Vendidas", min_value=1, value=1, step=1)
        
        comentarios = st.text_area("📝 Comentarios (opcional)", placeholder="Agrega algún comentario sobre la venta...")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("💾 Guardar Venta", use_container_width=True)
    
    if submitted:
        if tipo_producto == "Selecciona un tipo":
            st.error("❌ Por favor selecciona un tipo de producto")
        elif not numero_parte:
            st.error("❌ El número de parte es obligatorio")
        else:
            # Obtener empleado_id
            if st.session_state.admin:
                empleado_data = empleados[empleados["nombre"] == vendedor].iloc[0]
                emp_id = empleado_data["id"]
            else:
                emp_id = st.session_state.emp_id
            
            registrar_venta(
                fecha=fecha,
                empleado_id=emp_id,
                vendedor=vendedor,
                tipo_producto=tipo_producto,
                numero_parte=numero_parte,
                unidades=unidades,
                comentarios=comentarios
            )
            
            st.markdown('<div class="success-message">✅ ¡Venta registrada exitosamente!</div>', unsafe_allow_html=True)
            st.balloons()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Mostrar últimas ventas del usuario
    st.markdown("### 📋 Mis Últimas Ventas")
    
    if st.session_state.admin:
        ventas = get_ventas(fecha_inicio=date.today().replace(day=1))
    else:
        ventas = get_ventas(empleado_id=st.session_state.emp_id, fecha_inicio=date.today().replace(day=1))
    
    if not ventas.empty:
        ventas_show = ventas[['fecha', 'vendedor', 'tipo_producto', 'numero_parte', 'unidades']].head(10)
        ventas_show['fecha'] = pd.to_datetime(ventas_show['fecha']).dt.strftime('%d/%m/%Y')
        ventas_show.columns = ['Fecha', 'Vendedor', 'Producto', 'N° Parte', 'Unidades']
        st.dataframe(ventas_show, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No hay ventas registradas este mes")

def pagina_mis_metas():
    st.markdown("### 🎯 Mis Metas Comerciales")
    
    if st.session_state.emp_id:
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        # Obtener ventas del mes
        ventas = get_ventas(empleado_id=st.session_state.emp_id)
        if not ventas.empty:
            ventas['fecha'] = pd.to_datetime(ventas['fecha'])
            ventas_mes = ventas[
                (ventas['fecha'].dt.month == mes_actual) & 
                (ventas['fecha'].dt.year == anio_actual)
            ]
            total_ventas = ventas_mes['unidades'].sum() if not ventas_mes.empty else 0
        else:
            total_ventas = 0
        
        # Obtener meta del mes
        conn = get_connection()
        meta_df = pd.read_sql("""
            SELECT meta_unidades FROM metas 
            WHERE empleado_id = ? AND mes = ? AND anio = ?
        """, conn, params=(st.session_state.emp_id, mes_actual, anio_actual))
        conn.close()
        
        meta = meta_df['meta_unidades'].iloc[0] if not meta_df.empty else 0
        
        # Mostrar progreso
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{total_ventas}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Ventas Actuales</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{meta}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Meta del Mes</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            progreso = (total_ventas / meta * 100) if meta > 0 else 0
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{progreso:.1f}%</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Progreso</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Barra de progreso
        st.progress(min(progreso/100, 1.0))
        
        if progreso >= 100:
            st.success("🎉 ¡Felicidades! Has superado tu meta mensual")
        elif progreso >= 75:
            st.info("💪 ¡Vas por buen camino! Sigue así")
        else:
            st.warning("📈 Aún puedes lograr tu meta, ¡a seguir vendiendo!")
    else:
        st.warning("No tienes un perfil de empleado asociado")

def pagina_admin_empleados():
    st.markdown("### 👥 Gestión de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["➕ Nuevo Empleado", "📋 Lista Empleados", "👤 Crear Usuario"])
    
    with tab1:
        with st.form("nuevo_empleado"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre = st.text_input("Nombre completo")
                email = st.text_input("Email")
            
            with col2:
                # CAMBIADO: Nuevos departamentos
                departamento = st.selectbox(
                    "Departamento", 
                    ["Droguería", "Equipos Médicos", "Tienda", "Cajas"]
                )
                area = st.text_input("Área específica")
            
            submitted = st.form_submit_button("Crear Empleado", use_container_width=True)
            
            if submitted and nombre and email:
                success, emp_id = crear_empleado(nombre, email, departamento, area)
                if success:
                    st.success(f"✅ Empleado {nombre} creado correctamente")
                else:
                    st.error("❌ Error: El empleado ya existe o el email está duplicado")
    
    with tab2:
        empleados = get_empleados()
        if not empleados.empty:
            st.dataframe(empleados, use_container_width=True, hide_index=True)
        else:
            st.info("No hay empleados registrados")
    
    with tab3:
        st.markdown("#### Crear usuario para empleado")
        empleados = get_empleados()
        
        if not empleados.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                empleado = st.selectbox("Seleccionar empleado", empleados["nombre"].tolist())
                username = st.text_input("Nombre de usuario")
            
            with col2:
                password = st.text_input("Contraseña", type="password")
                es_admin = st.checkbox("Es administrador")
            
            if st.button("Crear Usuario", use_container_width=True):
                emp_data = empleados[empleados["nombre"] == empleado].iloc[0]
                success = crear_usuario(username, password, emp_data["id"], 1 if es_admin else 0)
                
                if success:
                    st.success(f"✅ Usuario {username} creado para {empleado}")
                else:
                    st.error("❌ Error: El usuario ya existe o el empleado ya tiene usuario")
        else:
            st.warning("Primero debes crear empleados")

def pagina_dashboard():
    st.markdown("### 📊 Dashboard Comercial")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        mes = st.selectbox("Mes", range(1, 13), index=datetime.now().month-1,
                          format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
    with col2:
        anio = st.number_input("Año", 2024, 2100, datetime.now().year)
    with col3:
        if st.session_state.admin:
            empleados = get_empleados()
            empleado_filtro = st.selectbox("Empleado", ["Todos"] + empleados["nombre"].tolist())
        else:
            empleado_filtro = "Todos"
    
    # Obtener datos
    ventas = get_ventas()
    if not ventas.empty:
        ventas['fecha'] = pd.to_datetime(ventas['fecha'])
        ventas_filtradas = ventas[
            (ventas['fecha'].dt.month == mes) & 
            (ventas['fecha'].dt.year == anio)
        ]
        
        if empleado_filtro != "Todos" and st.session_state.admin:
            ventas_filtradas = ventas_filtradas[ventas_filtradas['vendedor'] == empleado_filtro]
        
        if not ventas_filtradas.empty:
            # Métricas principales
            total_unidades = ventas_filtradas['unidades'].sum()
            total_ventas = len(ventas_filtradas)
            vendedores_activos = ventas_filtradas['vendedor'].nunique()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📦 Unidades Vendidas", f"{total_unidades:,}")
            col2.metric("📝 N° Ventas", total_ventas)
            col3.metric("👥 Vendedores", vendedores_activos)
            col4.metric("📊 Promedio x Venta", f"{total_unidades/total_ventas:.1f}")
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                # Ventas por tipo de producto
                ventas_tipo = ventas_filtradas.groupby('tipo_producto')['unidades'].sum().reset_index()
                fig_tipo = px.pie(ventas_tipo, values='unidades', names='tipo_producto',
                                 title='Distribución por Tipo de Producto',
                                 color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig_tipo, use_container_width=True)
            
            with col2:
                # Top vendedores
                top_vendedores = ventas_filtradas.groupby('vendedor')['unidades'].sum().nlargest(5).reset_index()
                fig_top = px.bar(top_vendedores, x='vendedor', y='unidades',
                                title='Top 5 Vendedores del Mes',
                                color='unidades', color_continuous_scale='Viridis')
                st.plotly_chart(fig_top, use_container_width=True)
            
            # Ventas diarias
            ventas_diarias = ventas_filtradas.groupby('fecha')['unidades'].sum().reset_index()
            fig_diario = px.line(ventas_diarias, x='fecha', y='unidades',
                                title='Evolución Diaria de Ventas',
                                markers=True)
            st.plotly_chart(fig_diario, use_container_width=True)
            
            # NUEVO: Gráfico por departamento
            st.markdown("### 📊 Ventas por Departamento")
            ventas_departamento = ventas_filtradas.groupby('departamento')['unidades'].sum().reset_index()
            
            col1, col2 = st.columns(2)
            with col1:
                fig_dep = px.bar(ventas_departamento, x='departamento', y='unidades',
                                title='Ventas por Departamento',
                                color='departamento',
                                color_discrete_map={
                                    'Droguería': '#FF6B6B',
                                    'Equipos Médicos': '#4ECDC4',
                                    'Tienda': '#45B7D1',
                                    'Cajas': '#96CEB4'
                                })
                st.plotly_chart(fig_dep, use_container_width=True)
            
            with col2:
                fig_dep_pie = px.pie(ventas_departamento, values='unidades', names='departamento',
                                    title='Distribución por Departamento',
                                    color='departamento',
                                    color_discrete_map={
                                        'Droguería': '#FF6B6B',
                                        'Equipos Médicos': '#4ECDC4',
                                        'Tienda': '#45B7D1',
                                        'Cajas': '#96CEB4'
                                    })
                st.plotly_chart(fig_dep_pie, use_container_width=True)
            
            # Tabla detallada
            st.markdown("### 📋 Detalle de Ventas")
            detalle = ventas_filtradas[['fecha', 'vendedor', 'departamento', 'tipo_producto', 'numero_parte', 'unidades', 'comentarios']]
            detalle['fecha'] = detalle['fecha'].dt.strftime('%d/%m/%Y')
            st.dataframe(detalle, use_container_width=True, hide_index=True)
        else:
            st.info("No hay ventas para el período seleccionado")
    else:
        st.info("No hay ventas registradas en el sistema")

def pagina_admin_metas():
    st.markdown("### 🎯 Gestión de Metas")
    
    empleados = get_empleados()
    if empleados.empty:
        st.warning("⚠️ No hay empleados registrados")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.selectbox("👤 Empleado", empleados["nombre"])
        emp = empleados[empleados["nombre"] == nombre].iloc[0]
    
    with col2:
        mes = st.selectbox("📅 Mes", range(1, 13), 
                          format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
        anio = st.number_input("📆 Año", 2024, 2100, datetime.now().year)
    
    meta = st.number_input("🎯 Meta en Unidades", min_value=0, value=1000, step=100)
    
    if st.button("💾 Guardar Meta", use_container_width=True):
        set_meta(emp["id"], mes, anio, meta)
        st.success(f"✅ Meta asignada a {nombre} para {mes}/{anio}")
    
    st.divider()
    st.subheader("📋 Metas Registradas")
    metas_df = get_metas(mes, anio)
    if not metas_df.empty:
        st.dataframe(metas_df[['nombre', 'departamento', 'meta_unidades']], 
                    column_config={
                        "nombre": "Empleado",
                        "departamento": "Departamento",
                        "meta_unidades": "Meta"
                    },
                    use_container_width=True,
                    hide_index=True)
    else:
        st.info(f"ℹ️ No hay metas registradas para {mes}/{anio}")

def pagina_ranking():
    st.markdown("### 🏆 Ranking de Ventas")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox("Seleccionar Mes", range(1, 13), 
                          index=datetime.now().month-1,
                          format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
                          key="ranking_mes")
    with col2:
        anio = st.number_input("Año", 2024, 2100, datetime.now().year, key="ranking_anio")
    
    # Obtener datos
    ventas = get_ventas()
    if not ventas.empty:
        ventas['fecha'] = pd.to_datetime(ventas['fecha'])
        ventas_mes = ventas[
            (ventas['fecha'].dt.month == mes) & 
            (ventas['fecha'].dt.year == anio)
        ]
        
        if not ventas_mes.empty:
            # Ranking por vendedor
            ranking = ventas_mes.groupby('vendedor').agg({
                'unidades': 'sum',
                'id': 'count',
                'departamento': 'first'
            }).reset_index()
            ranking.columns = ['Vendedor', 'Unidades', 'Ventas', 'Departamento']
            ranking = ranking.sort_values('Unidades', ascending=False).reset_index(drop=True)
            ranking['Posición'] = ranking.index + 1
            
            # Métricas del ranking
            col1, col2, col3 = st.columns(3)
            col1.metric("🥇 1er Lugar", f"{ranking.iloc[0]['Vendedor']} ({ranking.iloc[0]['Unidades']} uds)")
            col2.metric("📊 Total Vendedores", len(ranking))
            col3.metric("📦 Total Unidades", f"{ranking['Unidades'].sum():,}")
            
            # Ranking por departamento
            st.markdown("### 📊 Ranking por Departamento")
            deptos = ventas_mes.groupby('departamento')['unidades'].sum().reset_index()
            
            col1, col2 = st.columns(2)
            with col1:
                fig_depto = px.bar(deptos, x='departamento', y='unidades',
                                  title='Ventas por Departamento',
                                  color='departamento',
                                  color_discrete_map={
                                      'Droguería': '#FF6B6B',
                                      'Equipos Médicos': '#4ECDC4',
                                      'Tienda': '#45B7D1',
                                      'Cajas': '#96CEB4'
                                  })
                st.plotly_chart(fig_depto, use_container_width=True)
            
            with col2:
                st.dataframe(
                    deptos.sort_values('unidades', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "departamento": "Departamento",
                        "unidades": "Unidades Vendidas"
                    }
                )
            
            # Tabla de ranking general
            st.markdown("### 📋 Ranking General")
            st.dataframe(
                ranking[['Posición', 'Vendedor', 'Departamento', 'Unidades', 'Ventas']],
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico
            fig = px.bar(ranking.head(10), 
                        x='Vendedor', 
                        y='Unidades',
                        title=f'🏆 Top 10 - {datetime(2000, mes, 1).strftime("%B")} {anio}',
                        color='Departamento',
                        color_discrete_map={
                            'Droguería': '#FF6B6B',
                            'Equipos Médicos': '#4ECDC4',
                            'Tienda': '#45B7D1',
                            'Cajas': '#96CEB4'
                        },
                        text='Unidades')
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No hay ventas para {datetime(2000, mes, 1).strftime('%B')} {anio}")
    else:
        st.info("No hay ventas registradas en el sistema")

def pagina_exportar():
    st.markdown("### 📤 Exportar Datos")
    
    ventas = get_ventas()
    
    if ventas.empty:
        st.warning("⚠️ No hay datos para exportar")
        return
    
    # Filtros
    with st.expander("🔍 Filtros de exportación", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=ventas['fecha'].min() if not ventas.empty else date.today())
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today())
        
        if st.session_state.admin:
            empleados = ["Todos"] + ventas['vendedor'].unique().tolist()
            vendedor_filtro = st.selectbox("Vendedor", empleados)
            
            # NUEVO: Filtro por departamento
            departamentos = ["Todos"] + ventas['departamento'].unique().tolist()
            depto_filtro = st.selectbox("Departamento", departamentos)
        else:
            vendedor_filtro = "Todos"
            depto_filtro = "Todos"
    
    # Aplicar filtros
    ventas_filtradas = ventas.copy()
    ventas_filtradas['fecha'] = pd.to_datetime(ventas_filtradas['fecha'])
    ventas_filtradas = ventas_filtradas[
        (ventas_filtradas['fecha'].dt.date >= fecha_desde) &
        (ventas_filtradas['fecha'].dt.date <= fecha_hasta)
    ]
    
    if vendedor_filtro != "Todos" and st.session_state.admin:
        ventas_filtradas = ventas_filtradas[ventas_filtradas['vendedor'] == vendedor_filtro]
    
    if depto_filtro != "Todos" and st.session_state.admin:
        ventas_filtradas = ventas_filtradas[ventas_filtradas['departamento'] == depto_filtro]
    
    if ventas_filtradas.empty:
        st.warning("No hay datos con los filtros seleccionados")
        return
    
    # Vista previa
    st.subheader("📋 Vista Previa")
    preview = ventas_filtradas[['fecha', 'vendedor', 'departamento', 'tipo_producto', 'numero_parte', 'unidades']].head(10)
    preview['fecha'] = pd.to_datetime(preview['fecha']).dt.strftime('%d/%m/%Y')
    preview.columns = ['Fecha', 'Vendedor', 'Departamento', 'Producto', 'N° Parte', 'Unidades']
    st.dataframe(preview, use_container_width=True, hide_index=True)
    st.caption(f"Mostrando 10 de {len(ventas_filtradas)} registros")
    
    # Botones de exportación
    col1, col2 = st.columns(2)
    
    with col1:
        csv = ventas_filtradas.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar CSV",
            csv,
            file_name=f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Excel
        output = pd.ExcelWriter('temp.xlsx', engine='openpyxl')
        ventas_filtradas.to_excel(output, index=False, sheet_name='Ventas')
        output.close()
        with open('temp.xlsx', 'rb') as f:
            st.download_button(
                "📥 Descargar Excel",
                f,
                file_name=f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        os.remove('temp.xlsx')

# ================= MENÚ PRINCIPAL =================
# Sidebar para navegación
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    st.markdown(f"**Rol:** {'👑 Administrador' if st.session_state.admin else '👤 Vendedor'}")
    st.divider()
    
    # Menú basado en el rol
    menu_options = []
    
    if st.session_state.admin:
        menu_options = [
            "📝 Registrar Venta",
            "📊 Dashboard",
            "👥 Empleados",
            "🎯 Metas",
            "🏆 Ranking",
            "📤 Exportar"
        ]
    else:
        menu_options = [
            "📝 Registrar Venta",
            "🎯 Mis Metas",
            "📤 Exportar Mis Ventas"
        ]
    
    selected = st.radio("Navegación", menu_options)
    
    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ================= CONTENIDO PRINCIPAL =================
if selected == "📝 Registrar Venta":
    pagina_registro_ventas()
elif selected == "📊 Dashboard":
    pagina_dashboard()
elif selected == "👥 Empleados":
    pagina_admin_empleados()
elif selected == "🎯 Metas":
    if st.session_state.admin:
        pagina_admin_metas()
    else:
        pagina_mis_metas()
elif selected == "🏆 Ranking":
    pagina_ranking()
elif selected == "📤 Exportar":
    pagina_exportar()
elif selected == "📤 Exportar Mis Ventas":
    # Versión simplificada para empleados
    ventas = get_ventas(empleado_id=st.session_state.emp_id)
    if not ventas.empty:
        csv = ventas.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar Mis Ventas",
            csv,
            file_name=f"mis_ventas_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No tienes ventas registradas")