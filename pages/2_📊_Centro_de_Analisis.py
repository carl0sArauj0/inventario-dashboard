import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import supabase
from logic import formatear_moneda

# Configuración estética
st.set_page_config(page_title="Business Intelligence - Cafetería", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00CC96; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def cargar_datos_maestros():
    try:
        # Cargamos cierres
        res_c = supabase.table("cierres").select("*").order("fecha", desc=False).execute()
        df_c = pd.DataFrame(res_c.data)
        
        # Cargamos pagos y deudas
        res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
        res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
        
        df_p = pd.DataFrame(res_p.data)
        df_d = pd.DataFrame(res_d.data)

        # Procesamiento de Fechas
        if not df_c.empty:
            df_c['fecha'] = pd.to_datetime(df_c['fecha'])
            df_c['dia_semana'] = df_c['fecha'].dt.day_name()
            df_c['mes_año'] = df_c['fecha'].dt.strftime('%Y-%m')

        # Aplanar fecha para pagos
        if not df_p.empty:
            df_p['fecha'] = df_p['cierres'].apply(lambda x: x['fecha'] if isinstance(x, dict) else None)
            df_p['fecha'] = pd.to_datetime(df_p['fecha'])
        
        # Aplanar fecha para deudas
        if not df_d.empty:
            df_d['fecha'] = df_d['cierres'].apply(lambda x: x['fecha'] if isinstance(x, dict) else None)
            df_d['fecha'] = pd.to_datetime(df_d['fecha'])

        return df_c, df_p, df_d
    except Exception as e:
        st.error(f"Error en carga de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_c, df_p, df_d = cargar_datos_maestros()

if df_c.empty:
    st.info("☕ Esperando datos para iniciar el análisis estadístico...")
    st.stop()

# --- FILTROS EN SIDEBAR ---
st.sidebar.title("🛠️ Inteligencia de Negocio")
fecha_inicio = df_c['fecha'].min().date()
fecha_fin = df_c['fecha'].max().date()

# Manejo de rango de fechas
rango = st.sidebar.date_input("Periodo de Análisis", [fecha_inicio, fecha_fin])

if isinstance(rango, list) and len(rango) == 2:
    mask = (df_c['fecha'].dt.date >= rango[0]) & (df_c['fecha'].dt.date <= rango[1])
    df_c_f = df_c[mask]
    ids_periodo = df_c_f['id'].tolist()
    df_p_f = df_p[df_p['cierre_id'].isin(ids_periodo)] if not df_p.empty else pd.DataFrame()
    df_d_f = df_d[df_d['cierre_id'].isin(ids_periodo)] if not df_d.empty else pd.DataFrame()
else:
    df_c_f, df_p_f, df_d_f = df_c, df_p, df_d

st.title("📊 Dashboard Estadístico de Cafetería")

tab1, tab2, tab3 = st.tabs(["🚀 KPIs de Rendimiento", "🕒 Comportamiento Temporal", "🔍 Auditoría Detallada"])

# ==========================================
# TAB 1: KPIs
# ==========================================
with tab1:
    v_total = df_c_f['total_venta_dia'].sum()
    g_total = df_p_f['valor'].sum() if not df_p_f.empty else 0
    utilidad = v_total - g_total
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas Totales", formatear_moneda(v_total))
    c2.metric("Gastos Totales", formatear_moneda(g_total), delta_color="inverse")
    c3.metric("Utilidad Bruta", formatear_moneda(utilidad), delta=f"{(utilidad/v_total*100):.1f}%" if v_total>0 else "0%")
    c4.metric("Días Registrados", len(df_c_f))

    st.divider()
    
    # Gráfico de Área
    df_resumen = df_c_f.groupby('fecha')['total_venta_dia'].sum().reset_index()
    fig_area = px.area(df_resumen, x='fecha', y='total_venta_dia', 
                       title="Flujo de Ventas Diarias", color_discrete_sequence=['#00CC96'], template="plotly_white")
    st.plotly_chart(fig_area, use_container_width=True)

# ==========================================
# TAB 2: COMPORTAMIENTO TEMPORAL
# ==========================================
with tab2:
    st.subheader("¿Cuándo se vende más?")
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Fortaleza por día
        orden_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df_dias = df_c_f.groupby('dia_semana')['total_venta_dia'].mean().reindex(orden_dias).reset_index()
        df_dias['dia_label'] = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
        
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=df_dias['total_venta_dia'],
            theta=df_dias['dia_label'],
            fill='toself', line_color='#636EFA'
        ))
        fig_radar.update_layout(title="Fortaleza Comercial por Día (Promedio)", polar=dict(radialaxis=dict(visible=True)), template="plotly_white")
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_b:
        # Mix de cobro
        mix = df_c_f[['ingreso_efectivo', 'ingresos_nequi']].sum()
        fig_pie = px.pie(values=mix.values, names=['Efectivo', 'Nequi'], 
                         title="Preferencias de Pago Clientes", hole=.4, template="plotly_white")
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# TAB 3: AUDITORÍA DETALLADA
# ==========================================
with tab3:
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("📝 Control de Fiados (Por Cobrar)")
        if not df_d_f.empty:
            display_deudas = df_d_f[['fecha', 'cliente', 'monto', 'telefono']].copy()
            display_deudas['fecha'] = display_deudas['fecha'].dt.date
            st.dataframe(display_deudas, hide_index=True, use_container_width=True)
            st.metric("Total por Cobrar", formatear_moneda(df_d_f['monto'].sum()))
        else:
            st.info("No hay deudas en este periodo.")

    with col_t2:
        st.subheader("💸 Top Gastos")
        if not df_p_f.empty:
            top_gastos = df_p_f.groupby('concepto')['valor'].sum().sort_values(ascending=True).tail(10)
            fig_bar = px.bar(top_gastos, title="Principales Fugas de Dinero (Top 10)", orientation='h', color_discrete_sequence=['#EF553B'], template="plotly_white")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay gastos registrados.")

# --- FOOTER ---
st.divider()
if not df_c_f.empty:
    mejor_dia = df_c_f.loc[df_c_f['total_venta_dia'].idxmax()]
    st.caption(f"💡 Tip estadístico: Su mejor día fue el {mejor_dia['fecha'].date()} vendiendo {formatear_moneda(mejor_dia['total_venta_dia'])}.")