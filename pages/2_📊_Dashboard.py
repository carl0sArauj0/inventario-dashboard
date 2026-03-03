import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
from logic import formatear_moneda

st.set_page_config(page_title="Dashboard de Ventas", page_icon="📊", layout="wide")

st.title("📊 Análisis de Ventas y Gastos")

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60) # Cache para no saturar la base de datos, refresca cada minuto
def cargar_datos_completos():
    # Traer cierres
    res_cierres = supabase.table("cierres").select("*").order("fecha", desc=False).execute()
    # Traer pagos
    res_pagos = supabase.table("pagos").select("*").execute()
    
    df_cierres = pd.DataFrame(res_cierres.data)
    df_pagos = pd.DataFrame(res_pagos.data)
    
    return df_cierres, df_pagos

df_c, df_p = cargar_datos_completos()

if df_c.empty:
    st.warning("Aún no hay datos suficientes para generar el análisis.")
    st.stop()

# --- FILTROS ---
st.sidebar.header("Filtros")
fecha_min = pd.to_datetime(df_c['fecha']).min()
fecha_max = pd.to_datetime(df_c['fecha']).max()

start_date, end_date = st.sidebar.date_input(
    "Selecciona el rango de fechas:",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)

# Filtrar DataFrames por fecha
df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
df_c_filtrado = df_c[(df_c['fecha'] >= start_date) & (df_c['fecha'] <= end_date)]

# --- CÁLCULOS CLAVE ---
total_ventas = df_c_filtrado['total_venta_dia'].sum()
total_nequi = df_c_filtrado['ingreso_nequi'].sum()
total_efectivo = df_c_filtrado['ingreso_efectivo'].sum()

# Calcular gastos del periodo (cruzando con los cierres filtrados)
ids_filtrados = df_c_filtrado['id'].tolist()
df_p_filtrado = df_p[df_p['cierre_id'].isin(ids_filtrados)]
total_gastos = df_p_filtrado['valor'].sum()

# --- MÉTRICAS PRINCIPALES ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Venta Total Bruta", formatear_moneda(total_ventas))
c2.metric("Total Gastos", formatear_moneda(total_gastos), delta_color="inverse")
c3.metric("Utilidad Operativa", formatear_moneda(total_ventas - total_gastos))
c4.metric("Promedio Diario", formatear_moneda(df_c_filtrado['total_venta_dia'].mean()))

st.divider()

# --- GRÁFICOS ---
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("Tendencia de Venta Diaria")
    fig_linea = px.line(
        df_c_filtrado, 
        x="fecha", 
        y="total_venta_dia", 
        markers=True,
        labels={"total_venta_dia": "Venta ($)", "fecha": "Día"},
        title="Ventas por Día"
    )
    st.plotly_chart(fig_linea, use_container_width=True)

with col_der:
    st.subheader("Método de Pago Preferido")
    data_pie = pd.DataFrame({
        "Método": ["Efectivo", "Nequi"],
        "Valor": [total_efectivo, total_nequi]
    })
    fig_pie = px.pie(
        data_pie, 
        values="Valor", 
        names="Método", 
        hole=0.4,
        color_discrete_sequence=["#2ecc71", "#3498db"]
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# --- ANÁLISIS DE GASTOS ---
st.subheader("Detalle de Gastos/Pagos en el Periodo")
if not df_p_filtrado.empty:
    # Agrupar gastos por concepto para ver en qué se va más dinero
    gastos_agrupados = df_p_filtrado.groupby("concepto")["valor"].sum().reset_index().sort_values(by="valor", ascending=False)
    
    fig_bar = px.bar(
        gastos_agrupados, 
        x="valor", 
        y="concepto", 
        orientation='h',
        title="Gastos por Concepto",
        labels={"valor": "Total Gastado ($)", "concepto": "Ítem"}
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No se registraron gastos en este periodo.")

# --- TABLA DE DATOS CRUDOS ---
with st.expander("Ver tabla detallada de cierres"):
    st.dataframe(df_c_filtrado, use_container_width=True)