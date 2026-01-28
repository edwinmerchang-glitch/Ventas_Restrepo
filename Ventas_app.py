# ventas_app.py - Aplicación completa de gestión de ventas
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import date, datetime, timedelta

# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================
st.set_page_config(
    page_title="Sistema de Ventas Restrepo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
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
</style>
""", unsafe_allow_html=True)

# ============================================================================
# BASE DE DATOS
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
            # Crear tablas
            create_tables(conn)
            st.success("✅ Base de datos inicializada correctamente")
        else:
            st.info("Base de datos ya existe")
            
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error al inicializar la base de datos: {e}")
        return False

def create_tables(conn=None):
    """Crea las tablas necesarias"""
    close_conn = False
    try:
        if conn is None:
            conn = get_connection()
            close_conn = True
            
        c = conn.cursor()
        
        # Tabla de ventas
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
            valor REAL NOT NULL CHECK (valor >= 0),
            ticket INTEGER UNIQUE NOT NULL,
            cantidad_total INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Tabla de detalle de ventas (unidades por producto)
        c.execute("""
        CREATE TABLE IF NOT EXISTS ventas_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_medida TEXT NOT NULL,
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            precio_unitario REAL NOT NULL CHECK (precio_unitario > 0),
            subtotal REAL NOT NULL CHECK (subtotal >= 0),
            FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
        )
        """)
        
        # Tabla de productos/inventario
        c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_medida TEXT NOT NULL,
            precio REAL NOT NULL CHECK (precio > 0),
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
    """Inserta datos iniciales en la base de datos"""
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
        
        # Insertar productos de ejemplo si la tabla está vacía
        c.execute("SELECT COUNT(*) as count FROM productos")
        if c.fetchone()[0] == 0:
            productos = [
                ("MED001", "Paracetamol 500mg", "Medicamentos", "Caja", 15000.0, 100),
                ("MED002", "Ibuprofeno 400mg", "Medicamentos", "Caja", 18000.0, 80),
                ("MED003", "Amoxicilina 500mg", "Medicamentos", "Frasco", 25000.0, 50),
                ("HIG001", "Jabón Antibacterial", "Higiene", "Unidad", 5000.0, 200),
                ("HIG002", "Alcohol Antiséptico", "Higiene", "Botella", 12000.0, 150),
                ("HIG003", "Tapabocas N95", "Higiene", "Caja", 30000.0, 75),
                ("BEB001", "Agua Mineral 600ml", "Bebidas", "Botella", 2500.0, 300),
                ("BEB002", "Gatorade 500ml", "Bebidas", "Botella", 4500.0, 150),
                ("EQU001", "Termómetro Digital", "Equipos", "Unidad", 35000.0, 30),
                ("EQU002", "Tensiómetro", "Equipos", "Unidad", 85000.0, 15),
                ("COS001", "Protector Solar 50FPS", "Cosmética", "Tubo", 28000.0, 60),
                ("COS002", "Crema Hidratante", "Cosmética", "Frasco", 22000.0, 70)
            ]
            c.executemany(
                """INSERT OR IGNORE INTO productos 
                (codigo, nombre, categoria, unidad_medida, precio, stock) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                productos
            )
        
        conn.commit()
        
    except Exception as e:
        st.error(f"Error al insertar datos iniciales: {e}")

def add_sample_sales():
    """Agrega ventas de ejemplo para pruebas"""
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
        c.execute("SELECT codigo, nombre, categoria, unidad_medida, precio FROM productos LIMIT 5")
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
                
                # Crear venta principal
                c.execute("""
                    INSERT INTO ventas 
                    (fecha, anio, mes, dia, empleado, cargo, area, 
                     tipo_venta, canal, valor, ticket, cantidad_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    0,  # Se calculará después
                    ticket_base,
                    0   # Se calculará después
                ))
                
                venta_id = c.lastrowid
                valor_total = 0
                cantidad_total = 0
                
                # Agregar productos a la venta
                for prod_idx, producto in enumerate(productos[:3]):  # Máximo 3 productos por venta
                    cantidad = (emp_idx * 2) + prod_idx + 1
                    subtotal = cantidad * producto[4]  # precio
                    
                    c.execute("""
                        INSERT INTO ventas_detalle 
                        (venta_id, producto, categoria, unidad_medida, cantidad, precio_unitario, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        venta_id,
                        producto[1],  # nombre
                        producto[2],  # categoria
                        producto[3],  # unidad_medida
                        cantidad,
                        producto[4],  # precio
                        subtotal
                    ))
                    
                    valor_total += subtotal
                    cantidad_total += cantidad
                
                # Actualizar la venta con el total
                c.execute("""
                    UPDATE ventas 
                    SET valor = ?, cantidad_total = ?
                    WHERE id = ?
                """, (valor_total, cantidad_total, venta_id))
        
        conn.commit()
        st.success(f"✅ Ventas de ejemplo agregadas")
        
    except Exception as e:
        st.error(f"Error al agregar ventas de ejemplo: {e}")
    finally:
        if conn:
            conn.close()

