import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
from logic import formatear_moneda

st.set_page_config(page_title="Análisis", page_icon="📊", layout="wide")

@st.cache_data(ttl=60)
def cargar_datos():
    res_c = supabase.table("cierres").select("*").order("fecha", desc=True).execute()
    res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
    res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
    df_c = pd.DataFrame(res_c.data)
    if not df_c.empty: df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
    return df_c, pd.DataFrame(res_p.data), pd.DataFrame(res_d.data)

df_c, df_p, df_d = cargar_datos()

if df_c.empty:
    st.info("Sin datos registrados.")
    st.stop()

t1, t2, t3 = st.tabs(["📈 Mensual", "📅 Detalle Diario", "🔍 Buscador"])

with t1:
    df_c['mes'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')
    mes_sel = st.selectbox("Mes:", df_c['mes'].unique())
    df_m = df_c[df_c['mes'] == mes_sel]
    ids = df_m['id'].tolist()
    gastos_m = df_p[df_p['cierre_id'].isin(ids)]['valor'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Venta Bruta Total", formatear_moneda(df_m['total_venta_dia'].sum()))
    c2.metric("Gastos Totales", formatear_moneda(gastos_m), delta_color="inverse")
    c3.metric("Utilidad Estimada", formatear_moneda(df_m['total_venta_dia'].sum() - gastos_m))
    
    st.plotly_chart(px.bar(df_m.sort_values('fecha'), x='fecha', y='total_venta_dia', title="Ventas por Día"), use_container_width=True)

with t2:
    f_bus = st.date_input("Día:", df_c['fecha'].max())
    dia = df_c[df_c['fecha'] == f_bus]
    if not dia.empty:
        info = dia.iloc[0]
        st.subheader(f"Auditoría del {f_bus}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🚀 VENTA TOTAL", formatear_moneda(info['total_venta_dia']))
        c2.metric("Venta Efectivo", formatear_moneda(info['ingreso_efectivo']))
        c3.metric("Venta Nequi", formatear_moneda(info['ingresos_nequi']))
        
        st.divider()
        st.write("**Desglose de Caja:**")
        a1, a2, a3 = st.columns(3)
        a1.write(f"Efectivo en Caja: {formatear_moneda(info['efectivo_en_caja'])}")
        a2.write(f"Base Caja: - {formatear_moneda(info['base_caja'])}")
        a3.write(f"Efectivo en Casa: {formatear_moneda(info['efectivo_en_casa'])}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Gastos:**")
            st.dataframe(df_p[df_p['cierre_id']==info['id']][['concepto','valor','metodo_pago']], hide_index=True)
        with col2:
            st.write("**Fiados:**")
            st.dataframe(df_d[df_d['cierre_id']==info['id']][['cliente','monto','telefono']], hide_index=True)

with t3:
    term = st.text_input("Buscar Concepto o Cliente:")
    if term:
        r1 = df_p[df_p['concepto'].str.contains(term, case=False, na=False)]
        r2 = df_d[df_d['cliente'].str.contains(term, case=False, na=False)]
        if not r1.empty: st.write("Gastos:", r1)
        if not r2.empty: st.write("Fiados:", r2)