import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
from logic import formatear_moneda

st.set_page_config(page_title="Análisis de Negocio", page_icon="📊", layout="wide")

# --- CARGA DE DATOS CENTRALIZADA ---
@st.cache_data(ttl=60)
def cargar_todo():
    # Traer cierres y pagos
    res_c = supabase.table("cierres").select("*").order("fecha", desc=True).execute()
    res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
    
    df_c = pd.DataFrame(res_c.data)
    df_p = pd.DataFrame(res_p.data)
    
    if not df_c.empty:
        df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
    if not df_p.empty:
        df_p['fecha'] = df_p['cierres'].apply(lambda x: pd.to_datetime(x['fecha']).date() if x else None)
        
    return df_c, df_p

df_c, df_p = cargar_todo()

if df_c.empty:
    st.warning("No hay datos registrados aún. Por favor realiza un cierre de caja primero.")
    st.stop()

st.title("📊 Centro de Análisis y Consultas")

# --- CREACIÓN DE PESTAÑAS ---
tab_mensual, tab_diario, tab_consultas = st.tabs([
    "📈 Análisis Mensual", 
    "📅 Detalle por Día", 
    "🔍 Consultas y Reportes"
])

# ==========================================
# PESTAÑA 1: ANÁLISIS MENSUAL (Dashboard)
# ==========================================
with tab_mensual:
    st.header("Vista General del Mes")
    
    # Filtro de Mes/Año
    df_c['mes_año'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')
    meses_disponibles = df_c['mes_año'].unique()
    mes_sel = st.selectbox("Selecciona el mes a analizar:", meses_disponibles)
    
    df_m = df_c[df_c['mes_año'] == mes_sel]
    ids_mes = df_m['id'].tolist()
    df_p_m = df_p[df_p['cierre_id'].isin(ids_mes)]
    
    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    ventas_m = df_m['total_venta_dia'].sum()
    gastos_m = df_p_m['valor'].sum()
    
    m1.metric("Ventas Totales", formatear_moneda(ventas_m))
    m2.metric("Gastos Totales", formatear_moneda(gastos_m), delta_color="inverse")
    m3.metric("Utilidad Neta", formatear_moneda(ventas_m - gastos_m))
    m4.metric("Días Operados", len(df_m))
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig_ventas = px.bar(df_m, x='fecha', y='total_venta_dia', title="Ventas Diarias en el Mes", color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig_ventas, use_container_width=True)
    
    with col_b:
        metodos = pd.DataFrame({
            "Metodo": ["Efectivo", "Nequi"],
            "Monto": [df_m['ingreso_efectivo'].sum(), df_m['ingreso_nequi'].sum()]
        })
        fig_pie = px.pie(metodos, values='Monto', names='Metodo', title="Mix de Ventas", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# PESTAÑA 2: ANÁLISIS DIARIO (Consulta Específica)
# ==========================================
with tab_diario:
    st.header("Consulta de Día Específico")
    dia_sel = st.date_input("Selecciona un día para ver el detalle:", df_c['fecha'].max())
    
    datos_dia = df_c[df_c['fecha'] == dia_sel]
    
    if datos_dia.empty:
        st.error("No se encontró ningún registro para esta fecha.")
    else:
        dia = datos_dia.iloc[0]
        
        # Mostrar los nuevos campos en el detalle diario
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ingreso Efectivo", formatear_moneda(dia.get('ingreso_efectivo')))
        k2.metric("Nequi Total Día", formatear_moneda(dia.get('nequi_total_dia')))
        k3.metric("Efectivo en Casa", formatear_moneda(dia.get('efectivo_en_casa')))
        k4.metric("Venta Total", formatear_moneda(dia.get('total_venta_dia')))

        c1, c2, c3 = st.columns(3)
        c1.info(f"**Responsable:** {dia['responsable']}")
        c2.success(f"**Venta Total:** {formatear_moneda(dia['total_venta_dia'])}")
        c3.warning(f"**Base Inicial:** {formatear_moneda(dia['base_caja'])}")
        
        st.subheader("Desglose de Ingresos")
        k1, k2, k3 = st.columns(3)
        k1.metric("Efectivo (Contado - Base)", formatear_moneda(dia['ingreso_efectivo']))
        k2.metric("Nequi", formatear_moneda(dia['ingreso_nequi']))
        
        # Pagos del día
        st.subheader("Pagos Realizados este día")
        pagos_dia = df_p[df_p['cierre_id'] == dia['id']]
        if not pagos_dia.empty:
            st.table(pagos_dia[['concepto', 'valor', 'metodo_pago']].style.format({"valor": "${:,.0f}"}))
        else:
            st.info("No se registraron pagos este día.")
    st.subheader("📝 Detalle de Fiados (Ventas a Crédito)")
    res_d = supabase.table("deudas").select("*").eq("cierre_id", dia['id']).execute()
    if res_d.data:
        st.table(pd.DataFrame(res_d.data)[['cliente', 'monto']].style.format({"monto": "${:,.0f}"}))
    else:
        st.info("No hubo fiados este día.")

# ==========================================
# PESTAÑA 3: CONSULTAS Y REPORTES (Gastos y Filtros)
# ==========================================
with tab_consultas:
    st.header("Buscador Global de Gastos y Cierres")
    
    tipo_busqueda = st.radio("¿Qué deseas buscar?", ["Todos los Pagos/Gastos", "Historial de Cierres"])
    
    if tipo_busqueda == "Todos los Pagos/Gastos":
        metodo_filtro = st.multiselect(
            "Filtrar por origen del dinero:", 
            ["Efectivo hoy", "Efectivo ayer", "Nequi"], 
            default=["Efectivo hoy", "Efectivo ayer", "Nequi"]
        )
        if not df_p.empty:
            df_res = df_p[df_p['concepto'].str.contains(busqueda, case=False, na=False)]
            st.dataframe(df_res[['fecha', 'concepto', 'valor', 'metodo_pago']], use_container_width=True)
            
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Resultados CSV", csv, "reporte_gastos.csv", "text/csv")
            
    else:
        st.dataframe(df_c[['fecha', 'total_venta_dia', 'ingreso_efectivo', 'ingreso_nequi', 'responsable']], use_container_width=True)
        csv = df_c.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Historial Cierres CSV", csv, "historial_cierres.csv", "text/csv")