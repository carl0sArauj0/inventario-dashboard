import streamlit as st
import pandas as pd
from database import obtener_resumen_mensual


def verificar_credenciales(usuario, password):
    # Validación simple de credenciales. Actualiza según tu lógica de autenticación.
    return usuario == "admin" and password == "admin123"


# 1. Configuración de página 
st.set_page_config(
    page_title="Cafetería - Login",
    page_icon="☕",
    layout="wide"
)

# 2. Inicializar estado de autenticación
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# 3. Lógica de Login
if not st.session_state.autenticado:
    st.title("🔑 Acceso al Sistema")
    
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Inicia Sesión")

        usuario = st.text_input("Nombre de Usuario")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if verificar_credenciales(usuario, password):
                st.session_state.autenticado = True
                st.session_state.usuario_actual = usuario
                st.success("¡Éxito! Cargando sistema...")
                st.rerun() 
            else:
                st.error("❌ Usuario o contraseña incorrectos. Revisa el SQL y las credenciales.")
    
    st.stop() 

# --- Funcionamiento post acceso ---

with st.sidebar:
    st.write(f"👤 **{st.session_state.usuario_actual}**")
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

st.title("☕ Sistema de Gestión - Cafetería")

# --- CUERPO PRINCIPAL ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Resumen de Ventas Recientes")
    data = obtener_resumen_mensual()
    
    if data:
        df = pd.DataFrame(data)
        df_display = df[['fecha', 'total_venta_dia', 'ingreso_nequi', 'ingreso_efectivo']].copy()
        df_display.columns = ['Fecha', 'Venta Total', 'Nequi', 'Efectivo']
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("Aún no hay registros de cierre de caja.")

with col2:
    st.subheader("Estado Rápido")
    if data:
        total_mes = sum(item['total_venta_dia'] for item in data)
        st.metric(label="Ventas últimos 30 días", value=f"${total_mes:,.0f}")
        
        ultima_venta = data[0]['total_venta_dia']
        st.metric(label="Último Cierre", value=f"${ultima_venta:,.0f}")
    else:
        st.write("No hay datos suficientes para mostrar métricas.")

st.divider()
st.info("Utiliza el menú lateral para registrar un nuevo cierre de caja o ver el análisis detallado.")