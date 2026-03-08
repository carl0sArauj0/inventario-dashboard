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
    st.warning("Sin datos.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📈 Mensual", "📅 Diario", "🔍 Buscador"])

with tab1:
    df_c['mes'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')
    mes_sel = st.selectbox("Mes:", df_c['mes'].unique())
    df_m = df_c[df_c['mes'] == mes_sel]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Venta Bruta", formatear_moneda(df_m['total_venta_dia'].sum()))
    c2.metric("Gastos", formatear_moneda(df_p[df_p['cierre_id'].isin(df_m['id'])]['valor'].sum()))
    c3.metric("Días con Cierre", len(df_m))
    
    st.plotly_chart(px.line(df_m.sort_values('fecha'), x='fecha', y='total_venta_dia', title="Ventas Diarias"), use_container_width=True)

with tab2:
    fecha_bus = st.date_input("Día:", df_c['fecha'].max())
    dia = df_c[df_c['fecha'] == fecha_bus]
    if not dia.empty:
        info = dia.iloc[0]
        st.subheader(f"Resumen de {fecha_bus}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Ingreso Efectivo (Venta)", formatear_moneda(info.get('ingreso_efectivo', 0)))
        k2.metric("Ingreso Nequi (Venta)", formatear_moneda(info.get('ingresos_nequi', 0)))
        k3.metric("🚀 VENTA TOTAL", formatear_moneda(info.get('total_venta_dia', 0)))
        
        st.markdown("---")
        a1, a2, a3 = st.columns(3)
        a1.metric("Efectivo Físico Contado", formatear_moneda(info.get('efectivo_en_caja', 0)))
        a2.metric("Efectivo en Casa", formatear_moneda(info.get('efectivo_en_casa', 0)))
        a3.metric("Saldo Nequi (App)", formatear_moneda(info.get('nequi_total_dia', 0)))
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("**Gastos:**")
            st.dataframe(df_p[df_p['cierre_id']==info['id']][['concepto','valor','metodo_pago']], hide_index=True)
        with col_t2:
            st.write("**Fiados:**")
            st.dataframe(df_d[df_d['cierre_id']==info['id']][['cliente','monto']], hide_index=True)

with tab3:
    bus = st.text_input("Buscar Concepto o Cliente:")
    if bus:
        r1 = df_p[df_p['concepto'].str.contains(bus, case=False, na=False)]
        r2 = df_d[df_d['cliente'].str.contains(bus, case=False, na=False)]
        if not r1.empty: st.write("Gastos:", r1)
        if not r2.empty: st.write("Fiados:", r2)