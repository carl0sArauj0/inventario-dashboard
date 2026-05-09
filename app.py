import streamlit as st
import pandas as pd
from database import obtener_resumen_mensual


def verificar_credenciales(usuario, contraseña):
    # Ejemplo simple de verificación de credenciales.
    # Cambia esta lógica por la validación real contra tu base de datos.
    return usuario == "admin" and contraseña == "password"

# Configuración de la página
st.set_page_config(
    page_title="Cafetería - Control de Inventario",
    page_icon="☕",
    layout="wide"
)

# Configuración de la página
st.set_page_config(
    page_title="Cafetería - Control de inventario",
    page_icon="=",
    layout="wide"
)

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("🔑 Acceso al Sistema - Cafetería")

    col_login, _=st.columns([1,1.5])
    with col_login:
        with st.form('login_form'):
            usuario = st.text_input("Usuario")
            contraseña = st.text_input("Contraseña", type='password')
            boton_login = st.form_submit_button("Ingresar", use_container_width=True)

            if boton_login:
                if verificar_credenciales(usuario, contraseña):
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usuario
                    st.succes("¡Acceso concedido!")
                    time_sleep = 1
                    st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    st.success(f"Sesión activa: {st.session_state.usuario_actual}")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_actual = None
        st.rerun()

st.title("= Sistema de GEstión - Cafetería")



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