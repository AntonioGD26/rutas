import streamlit as st
from datetime import datetime
from db import db
from auth import verify_password
from modulos.dashboard import show_dashboard
from modulos.operacion import show_operacion

# Configuración de la página
st.set_page_config(
    page_title="RUTAS",
    page_icon="🚙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar variables de sesión
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = "➡️ Dashboard"

# Migración: si la página guardada ya no existe, resetear a Dashboard
menu_options = ["➡️ Dashboard", "🛠️ Operación"]
if st.session_state.page not in menu_options:
    st.session_state.page = "➡️ Dashboard"

# CSS personalizado (se mantiene igual)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #000000;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
    }
    .widget-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: all 0.3s;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .widget-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transform: translateY(-2px);
        cursor: pointer;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
    .button-primary {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .button-primary:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .dataframe {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# --- PÁGINA DE LOGIN (si no está autenticado) ---
if not st.session_state.authenticated:
    st.markdown('<h1 class="main-header">🔐 Inicio de Sesión</h1>', unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")

    if submitted:
        if not username or not password:
            st.error("Por favor ingrese usuario y contraseña")
        else:
            user = db.get_user(username)
            if user and verify_password(password, user['password_hash']):
                st.session_state.authenticated = True
                st.session_state.user = {
                    'id': user['id'],
                    'username': user['username'],
                    'nombre': user['nombre'],
                    'rol': user['rol']
                }
                st.success(f"Bienvenido {user['nombre'] or user['username']}")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    
    # Detener la ejecución aquí para usuarios no autenticados
    st.stop()

# --- USUARIO AUTENTICADO: mostrar barra lateral y contenido ---

# Barra lateral (solo visible para usuarios autenticados)
with st.sidebar:
    st.title("🔧 Navegación")

    # Selectbox para navegación automática
    selected_page = st.selectbox(
        "Seleccionar página",
        menu_options,
        index=menu_options.index(st.session_state.page) if st.session_state.page in menu_options else 0,
        key="nav_select"
    )
    
    # Si la selección cambia, actualizar la página y recargar
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()

    st.divider()
    st.caption(f"© {datetime.now().year} Sistema de Gestión")

    # Información del usuario y botón de logout
    st.write(f"👤 Usuario: {st.session_state.user['nombre'] or st.session_state.user['username']}")
    st.write(f"📋 Rol: {st.session_state.user['rol']}")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()
    st.divider()

# Enrutamiento a las páginas según la selección
if st.session_state.page == "➡️ Dashboard":
    show_dashboard()
elif st.session_state.page == "🛠️ Operación":
    show_operacion()

# Footer
st.divider()
st.caption(f"© {datetime.now().year} Sistema de Gestión de Visitas Técnicas | Versión 2.0")