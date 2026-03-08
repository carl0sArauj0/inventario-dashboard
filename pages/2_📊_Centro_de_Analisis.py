import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
from logic import formatear_moneda

st.set_page_config(page_title="Análisis de Negocio", page_icon="📊", layout="wide")

# --- CARGA DE DATOS CENTRALIZADA ---
@st.cache_data(ttl=60)
def cargar_datos_completos():
    try:
        # Traer cierres, pagos y deudas
        res_c = supabase.table("cierres").select("*").order("fecha", desc=True).execute()
        res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
        res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
        
        df_c = pd.DataFrame(res_c.data)
        df_p = pd.DataFrame(res_p.data)
        df_d = pd.DataFrame(res_d.data)
        
        # Formatear fechas si hay datos
        if not df_c.empty:
            df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
        if not df_p.empty:
            df_p['fecha'] = df_p['cierres'].apply(lambda x: pd.to_datetime(x['fecha']).date() if x else None)
        if not df_d.empty:
            df_d['fecha'] = df_d['cierres'].apply(lambda x: pd.to_datetime(x['fecha']).date() if x else None)
            
        return df_c, df_p, df_d
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_c, df_p, df_d = cargar_datos_completos()

if df_c.empty:
    st.warning("☕ Aún no hay datos registrados. Realiza tu primer cierre de caja para ver el análisis.")
    st.stop()

st.title("📊 Centro de Análisis y Consultas")

# --- PESTAÑAS DE NAVEGACIÓN ---
tab_mensual, tab_diario, tab_busqueda = st.tabs([
    "📈 Análisis Mensual", 
    "📅 Consulta por Día", 
    "🔍 Buscador de Gastos y Fiados"
])

