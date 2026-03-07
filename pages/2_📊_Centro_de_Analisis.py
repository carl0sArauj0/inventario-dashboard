import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
from logic import formatear_moneda

st.set_page_config(page_title="Análisis de Negocio", page_icon="📊", layout="wide")

# --- CARGA DE DATOS CENTRALIZADA ---
@st.cache_data(ttl=60)
def cargar_datos_completos():
    # Traer cierres, pagos y deudas
    res_c = supabase.table("cierres").select("*").order("fecha", desc=True).execute()
    res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
    res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
    
    df_c = pd.DataFrame(res_c.data)
    df_p = pd.DataFrame(res_p.data)
    df_d = pd.DataFrame(res_d.data)
    
    # Formatear fechas
    if not df_c.empty:
        df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
    if not df_p.empty:
        df_p['fecha'] = df_p['cierres'].apply(lambda x: pd.to_datetime(x['fecha']).date() if x else None)
    if not df_d.empty:
        df_d['fecha'] = df_d['cierres'].apply(lambda x: pd.to_datetime(x['fecha']).date() if x else None)
        
    return df_c, df_p, df_d

df_c, df_p, df_d = cargar_datos_completos()

if df_c.empty:
    st.warning("No hay datos registrados aún. Realiza un cierre de caja primero.")
    st.stop()

st.title("📊 Centro de Análisis y Consultas")

# --- PESTAÑAS ---
tab_mensual, tab_diario, tab_busqueda = st.tabs([
    "📈 Análisis Mensual", 
    "📅 Consulta por Día", 
    "🔍 Buscador Global"
])

# ==========================================
# PESTAÑA 1: ANÁLISIS MENSUAL
# ==========================================
with tab_mensual:
    st.header("Resumen del Mes")
    
    # Filtro de Mes
    df_c['mes_año'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')
    mes_sel = st.selectbox("Selecciona el mes:", df_c['mes_año'].unique())
    
    df_m = df_c[df_c['mes_año'] == mes_sel]
    ids_mes = df_m['id'].tolist()
    df_p_m = df_p[df_p['cierre_id'].isin(ids_mes)]
    df_d_m = df_d[df_d['cierre_id'].isin(ids_mes)]
    
    # Métricas de Alto Nivel
    m1, m2, m3, m4 = st.columns(4)
    v_total = df_m['total_venta_dia'].sum()
    g_total = df_p_m['valor'].sum()
    fiados_total = df_d_m['monto'].sum()
    
    m1.metric("Venta Bruta Total", formatear_moneda(v_total))
    m2.metric("Gastos Totales", formatear_moneda(g_total), delta_color="inverse")
    m3.metric("Utilidad Estimada", formatear_moneda(v_total - g_total))
    m4.metric("Total en Fiados", formatear_moneda(fiados_total))

    st.divider()
    
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.subheader("Tendencia de Ventas")
        fig_v = px.line(df_m, x='fecha', y='total_venta_dia', markers=True, title="Venta Diaria")
        st.plotly_chart(fig_v, use_container_width=True)
        
    with col_graf2:
        st.subheader("Composición de Ventas")
        comp = pd.DataFrame({
            "Tipo": ["Efectivo", "Nequi", "Fiados"],
            "Monto": [df_m['ingreso_efectivo'].sum(), df_m['ingresos_nequi'].sum(), fiados_total]
        })
        fig_p = px.pie(comp, values='Monto', names='Tipo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_p, use_container_width=True)

# ==========================================
# PESTAÑA 2: CONSULTA POR DÍA
# ==========================================
with tab_diario:
    st.header("Detalle Específico de un Día")
    dia_buscado = st.date_input("Selecciona una fecha:", df_c['fecha'].max())
    
    dia_data = df_c[df_c['fecha'] == dia_buscado]
    
    if dia_data.empty:
        st.error("No hay registros para este día.")
    else:
        info = dia_data.iloc[0]
        st.success(f"Cierre realizado por: **{info['responsable']}**")
        
        # Fila 1: Ingresos
        st.markdown("### 💰 Ingresos y Ventas")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Efectivo Hoy", formatear_moneda(info['ingreso_efectivo']))
        k2.metric("Nequi Hoy", formatear_moneda(info['ingresos_nequi']))
        k3.metric("Fiados Hoy", formatear_moneda(df_d[df_d['cierre_id']==info['id']]['monto'].sum()))
        k4.metric("VENTA TOTAL", formatear_moneda(info['total_venta_dia']))

        # Fila 2: Saldos
        k5, k6, k7 = st.columns(3)
        k5.metric("Saldo Nequi (App)", formatear_moneda(info['nequi_total_dia']))
        k6.metric("Efectivo en Casa", formatear_moneda(info['efectivo_en_casa']))
        k7.metric("Base Caja", formatear_moneda(info['base_caja']))

        st.divider()
        
        # Tablas de detalle
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("💸 Gastos del Día")
            pagos_dia = df_p[df_p['cierre_id'] == info['id']]
            if not pagos_dia.empty:
                st.dataframe(pagos_dia[['concepto', 'valor', 'metodo_pago']], hide_index=True, use_container_width=True)
            else:
                st.info("No hubo gastos.")
                
        with col_t2:
            st.subheader("📝 Fiados (Deudas)")
            deudas_dia = df_d[df_d['cierre_id'] == info['id']]
            if not deudas_dia.empty:
                st.dataframe(deudas_dia[['cliente', 'monto']], hide_index=True, use_container_width=True)
            else:
                st.info("No hubo ventas a crédito.")

# ==========================================
# PESTAÑA 3: BUSCADOR GLOBAL
# ==========================================
with tab_busqueda:
    st.header("Buscador de Proveedores y Clientes")
    
    opcion = st.radio("Buscar en:", ["Gastos (Proveedores)", "Fiados (Clientes)"])
    
    if opcion == "Gastos (Proveedores)":
        termino = st.text_input("Nombre del proveedor o concepto:")
        if termino:
            resultado = df_p[df_p['concepto'].str.contains(termino, case=False, na=False)]
            st.write(f"Se encontraron {len(resultado)} registros:")
            st.dataframe(resultado[['fecha', 'concepto', 'valor', 'metodo_pago']], hide_index=True, use_container_width=True)
            st.metric("Total pagado a este concepto", formatear_moneda(resultado['valor'].sum()))
    
    else:
        termino = st.text_input("Nombre del cliente:")
        if termino:
            resultado = df_d[df_d['cliente'].str.contains(termino, case=False, na=False)]
            st.write(f"Se encontraron {len(resultado)} deudas registradas:")
            st.dataframe(resultado[['fecha', 'cliente', 'monto']], hide_index=True, use_container_width=True)
            st.metric("Total que debe este cliente", formatear_moneda(resultado['monto'].sum()))

    st.divider()
    with st.expander("Ver tabla de cierres completa (Descargar CSV)"):
        st.dataframe(df_c, hide_index=True)
        csv = df_c.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Datos de Cierre", csv, "cierres.csv", "text/csv")