def get_products():
    """Obtiene la lista de productos disponibles"""
    try:
        conn = get_connection()
        productos = pd.read_sql("""
            SELECT codigo, nombre, categoria, unidad_medida, precio, stock 
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
                'precio': row['precio'],
                'stock': row['stock']
            }
        
        return productos, product_dict
    except Exception as e:
        st.error(f"Error al obtener productos: {e}")
        return pd.DataFrame(), {}

# ============================================================================
# PÁGINA PRINCIPAL / INICIO
# ============================================================================
def show_home():
    """Muestra la página de inicio"""
    st.markdown("""
    <div class="main-header">
        <h1>🏥 Sistema de Gestión de Ventas</h1>
        <h3>Droguería Restrepo</h3>
        <p>Registro de unidades vendidas por el equipo de trabajo</p>
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
    
    # Estadísticas rápidas
    st.header("📈 Estadísticas del Equipo")
    
    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Venta Total", f"${stats['venta_total']:,.0f}")
    
    with col2:
        st.metric("📦 Unidades Vendidas", f"{stats['unidades_total']:,.0f}")
    
    with col3:
        st.metric("👥 Empleados Activos", stats['empleados_count'])
    
    with col4:
        if stats['unidades_total'] > 0:
            prom_valor = stats['venta_total'] / stats['unidades_total']
            st.metric("📊 Valor Promedio/Unidad", f"${prom_valor:,.0f}")
        else:
            st.metric("📊 Valor Promedio/Unidad", "$0")
    
    # Top productos
    try:
        conn = get_connection()
        top_productos = pd.read_sql("""
            SELECT 
                producto,
                SUM(cantidad) as unidades_vendidas,
                SUM(subtotal) as valor_total
            FROM ventas_detalle
            GROUP BY producto
            ORDER BY unidades_vendidas DESC
            LIMIT 5
        """, conn)
        
        if not top_productos.empty:
            st.header("🏆 Productos Más Vendidos")
            
            for idx, row in top_productos.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"**{row['producto']}**")
                with col2:
                    st.write(f"📦 {int(row['unidades_vendidas'])} unidades")
                with col3:
                    st.write(f"💰 ${row['valor_total']:,.0f}")
                st.divider()
        
        conn.close()
        
    except Exception as e:
        st.info("No hay datos de productos vendidos aún")