# ==========================================
# PESTAÑA 1: ANÁLISIS MENSUAL
# ==========================================
with tab_mensual:
    st.header("Resumen del Mes")
    
    # Filtro de Mes/Año
    df_c['mes_año'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')
    meses_disp = df_c['mes_año'].unique()
    mes_sel = st.selectbox("Selecciona el mes a analizar:", meses_disp)
    
    df_m = df_c[df_c['mes_año'] == mes_sel]
    ids_mes = df_m['id'].tolist()
    
    # Filtrar pagos y deudas del mes seleccionado
    df_p_m = df_p[df_p['cierre_id'].isin(ids_mes)]
    df_d_m = df_d[df_d['cierre_id'].isin(ids_mes)]
    
    # Métricas Principales
    m1, m2, m3, m4 = st.columns(4)
    v_total = df_m['total_venta_dia'].sum()
    g_total = df_p_m['valor'].sum() if not df_p_m.empty else 0
    f_total = df_d_m['monto'].sum() if not df_d_m.empty else 0
    
    m1.metric("Ventas Totales (Bruto)", formatear_moneda(v_total))
    m2.metric("Gastos Totales", formatear_moneda(g_total), delta_color="inverse")
    m3.metric("Utilidad Operativa", formatear_moneda(v_total - g_total))
    m4.metric("Total en Fiados", formatear_moneda(f_total))

    st.divider()
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Tendencia de Venta Diaria")
        fig_linea = px.line(df_m.sort_values('fecha'), x='fecha', y='total_venta_dia', 
                           markers=True, title="Ventas por Día", labels={'total_venta_dia': 'Venta ($)'})
        st.plotly_chart(fig_linea, use_container_width=True)
        
    with col_g2:
        st.subheader("Composición de los Ingresos")
        # Sumamos las 3 fuentes de ingreso real
        efectivo_real = df_m['ingreso_efectivo'].sum()
        nequi_real = df_m['ingresos_nequi'].sum()
        
        comp_data = pd.DataFrame({
            "Origen": ["Efectivo", "Nequi", "Fiados"],
            "Monto": [efectivo_real, nequi_real, f_total]
        })
        fig_pie = px.pie(comp_data, values='Monto', names='Origen', hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# PESTAÑA 2: CONSULTA POR DÍA (Auditoría)
# ==========================================
with tab_diario:
    st.header("Detalle Específico de un Día")
    fecha_busqueda = st.date_input("Selecciona una fecha para auditar:", df_c['fecha'].max())
    
    dia_data = df_c[df_c['fecha'] == fecha_busqueda]
    
    if dia_data.empty:
        st.error("No se encontró ningún cierre de caja para esta fecha.")
    else:
        info = dia_data.iloc[0]
        st.success(f"Cierre registrado por: **{info.get('responsable', 'Desconocido')}**")
        
        # Fila 1: Resumen de Ventas
        st.markdown("### 💰 Ventas Reales del Día")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Venta Efectivo", formatear_moneda(info.get('ingreso_efectivo', 0)))
        k2.metric("Venta Nequi", formatear_moneda(info.get('ingresos_nequi', 0)))
        k3.metric("Venta Fiados", formatear_moneda(df_d[df_d['cierre_id']==info['id']]['monto'].sum()))
        k4.metric("🚀 VENTA TOTAL", formatear_moneda(info.get('total_venta_dia', 0)))

        # Fila 2: Saldos y Caja
        st.markdown("### 🔍 Auditoría de Caja y Saldos")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Efectivo en Caja (Físico)", formatear_moneda(info.get('efectivo_en_caja', 0)))
        s2.metric("Base Caja (Restada)", f"- {formatear_moneda(info.get('base_caja', 0))}")
        s3.metric("Saldo Nequi (App)", formatear_moneda(info.get('nequi_total_dia', 0)))
        s4.metric("Efectivo en Casa", formatear_moneda(info.get('efectivo_en_casa', 0)))

        st.divider()
        
        # Tablas de detalle: Gastos y Fiados
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("💸 Gastos Registrados")
            pagos_dia = df_p[df_p['cierre_id'] == info['id']]
            if not pagos_dia.empty:
                st.dataframe(pagos_dia[['concepto', 'valor', 'metodo_pago']], hide_index=True, use_container_width=True)
            else:
                st.info("No se registraron gastos este día.")
                
        with col_t2:
            st.subheader("📝 Fiados (Deudas)")
            deudas_dia = df_d[df_d['cierre_id'] == info['id']]
            if not deudas_dia.empty:
                st.dataframe(deudas_dia[['cliente', 'monto']], hide_index=True, use_container_width=True)
            else:
                st.info("No hubo ventas fiadas este día.")

# ==========================================
# PESTAÑA 3: BUSCADOR GLOBAL
# ==========================================
with tab_busqueda:
    st.header("Buscador Global")
    
    opcion_busqueda = st.radio("¿Qué deseas rastrear?", ["Gastos a Proveedores", "Deudas de Clientes"])
    
    if opcion_busqueda == "Gastos a Proveedores":
        term = st.text_input("Ingresa el nombre del proveedor o concepto (ej: Gaseosas, Makro, Arriendo):")
        if term:
            res_busq = df_p[df_p['concepto'].str.contains(term, case=False, na=False)]
            st.write(f"Se encontraron **{len(res_busq)}** registros.")
            st.dataframe(res_busq[['fecha', 'concepto', 'valor', 'metodo_pago']], hide_index=True, use_container_width=True)
            st.metric(f"Total pagado a '{term}'", formatear_moneda(res_busq['valor'].sum()))
    
    else:
        term = st.text_input("Ingresa el nombre del cliente para ver cuánto debe:")
        if term:
            res_busq = df_d[df_d['cliente'].str.contains(term, case=False, na=False)]
            st.write(f"Se encontraron **{len(res_busq)}** deudas pendientes.")
            st.dataframe(res_busq[['fecha', 'cliente', 'monto']], hide_index=True, use_container_width=True)
            st.metric(f"Total que debe '{term}'", formatear_moneda(res_busq['monto'].sum()))

    st.divider()
    with st.expander("📥 Exportar Datos Crutos"):
        st.write("Aquí puedes descargar toda la tabla de cierres para abrirla en Excel.")
        csv_data = df_c.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Excel (CSV)", csv_data, "cierres_cafeteria.csv", "text/csv")