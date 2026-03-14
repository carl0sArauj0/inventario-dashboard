import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import supabase
from logic import formatear_moneda, BILLETES, MONEDAS

# Configuración Estética de Saas Moderno
st.set_page_config(page_title="BI Cafetería - Inteligencia de Datos", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00CC96; }
    .main { background-color: #f8f9fa; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def cargar_datos_maestros():
    try:
        res_c = supabase.table("cierres").select("*").order("fecha", desc=False).execute()
        res_p = supabase.table("pagos").select("*, cierres(fecha)").execute()
        res_d = supabase.table("deudas").select("*, cierres(fecha)").execute()
        
        df_c = pd.DataFrame(res_c.data)
        df_p = pd.DataFrame(res_p.data)
        df_d = pd.DataFrame(res_d.data)

        if not df_c.empty:
            df_c['fecha_dt'] = pd.to_datetime(df_c['fecha'])
            df_c['dia_semana'] = df_c['fecha_dt'].dt.day_name()
            df_c['mes_año'] = df_c['fecha_dt'].dt.strftime('%Y-%m')

        if not df_p.empty:
            df_p['fecha'] = df_p['cierres'].apply(lambda x: x['fecha'] if isinstance(x, dict) else None)
            df_p['fecha'] = pd.to_datetime(df_p['fecha']).dt.date
        
        if not df_d.empty:
            df_d['fecha'] = df_d['cierres'].apply(lambda x: x['fecha'] if isinstance(x, dict) else None)
            df_d['fecha'] = pd.to_datetime(df_d['fecha']).dt.date

        return df_c, df_p, df_d
    except Exception as e:
        st.error(f"Error en carga de datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_c, df_p, df_d = cargar_datos_maestros()

if df_c.empty:
    st.info("☕ Esperando el primer cierre para activar el análisis estadístico...")
    st.stop()

# --- SIDEBAR: FILTROS ---
st.sidebar.title("🛠️ Inteligencia de Negocio")
fecha_rango = st.sidebar.date_input("Periodo de Análisis", [df_c['fecha_dt'].min().date(), df_c['fecha_dt'].max().date()])

# Filtrado de DataFrames
if len(fecha_rango) == 2:
    mask_c = (df_c['fecha_dt'].dt.date >= fecha_rango[0]) & (df_c['fecha_dt'].dt.date <= fecha_rango[1])
    df_c_f = df_c[mask_c]
    ids_f = df_c_f['id'].tolist()
    df_p_f = df_p[df_p['cierre_id'].isin(ids_f)] if not df_p.empty else pd.DataFrame()
    df_d_f = df_d[df_d['cierre_id'].isin(ids_f)] if not df_d.empty else pd.DataFrame()
else:
    df_c_f, df_p_f, df_d_f = df_c, df_p, df_d

st.title("📊 Business Intelligence - Gestión Cafetería")

tabs = st.tabs(["🚀 KPIs Rendimiento", "🕒 Perfil Temporal", "📅 Detalle Diario (Audit)", "🔍 Buscador Global"])

# ==========================================
# TAB 1: KPIs DE RENDIMIENTO
# ==========================================
with tabs[0]:
    v_total = df_c_f['total_venta_dia'].sum()
    g_total = df_p_f['valor'].sum() if not df_p_f.empty else 0
    utilidad = v_total - g_total
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas Netas", formatear_moneda(v_total))
    c2.metric("Gastos Operativos", formatear_moneda(g_total), delta_color="inverse")
    c3.metric("Utilidad Estimada", formatear_moneda(utilidad), delta=f"{(utilidad/v_total*100):.1f}% Margen" if v_total>0 else "0%")
    c4.metric("Días Registrados", len(df_c_f))

    st.divider()
    # Gráfica de Área Moderna
    fig_area = px.area(df_c_f.sort_values('fecha_dt'), x='fecha_dt', y='total_venta_dia', 
                       title="Flujo de Caja: Venta Diaria", color_discrete_sequence=['#00CC96'], template="plotly_white")
    st.plotly_chart(fig_area, use_container_width=True)

# ==========================================
# TAB 2: COMPORTAMIENTO TEMPORAL
# ==========================================
with tabs[1]:
    col_a, col_b = st.columns(2)
    with col_a:
        # Gráfico de Radar de Ventas por Día
        dias_es = {"Monday":"Lun", "Tuesday":"Mar", "Wednesday":"Mie", "Thursday":"Jue", "Friday":"Vie", "Saturday":"Sab", "Sunday":"Dom"}
        orden_d = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df_radar = df_c_f.groupby('dia_semana')['total_venta_dia'].mean().reindex(orden_d).reset_index()
        df_radar['dia_semana'] = df_radar['dia_semana'].map(dias_es)
        
        fig_radar = go.Figure(data=go.Scatterpolar(r=df_radar['total_venta_dia'], theta=df_radar['dia_semana'], fill='toself', line_color='#636EFA'))
        fig_radar.update_layout(title="Fortaleza por Día de la Semana", template="plotly_white")
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_b:
        # Mix de Ingresos Real
        mix_data = df_c_f[['ingreso_efectivo', 'ingresos_nequi']].sum()
        fig_pie = px.pie(values=mix_data.values, names=['Efectivo', 'Nequi'], title="Mix de Métodos de Cobro", hole=.4)
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# TAB 3: DETALLE DIARIO (AUDITORÍA PROFUNDA)
# ==========================================
with tabs[2]:
    st.subheader("Auditoría de un Punto en el Tiempo")
    f_audit = st.date_input("Selecciona el día a auditar:", df_c['fecha_dt'].max().date())
    dia_audit = df_c[df_c['fecha_dt'].dt.date == f_audit]
    
    if dia_audit.empty:
        st.error("No hay registros para este día.")
    else:
        info = dia_audit.iloc[0]
        st.success(f"Responsable del Cierre: **{info.get('responsable')}**")
        
        # Métricas de Auditoría
        k1, k2, k3, k4, k5 = st.columns(4)
        k1.metric("Venta Total", formatear_moneda(info['total_venta_dia']))
        k2.metric("Efectivo Contado", formatear_moneda(info.get('efectivo_en_caja', 0)))
        k3.metric("Ingreso Nequi", formatear_moneda(info.get('ingreso_nequi', 0)))
        k4.metric("Saldo Nequi App", formatear_moneda(info.get('nequi_total_dia', 0)))
        k5.metric("Efectivo Casa", formatear_moneda(info.get('efectivo_en_casa', 0)))

        st.divider()
        
        # Visualización de Billetes (JSON)
        desglose = info.get('desglose_efectivo', {})
        if desglose:
            st.markdown("### 💵 Desglose de Billetes y Monedas")
            data_vis = []
            for b in BILLETES: data_vis.append({"Item": f"${b:,}", "Cant": desglose.get(f"b_{b}", 0)})
            for m in MONEDAS: data_vis.append({"Item": f"${m:,}", "Cant": desglose.get(f"m_{m}", 0)})
            df_vis = pd.DataFrame(data_vis)
            fig_bar_d = px.bar(df_vis[df_vis['Cant']>0], x='Item', y='Cant', color='Cant', title="Inventario de Efectivo en Caja", color_continuous_scale='Viridis')
            st.plotly_chart(fig_bar_d, use_container_width=True)
        
        # Tablas del Día
        c_g, c_f = st.columns(2)
        with c_g:
            st.write("**Gastos del Día:**")
            st.dataframe(df_p[df_p['cierre_id']==info['id']][['concepto', 'valor', 'metodo_pago']], use_container_width=True, hide_index=True)
        with c_f:
            st.write("**Fiados del Día:**")
            st.dataframe(df_d[df_d['cierre_id']==info['id']][['cliente', 'monto', 'telefono']], use_container_width=True, hide_index=True)

# ==========================================
# TAB 4: BUSCADOR GLOBAL & TOP GASTOS
# ==========================================
with tabs[3]:
    col_bus, col_top = st.columns([1, 1.5])
    with col_bus:
        st.subheader("🔍 Buscador de Registros")
        term = st.text_input("Buscar Proveedor o Cliente:")
        if term:
            # Buscar en pagos
            rp = df_p[df_p['concepto'].str.contains(term, case=False, na=False)]
            # Buscar en deudas
            rd = df_d[df_d['cliente'].str.contains(term, case=False, na=False)]
            if not rp.empty: st.write("Pagos:", rp[['fecha','concepto','valor']])
            if not rd.empty: st.write("Fiados:", rd[['fecha','cliente','monto']])

    with col_top:
        st.subheader("💸 Principales Fugas de Efectivo")
        if not df_p_f.empty:
            top_g = df_p_f.groupby('concepto')['valor'].sum().sort_values(ascending=True).tail(10)
            fig_top = px.bar(top_g, orientation='h', title="Top 10 Gastos del Periodo", color_discrete_sequence=['#EF553B'])
            st.plotly_chart(fig_top, use_container_width=True)

# --- FOOTER ---
if not df_c_f.empty:
    mejor = df_c_f.loc[df_c_f['total_venta_dia'].idxmax()]
    st.divider()
    st.caption(f"💡 **Perspectiva Estadística:** Su mejor desempeño fue el {mejor['fecha_dt'].date()} con una venta de {formatear_moneda(mejor['total_venta_dia'])}.")