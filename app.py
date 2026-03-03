import streamlit as st
import pandas as pd
from database import obtener_resumen_mensual

# Configuración de la página
st.set_page_config(
    page_title="Cafetería - Control de Inventario",
    page_icon="☕",
    layout="wide"
)

st.title("☕ Sistema de Gestión - Cafetería")

# --- BARRA LATERAL ---
st.sidebar.success("Selecciona una opción arriba para empezar.")

# --- CUERPO PRINCIPAL ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Resumen de Ventas Recientes")
    data = obtener_resumen_mensual()
    
    if data:
        df = pd.DataFrame(data)
        # Formatear columnas para visualización
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