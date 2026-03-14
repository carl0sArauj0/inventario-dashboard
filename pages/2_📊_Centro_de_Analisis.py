import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import supabase
from logic import formatear_moneda, BILLETES, MONEDAS

# Configuración estética
st.set_page_config(page_title="Business Intelligence - Cafetería", page_icon="📊", layout="wide")

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
            df_c['fecha'] = pd.to_datetime(df_c['fecha']).dt.date
            df_c['mes'] = pd.to_datetime(df_c['fecha']).dt.strftime('%Y-%m')

        return df_c, df_p, df_d
    except Exception as e:
        st.error(f"Error en carga: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_c, df_p, df_d = cargar_datos_maestros()

if df_c.empty:
    st.info("☕ Esperando datos para iniciar el análisis...")
    st.stop()

# --- TABS ---
tab_mensual, tab_diario, tab_buscador = st.tabs([
    "📈 Análisis Mensual", 
    "📅 Detalle Diario (Auditoría)", 
    "🔍 Buscador Global"
])

# ==========================================
# PESTAÑA 1: ANÁLISIS MENSUAL
# ==========================================
with tab_mensual:
    st.header("Rendimiento Mensual")
    mes_sel = st.selectbox("Selecciona el mes:", df_c['mes'].unique(), index=len(df_c['mes'].unique())-1)
    df_m = df_c[df_c['mes'] == mes_sel]
    ids_m = df_m['id'].tolist()
    
    # KPIs
    v_total = df_m['total_venta_dia'].sum()
    g_total = df_p[df_p['cierre_id'].isin(ids_m)]['valor'].sum() if not df_p.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Venta Bruta", formatear_moneda(v_total))
    c2.metric("Gastos Totales", formatear_moneda(g_total), delta_color="inverse")
    c3.metric("Utilidad Estimada", formatear_moneda(v_total - g_total))
    
    st.divider()
    fig_line = px.line(df_m.sort_values('fecha'), x='fecha', y='total_venta_dia', 
                       title="Comportamiento de Venta Diaria", markers=True, template="plotly_white")
    st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# PESTAÑA 2: DETALLE DIARIO (NUEVO & MEJORADO)
# ==========================================
with tab_diario:
    st.header("Auditoría Detallada del Día")
    f_bus = st.date_input("Consultar Fecha:", df_c['fecha'].max())
    dia_data = df_c[df_c['fecha'] == f_bus]
    
    if dia_data.empty:
        st.error("No hay registros para este día.")
    else:
        info = dia_data.iloc[0]
        st.success(f"Responsable del cierre: **{info.get('responsable', 'N/A')}**")
        
        # 1. KPIs DE VENTA
        st.markdown("### 💰 Resumen de Ventas Reales")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Venta Efectivo", formatear_moneda(info.get('ingreso_efectivo')))
        k2.metric("Venta Nequi", formatear_moneda(info.get('ingresos_nequi')))
        k3.metric("Fiados (No suma)", formatear_moneda(df_d[df_d['cierre_id']==info['id']]['monto'].sum()))
        k4.metric("🚀 VENTA TOTAL", formatear_moneda(info.get('total_venta_dia')))

        st.divider()

        # 2. AUDITORÍA FÍSICA Y DESGLOSE DE BILLETES
        col_aud, col_graf = st.columns([1, 1.5])
        
        with col_aud:
            st.markdown("### 🔍 Auditoría de Caja")
            st.write(f"**Efectivo en Caja (Físico):** {formatear_moneda(info.get('efectivo_en_caja'))}")
            st.write(f"**Base Caja (Fondo):** {formatear_moneda(info.get('base_caja'))}")
            st.write(f"**Saldo Nequi App:** {formatear_moneda(info.get('nequi_total_dia'))}")
            st.write(f"**Efectivo en Casa:** {formatear_moneda(info.get('efectivo_en_casa'))}")
            
            # Mostrar Gastos desglosados
            pagos_este_dia = df_p[df_p['cierre_id'] == info['id']]
            g_hoy = pagos_este_dia[pagos_este_dia['metodo_pago'] == 'Efectivo hoy']['valor'].sum()
            st.write(f"**Gastos pagados hoy:** {formatear_moneda(g_hoy)}")

        with col_graf:
            st.markdown("### 💵 Desglose de Denominaciones")
            desglose = info.get('desglose_efectivo', {})
            if desglose:
                # Preparar datos para gráfica de barras
                data_d = []
                for b in BILLETES: data_d.append({"Denom": f"${b:,}", "Cant": desglose.get(f"b_{b}", 0)})
                for m in MONEDAS: data_d.append({"Denom": f"${m:,}", "Cant": desglose.get(f"m_{m}", 0)})
                
                df_visual = pd.DataFrame(data_d)
                fig_denom = px.bar(df_visual[df_visual['Cant'] > 0], x='Denom', y='Cant', 
                                   title="Cantidad de Billetes/Monedas en Caja",
                                   color_discrete_sequence=['#FFC107'])
                st.plotly_chart(fig_denom, use_container_width=True)
            else:
                st.info("No hay desglose de billetes guardado para esta fecha.")

        st.divider()

        # 3. TABLAS DETALLADAS
        t_gastos, t_fiados = st.columns(2)
        with t_gastos:
            st.subheader("💸 Detalle de Gastos")
            if not pagos_este_dia.empty:
                st.dataframe(pagos_este_dia[['concepto', 'valor', 'metodo_pago']], hide_index=True, use_container_width=True)
            else: st.write("Sin gastos.")

        with t_fiados:
            st.subheader("📝 Detalle de Fiados")
            fiados_este_dia = df_d[df_d['cierre_id'] == info['id']]
            if not fiados_este_dia.empty:
                st.dataframe(fiados_este_dia[['cliente', 'monto', 'telefono']], hide_index=True, use_container_width=True)
            else: st.write("Sin fiados.")

# ==========================================
# PESTAÑA 3: BUSCADOR GLOBAL
# ==========================================
with tab_buscador:
    st.header("Buscador Global")
    term = st.text_input("Buscar proveedor o cliente:")
    if term:
        r_p = df_p[df_p['concepto'].str.contains(term, case=False, na=False)]
        r_d = df_d[df_d['cliente'].str.contains(term, case=False, na=False)]
        
        if not r_p.empty:
            st.write("**Pagos encontrados:**")
            st.dataframe(r_p[['concepto', 'valor', 'metodo_pago']], hide_index=True)
        if not r_d.empty:
            st.write("**Fiados encontrados:**")
            st.dataframe(r_d[['cliente', 'monto', 'telefono']], hide_index=True)