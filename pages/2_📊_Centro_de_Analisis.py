import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import supabase
from logic import formatear_moneda
from datetime import datetime, timedelta

# Configuración de estilo "Modern Business Intelligence"
st.set_page_config(page_title="Business Intelligence - Cafetería", page_icon="📈", layout="wide")

# CSS para mejorar la estética de las tarjetas
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00CC96; }
    .main { background-color: #f8f9fa; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def cargar_datos_maestros():
    res_c = supabase.table("cierres").select("*").order("fecha", desc=False).execute()
    res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
    res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
    
    df_c = pd.DataFrame(res_c.data)
    if not df_c.empty:
        df_c['fecha'] = pd.to_datetime(df_c['fecha'])
        df_c['dia_semana'] = df_c['fecha'].dt.day_name()
        df_c['semana'] = df_c['fecha'].dt.isocalendar().week
        
    return df_c, pd.DataFrame(res_p.data), pd.DataFrame(res_d.data)

df_c, df_p, df_d = cargar_datos_maestros()

if df_c.empty:
    st.info("Esperando primer registro para activar motores estadísticos...")
    st.stop()

# --- SIDEBAR: FILTROS GLOBALES ---
st.sidebar.title("🛠️ Filtros de Inteligencia")
rango_fechas = st.sidebar.date_input("Periodo de Análisis", [df_c['fecha'].min(), df_c['fecha'].max()])

if len(rango_fechas) == 2:
    mask = (df_c['fecha'].dt.date >= rango_fechas[0]) & (df_c['fecha'].dt.date <= rango_fechas[1])
    df_c_filtered = df_c[mask]
else:
    df_c_filtered = df_c

# --- CABECERA ---
st.title("📈 Business Intelligence Dashboard")
st.caption(f"Análisis estadístico desde {rango_fechas[0]} hasta {rango_fechas[1]}")

# --- TABS ---
tab_kpi, tab_perfil, tab_gastos, tab_auditoria = st.tabs([
    "🚀 KPIs Principales", 
    "🕒 Perfil Temporal", 
    "💸 Análisis de Fuga (Gastos)", 
    "🔍 Auditoría Diaria"
])

# ==========================================
# TAB 1: KPIs PRINCIPALES (Vista de Dueño)
# ==========================================
with tab_kpi:
    # Cálculo de métricas
    total_ventas = df_c_filtered['total_venta_dia'].sum()
    promedio_diario = df_c_filtered['total_venta_dia'].mean()
    ids_periodo = df_c_filtered['id'].tolist()
    total_gastos = df_p[df_p['cierre_id'].isin(ids_periodo)]['valor'].sum() if not df_p.empty else 0
    total_fiados = df_d[df_d['cierre_id'].isin(ids_periodo)]['monto'].sum() if not df_d.empty else 0
    utilidad_neta = total_ventas - total_gastos

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ventas Totales", formatear_moneda(total_ventas))
    col2.metric("Utilidad Estimada", formatear_moneda(utilidad_neta), delta=f"{(utilidad_neta/total_ventas*100):.1f}% Margen" if total_ventas > 0 else "0%")
    col3.metric("Ticket Promedio Diario", formatear_moneda(promedio_diario))
    col4.metric("Riesgo Fiados", formatear_moneda(total_fiados), delta=f"{len(df_d)} facturas", delta_color="inverse")

    st.divider()
    
    # Gráfica de Serie de Tiempo con Línea de Tendencia
    st.subheader("Tendencia de Crecimiento")
    fig_line = px.area(df_c_filtered, x='fecha', y='total_venta_dia', 
                       title="Venta Diaria Acumulada",
                       color_discrete_sequence=['#00CC96'],
                       template="plotly_white")
    # Añadir media móvil para ver la tendencia real sin ruidos
    df_c_filtered['media_movil'] = df_c_filtered['total_venta_dia'].rolling(window=3).mean()
    fig_line.add_scatter(x=df_c_filtered['fecha'], y=df_c_filtered['media_movil'], name="Tendencia (3D)")
    st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# TAB 2: PERFIL TEMPORAL (¿Cuándo vendemos más?)
# ==========================================
with tab_perfil:
    st.subheader("Análisis de Estacionalidad Diaria")
    
    # Agrupar por día de la semana
    dias_orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df_dias = df_c_filtered.groupby('dia_semana')['total_venta_dia'].agg(['mean', 'sum']).reindex(dias_orden)
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Gráfico de Radar para ver la "fuerza" de cada día
        fig_radar = go.Figure(data=go.Scatterpolar(
          r=df_dias['mean'],
          theta=['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'],
          fill='toself',
          line_color='#636EFA'
        ))
        fig_radar.update_layout(title="Fortaleza por Día (Promedio)")
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_b:
        # Comparativa Efectivo vs Nequi
        mix_data = df_c_filtered.groupby('mes_año' if 'mes_año' in df_c_filtered else 'fecha')[['ingreso_efectivo', 'ingresos_nequi']].sum().reset_index()
        fig_bar = px.bar(mix_data, x=mix_data.columns[0], y=['ingreso_efectivo', 'ingresos_nequi'], 
                         title="Mix de Cobro: Efectivo vs Nequi",
                         barmode='group', template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# TAB 3: ANÁLISIS DE FUGA (Gastos)
# ==========================================
with tab_gastos:
    st.subheader("Estructura de Costos")
    
    if not df_p.empty:
        df_p_periodo = df_p[df_p['cierre_id'].isin(ids_periodo)]
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            # Gráfico de Torta de Gastos por Método
            fig_p_pie = px.pie(df_p_periodo, values='valor', names='metodo_pago', 
                               title="Origen del Dinero para Pagos",
                               hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_p_pie, use_container_width=True)
            
        with c2:
            # Pareto de Gastos (Conceptos más pesados)
            gastos_top = df_p_periodo.groupby('concepto')['valor'].sum().sort_values(ascending=True).tail(10)
            fig_pareto = px.bar(gastos_top, orientation='h', 
                                title="Top 10 Conceptos de Gasto",
                                color_discrete_sequence=['#EF553B'])
            st.plotly_chart(fig_pareto, use_container_width=True)
            
    else:
        st.warning("No hay datos de gastos para el periodo seleccionado.")

# ==========================================
# TAB 4: AUDITORÍA Y FIADOS
# ==========================================
with tab_auditoria:
    st.subheader("Auditoría Detallada")
    
    # Filtro de búsqueda rápida
    search = st.text_input("🔍 Buscar Cliente o Proveedor:")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("### Deudas Activas")
        df_d_f = df_d[df_d['cierre_id'].isin(ids_periodo)]
        if search:
            df_d_f = df_d_f[df_d_f['cliente'].str.contains(search, case=False, na=False)]
        st.dataframe(df_d_f[['fecha', 'cliente', 'monto', 'telefono']], hide_index=True, use_container_width=True)
        
    with col_t2:
        st.markdown("### Resumen de Saldos")
        # Gráfico comparativo de Efectivo en Casa vs Saldo Nequi
        saldos_box = df_c_filtered[['efectivo_en_casa', 'nequi_total_dia']].melt()
        fig_box = px.box(saldos_box, x="variable", y="value", 
                         points="all", title="Distribución de Liquidez (Saldos)",
                         color="variable", template="plotly_white")
        st.plotly_chart(fig_box, use_container_width=True)

# --- CIERRE ESTADÍSTICO ---
st.divider()
st.markdown(f"**Nota del Estadístico:** Durante este periodo, su mejor día fue el **{df_c_filtered.loc[df_c_filtered['total_venta_dia'].idxmax(), 'fecha'].date()}** con una venta de {formatear_moneda(df_c_filtered['total_venta_dia'].max())}.")