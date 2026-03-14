import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
from logic import formatear_moneda

st.set_page_config(page_title="Análisis de Negocio", page_icon="📊", layout="wide")

@st.cache_data(ttl=60)
def cargar_datos():
    try:
        res_c = supabase.table("cierres").select("*").order("fecha", desc=True).execute()
        res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
        res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
        
        df_c = pd.DataFrame(res_c.data)
        if not df_c.empty: 
            df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
            
        return df_c, pd.DataFrame(res_p.data), pd.DataFrame(res_d.data)
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_c, df_p, df_d = cargar_datos()

if df_c.empty:
    st.info("☕ Aún no hay datos registrados. Realiza un cierre de caja para ver el análisis.")
    st.stop()

# --- PESTAÑAS ---
t1, t2, t3 = st.tabs(["📈 Análisis Mensual", "📅 Detalle Diario", "🔍 Buscador Global"])

# PESTAÑA 1: MENSUAL
with t1:
    st.header("Resumen del Mes")
    df_c['mes'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')
    meses_disponibles = df_c['mes'].unique()
    mes_sel = st.selectbox("Selecciona el mes:", meses_disponibles)
    
    df_m = df_c[df_c['mes'] == mes_sel]
    ids_mes = df_m['id'].tolist()
    
    gastos_m = df_p[df_p['cierre_id'].isin(ids_mes)]['valor'].sum() if not df_p.empty else 0
    ventas_m = df_m['total_venta_dia'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Venta Bruta Total", formatear_moneda(ventas_m))
    c2.metric("Gastos Totales", formatear_moneda(gastos_m), delta_color="inverse")
    c3.metric("Utilidad Estimada", formatear_moneda(ventas_m - gastos_m))
    
    st.divider()
    st.plotly_chart(px.bar(df_m.sort_values('fecha'), x='fecha', y='total_venta_dia', 
                           title="Evolución de Ventas Diarias", color_discrete_sequence=['#00CC96']), 
                    use_container_width=True)

# PESTAÑA 2: DETALLE DIARIO (Auditoría)
with t2:
    st.header("Detalle Específico del Día")
    f_bus = st.date_input("Selecciona una fecha:", df_c['fecha'].max())
    dia = df_c[df_c['fecha'] == f_bus]
    
    if not dia.empty:
        info = dia.iloc[0]
        st.success(f"Cierre registrado por: **{info.get('responsable', 'N/A')}**")
        
        # FILA 1: VENTAS REALES
        st.markdown("### 💰 Ventas del Día")
        k1, k2, k3 = st.columns(3)
        k1.metric("Venta Efectivo", formatear_moneda(info.get('ingreso_efectivo', 0)))
        k2.metric("Venta Nequi", formatear_moneda(info.get('ingresos_nequi', 0)))
        k3.metric("🚀 VENTA TOTAL", formatear_moneda(info.get('total_venta_dia', 0)))
        
        st.divider()
        
        # FILA 2: AUDITORÍA DE CAJA Y SALDOS (Aquí se agregó Saldo Nequi App)
        st.markdown("### 🔍 Auditoría de Caja y Saldos")
        a1, a2, a3, a4 = st.columns(4)
        
        # Usamos st.metric para que se vea uniforme con el resto de la app
        a1.metric("Efectivo en Caja", formatear_moneda(info.get('efectivo_en_caja', 0)))
        a2.metric("Efectivo en Casa", formatear_moneda(info.get('efectivo_en_casa', 0)))
        a3.metric("Saldo Nequi App", formatear_moneda(info.get('nequi_total_dia', 0)))
        a4.metric("Base Caja (Fondo)", formatear_moneda(info.get('base_caja', 0)))
        
        st.divider()
        
        # TABLAS DE DETALLE
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💸 Gastos / Pagos")
            df_p_dia = df_p[df_p['cierre_id'] == info['id']]
            if not df_p_dia.empty:
                st.dataframe(df_p_dia[['concepto', 'valor', 'metodo_pago']], 
                             column_config={"valor": st.column_config.NumberColumn("Monto", format="$ %d")},
                             hide_index=True, use_container_width=True)
            else:
                st.info("No se registraron gastos este día.")
                
        with col2:
            st.subheader("📝 Fiados (Créditos)")
            df_d_dia = df_d[df_d['cierre_id'] == info['id']]
            if not df_d_dia.empty:
                st.dataframe(df_d_dia[['cliente', 'monto', 'telefono']], 
                             column_config={"monto": st.column_config.NumberColumn("Monto", format="$ %d")},
                             hide_index=True, use_container_width=True)
            else:
                st.info("No hubo ventas fiadas este día.")
    else:
        st.error("No se encontró ningún registro para esta fecha.")

# PESTAÑA 3: BUSCADOR
with t3:
    st.header("Buscador de Gastos y Deudores")
    term = st.text_input("Ingresa el concepto del gasto o nombre del cliente:")
    
    if term:
        # Búsqueda en Gastos
        r_pagos = df_p[df_p['concepto'].str.contains(term, case=False, na=False)]
        if not r_pagos.empty:
            st.subheader(f"Gastos encontrados para '{term}'")
            st.dataframe(r_pagos[['fecha', 'concepto', 'valor', 'metodo_pago']], 
                         column_config={"valor": st.column_config.NumberColumn("Monto", format="$ %d")},
                         hide_index=True, use_container_width=True)
            st.metric("Total Gastado", formatear_moneda(r_pagos['valor'].sum()))
        
        # Búsqueda en Fiados
        r_deudas = df_d[df_d['cliente'].str.contains(term, case=False, na=False)]
        if not r_deudas.empty:
            st.subheader(f"Deudas encontradas para '{term}'")
            st.dataframe(r_deudas[['fecha', 'cliente', 'monto', 'telefono']], 
                         column_config={"monto": st.column_config.NumberColumn("Monto", format="$ %d")},
                         hide_index=True, use_container_width=True)
            st.metric("Total Adeudado", formatear_moneda(r_deudas['monto'].sum()))
        
        if r_pagos.empty and r_deudas.empty:
            st.info("No se encontraron coincidencias.")