# ============================================================================
# PÁGINA DE REGISTRO DE VENTAS
# ============================================================================
def show_registro():
    """Muestra la página de registro de ventas con unidades"""
    st.title("📝 Registro de Ventas por Unidades")
    
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
        st.subheader("🛒 Productos Vendidos")
        
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
                st.text_input("Precio unitario", value=f"${producto_info['precio']:,.0f}", disabled=True)
                st.text_input("Stock disponible", value=producto_info['stock'], disabled=True)
        
        with col_prod3:
            if producto_seleccionado:
                cantidad = st.number_input(
                    "Cantidad",
                    min_value=1,
                    max_value=productos_dict[producto_seleccionado]['stock'],
                    step=1,
                    value=1
                )
                
                if st.button("➕ Agregar producto", type="secondary"):
                    producto_info = productos_dict[producto_seleccionado]
                    subtotal = cantidad * producto_info['precio']
                    
                    nuevo_producto = {
                        'codigo': producto_seleccionado,
                        'nombre': producto_info['nombre'],
                        'categoria': producto_info['categoria'],
                        'unidad': producto_info['unidad'],
                        'cantidad': cantidad,
                        'precio_unitario': producto_info['precio'],
                        'subtotal': subtotal
                    }
                    
                    st.session_state.productos_venta.append(nuevo_producto)
                    st.success(f"✅ {cantidad} {producto_info['unidad']} de {producto_info['nombre']} agregados")
                    st.rerun()
        
        # Mostrar productos agregados
        if st.session_state.productos_venta:
            st.divider()
            st.subheader("📋 Resumen de productos")
            
            total_unidades = 0
            total_valor = 0
            
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
                    st.write(f"Cantidad: {producto['cantidad']}")
                
                with col_res3:
                    st.write(f"Subtotal: ${producto['subtotal']:,.0f}")
                
                with col_res4:
                    if st.button("❌", key=f"eliminar_{i}"):
                        st.session_state.productos_venta.pop(i)
                        st.rerun()
                
                total_unidades += producto['cantidad']
                total_valor += producto['subtotal']
            
            # Mostrar totales
            st.markdown(f"""
            <div class="total-box">
                <h3>Total de la venta</h3>
                <p><strong>Unidades totales:</strong> {total_unidades}</p>
                <p><strong>Valor total:</strong> ${total_valor:,.0f}</p>
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
                    
                    # Registrar venta principal
                    c.execute("""
                        INSERT INTO ventas 
                        (fecha, anio, mes, dia, empleado, cargo, area, 
                         tipo_venta, canal, valor, ticket, cantidad_total)
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
                        total_valor,
                        ticket,
                        total_unidades
                    ))
                    
                    venta_id = c.lastrowid
                    
                    # Registrar detalles de productos
                    for producto in st.session_state.productos_venta:
                        c.execute("""
                            INSERT INTO ventas_detalle 
                            (venta_id, producto, categoria, unidad_medida, 
                             cantidad, precio_unitario, subtotal)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            venta_id,
                            producto['nombre'],
                            producto['categoria'],
                            producto['unidad'],
                            producto['cantidad'],
                            producto['precio_unitario'],
                            producto['subtotal']
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
                            st.write(f"- **Valor total:** ${total_valor:,.0f}")
                    
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
    """Obtiene estadísticas generales"""
    stats = {
        'venta_total': 0,
        'unidades_total': 0,
        'empleados_count': 0,
        'ticket_promedio': 0
    }
    
    try:
        conn = get_connection()
        if conn is None:
            return stats
            
        # Venta total
        df_total = pd.read_sql("SELECT COALESCE(SUM(valor), 0) as total FROM ventas", conn)
        stats['venta_total'] = float(df_total['total'].iloc[0])
        
        # Unidades totales
        df_unidades = pd.read_sql("SELECT COALESCE(SUM(cantidad_total), 0) as unidades FROM ventas", conn)
        stats['unidades_total'] = int(df_unidades['unidades'].iloc[0])
        
        # Empleados activos
        df_empleados = pd.read_sql("SELECT COUNT(DISTINCT empleado) as empleados FROM ventas", conn)
        stats['empleados_count'] = int(df_empleados['empleados'].iloc[0])
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error al obtener estadísticas: {e}")
        
    return stats

# ============================================================================
# SIDEBAR - NAVEGACIÓN PRINCIPAL
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h2>🏥 Droguería Restrepo</h2>
        <p style="color: #666; font-size: 0.9rem;">Registro de Unidades Vendidas</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Estado de la página
    if 'page' not in st.session_state:
        st.session_state.page = 'inicio'
    
    # Navegación
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
    
    # Módulos
    st.markdown("### 📂 Módulos")
    
    if st.button("📝 Registrar Ventas", use_container_width=True, 
                 help="Registrar unidades vendidas por el equipo"):
        st.session_state.page = 'registro'
        st.rerun()
    
    if st.button("📊 Ver Informes", use_container_width=True,
                 help="Ver reportes y estadísticas"):
        st.session_state.page = 'informes'
        st.rerun()
    
    st.divider()
    
    # Estadísticas del día
    st.markdown("### 📊 Hoy")
    
    try:
        conn = get_connection()
        hoy = date.today().strftime("%Y-%m-%d")
        
        stats_hoy = pd.read_sql(f"""
            SELECT 
                COUNT(*) as ventas,
                COALESCE(SUM(cantidad_total), 0) as unidades,
                COALESCE(SUM(valor), 0) as total
            FROM ventas 
            WHERE fecha = '{hoy}'
        """, conn)
        
        col_today1, col_today2, col_today3 = st.columns(3)
        with col_today1:
            st.metric("Ventas", int(stats_hoy['ventas'].iloc[0]))
        with col_today2:
            st.metric("Unidades", int(stats_hoy['unidades'].iloc[0]))
        with col_today3:
            st.metric("Total", f"${float(stats_hoy['total'].iloc[0]):,.0f}")
            
        conn.close()
        
    except:
        st.info("No hay ventas hoy")

# ============================================================================
# CONTENIDO PRINCIPAL
# ============================================================================
if st.session_state.page == 'inicio':
    show_home()
elif st.session_state.page == 'registro':
    show_registro()
elif st.session_state.page == 'informes':
    # La función show_informes() sigue igual que en tu código original
    # Solo asegúrate de que exista en tu código
    pass

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p><strong>🏥 Sistema de Registro de Unidades Vendidas</strong></p>
    <p>© 2024 | Versión 2.0 | Para equipo de trabajo</p>
</div>
""", unsafe_allow_html=True)