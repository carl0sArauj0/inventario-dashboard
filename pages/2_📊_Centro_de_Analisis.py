import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import supabase
from logic import formatear_moneda, BILLETES, MONEDAS

st.set_page_config(page_title="BI Cafetería - Inteligencia de Datos", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00CC96; }
    .main { background-color: #f8f9fa; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); }
    .graph-caption { color: #555; font-size: 0.9em; margin-top: -15px; margin-bottom: 20px; }
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
            df_c['diferencia_caja'] = df_c['efectivo_en_caja'] - df_c['ingreso_efectivo']

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

st.sidebar.title("🛠️ Inteligencia de Negocio")
fecha_rango = st.sidebar.date_input("Periodo de Análisis", [df_c['fecha_dt'].min().date(), df_c['fecha_dt'].max().date()])

if len(fecha_rango) == 2:
    mask_c = (df_c['fecha_dt'].dt.date >= fecha_rango[0]) & (df_c['fecha_dt'].dt.date <= fecha_rango[1])
    df_c_f = df_c[mask_c].copy()
    ids_f = df_c_f['id'].tolist()
    df_p_f = df_p[df_p['cierre_id'].isin(ids_f)] if not df_p.empty else pd.DataFrame()
    df_d_f = df_d[df_d['cierre_id'].isin(ids_f)] if not df_d.empty else pd.DataFrame()
else:
    df_c_f, df_p_f, df_d_f = df_c.copy(), df_p, df_d

# Preparar datos agregados
if not df_p_f.empty:
    gastos_diarios = df_p_f.groupby('cierre_id').agg(
        total_gastos=('valor', 'sum'),
        gastos_efectivo=('valor', lambda x: x[df_p_f.loc[x.index, 'metodo_pago'].isin(['Efectivo hoy', 'Efectivo ayer'])].sum()),
        gastos_nequi=('valor', lambda x: x[df_p_f.loc[x.index, 'metodo_pago'] == 'Nequi'].sum())
    ).reset_index()
else:
    gastos_diarios = pd.DataFrame(columns=['cierre_id', 'total_gastos', 'gastos_efectivo', 'gastos_nequi'])

if not df_d_f.empty:
    deudas_diarias = df_d_f.groupby('cierre_id').agg(
        total_deudas=('monto', 'sum'),
        num_deudas=('id', 'count')
    ).reset_index()
else:
    deudas_diarias = pd.DataFrame(columns=['cierre_id', 'total_deudas', 'num_deudas'])

# Unir con cierres (corregido)
df_diario = df_c_f.merge(gastos_diarios, left_on='id', right_on='cierre_id', how='left')
df_diario = df_diario.merge(deudas_diarias, left_on='id', right_on='cierre_id', how='left', suffixes=('', '_deuda'))

if 'cierre_id' in df_diario.columns and 'cierre_id_deuda' in df_diario.columns:
    df_diario.drop(columns=['cierre_id_deuda'], inplace=True)

for col in ['total_gastos', 'gastos_efectivo', 'gastos_nequi', 'total_deudas', 'num_deudas']:
    if col in df_diario.columns:
        df_diario[col] = df_diario[col].fillna(0)

df_diario['flujo_neto_efectivo'] = df_diario['ingreso_efectivo'] - df_diario['gastos_efectivo']
df_diario['ratio_gastos_ventas'] = (df_diario['total_gastos'] / df_diario['total_venta_dia'] * 100).fillna(0)

st.title("📊 Business Intelligence - Gestión Cafetería")

tabs = st.tabs(["🚀 KPIs Rendimiento", "🕒 Perfil Temporal", "📅 Detalle Diario (Audit)", "🔮 Análisis Avanzado", "🔍 Buscador Global"])

# ==========================================
# TAB 1: KPIs DE RENDIMIENTO (con descripciones)
# ==========================================
with tabs[0]:
    v_total = df_diario['total_venta_dia'].sum()
    g_total = df_diario['total_gastos'].sum()
    utilidad = v_total - g_total
    deudas_total = df_diario['total_deudas'].sum()
    dif_total = df_diario['diferencia_caja'].sum()
    dias = len(df_diario)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Ventas Netas", formatear_moneda(v_total))
    col2.metric("Gastos Operativos", formatear_moneda(g_total), delta_color="inverse")
    col3.metric("Utilidad Estimada", formatear_moneda(utilidad), delta=f"{(utilidad/v_total*100):.1f}% Margen" if v_total>0 else "0%")
    col4.metric("Nuevas Deudas (Período)", formatear_moneda(deudas_total))
    col5.metric("Días Registrados", dias)

    st.divider()

    # Gráfico de ventas diarias con media móvil
    df_plot = df_diario.sort_values('fecha_dt')
    fig_ventas = go.Figure()
    fig_ventas.add_trace(go.Scatter(x=df_plot['fecha_dt'], y=df_plot['total_venta_dia'],
                                    mode='lines+markers', name='Venta diaria',
                                    line=dict(color='#00CC96')))
    df_plot['media_movil_7'] = df_plot['total_venta_dia'].rolling(7, min_periods=1).mean()
    fig_ventas.add_trace(go.Scatter(x=df_plot['fecha_dt'], y=df_plot['media_movil_7'],
                                    mode='lines', name='Media móvil 7d',
                                    line=dict(color='orange', dash='dash')))
    fig_ventas.update_layout(title="Evolución de Ventas Diarias con Tendencia",
                             xaxis_title="Fecha", yaxis_title="Venta ($)",
                             template="plotly_white")
    st.plotly_chart(fig_ventas, use_container_width=True)
    st.markdown('<p class="graph-caption">📈 Las ventas diarias (verde) y su tendencia suavizada (naranja). Si la línea naranja baja durante varios días, revisa qué está pasando (días festivos, promociones, competencia).</p>', unsafe_allow_html=True)

    # Segunda fila: Sobrantes/Faltantes y Ratio Gastos/Ventas
    col_a, col_b = st.columns(2)
    with col_a:
        fig_dif = px.bar(df_diario, x='fecha_dt', y='diferencia_caja',
                         title="Sobrantes / Faltantes Diarios",
                         labels={'diferencia_caja': 'Diferencia ($)', 'fecha_dt': 'Fecha'},
                         color='diferencia_caja', color_continuous_scale=['red','yellow','green'])
        fig_dif.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig_dif, use_container_width=True)
        st.markdown('<p class="graph-caption">💰 Diferencia entre el efectivo que debería haber (según ventas) y el que contaste. Valores altos (positivos o negativos) pueden indicar errores de conteo o problemas en el manejo de caja.</p>', unsafe_allow_html=True)
    with col_b:
        fig_ratio = px.line(df_diario, x='fecha_dt', y='ratio_gastos_ventas',
                            title="% Gastos sobre Ventas",
                            labels={'ratio_gastos_ventas': '% Gastos', 'fecha_dt': 'Fecha'})
        fig_ratio.add_hline(y=df_diario['ratio_gastos_ventas'].mean(), line_dash="dash",
                            annotation_text=f"Promedio: {df_diario['ratio_gastos_ventas'].mean():.1f}%")
        st.plotly_chart(fig_ratio, use_container_width=True)
        st.markdown('<p class="graph-caption">📊 Porcentaje de tus ventas que se va en gastos. Si un día supera mucho el promedio, revisa los gastos de ese día para controlar fugas.</p>', unsafe_allow_html=True)

# ==========================================
# TAB 2: PERFIL TEMPORAL (con descripciones)
# ==========================================
with tabs[1]:
    col_c, col_d = st.columns(2)
    with col_c:
        orden_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df_c_f['dia_semana'] = pd.Categorical(df_c_f['dia_semana'], categories=orden_dias, ordered=True)
        fig_box = px.box(df_c_f, x='dia_semana', y='total_venta_dia',
                         title="Distribución de Ventas por Día de la Semana",
                         labels={'dia_semana': 'Día', 'total_venta_dia': 'Venta ($)'},
                         color='dia_semana', color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_box, use_container_width=True)
        st.markdown('<p class="graph-caption">📅 La caja muestra el rango típico de ventas para cada día. La línea del medio es la mediana (valor típico). Identifica tus días fuertes y débiles para planificar promociones o descansos.</p>', unsafe_allow_html=True)

    with col_d:
        df_melt = df_diario.melt(id_vars='fecha_dt', value_vars=['ingreso_efectivo', 'ingresos_nequi'],
                                 var_name='metodo', value_name='monto')
        fig_stack = px.area(df_melt, x='fecha_dt', y='monto', color='metodo',
                           title="Composición de Ingresos en el Tiempo",
                           labels={'monto': 'Monto ($)', 'fecha_dt': 'Fecha'},
                           color_discrete_map={'ingreso_efectivo': '#00CC96', 'ingresos_nequi': '#636EFA'})
        st.plotly_chart(fig_stack, use_container_width=True)
        st.markdown('<p class="graph-caption">💳 Cómo se mezclan tus ingresos: efectivo (verde) y Nequi (azul). Si el área azul crece, considera promociones para pago digital o revisa comisiones.</p>', unsafe_allow_html=True)

    # Segunda fila: Efectivo en caja vs en casa y Gastos diarios
    col_e, col_f = st.columns(2)
    with col_e:
        fig_efectivo = go.Figure()
        fig_efectivo.add_trace(go.Scatter(x=df_diario['fecha_dt'], y=df_diario['efectivo_en_caja'],
                                          mode='lines', name='Efectivo en Caja'))
        fig_efectivo.add_trace(go.Scatter(x=df_diario['fecha_dt'], y=df_diario['efectivo_en_casa'],
                                          mode='lines', name='Efectivo en Casa'))
        fig_efectivo.update_layout(title="Evolución del Efectivo (Caja vs Casa)",
                                   xaxis_title="Fecha", yaxis_title="Monto ($)",
                                   template="plotly_white")
        st.plotly_chart(fig_efectivo, use_container_width=True)
        st.markdown('<p class="graph-caption">🏦 Compara cuánto dinero dejas en caja vs. cuánto retiras a casa. Sirve para controlar la liquidez y evitar acumular mucho efectivo en el local.</p>', unsafe_allow_html=True)
    with col_f:
        fig_gastos = px.line(df_diario, x='fecha_dt', y='total_gastos',
                             title="Gastos Diarios",
                             labels={'total_gastos': 'Gastos ($)', 'fecha_dt': 'Fecha'})
        st.plotly_chart(fig_gastos, use_container_width=True)
        st.markdown('<p class="graph-caption">💸 La evolución de tus gastos día a día. Picos altos pueden ser compras grandes o pagos inusuales; revisa si están justificados.</p>', unsafe_allow_html=True)

# ==========================================
# TAB 3: DETALLE DIARIO (AUDIT) - Igual, pero añadimos descripción al desglose
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
        
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Venta Total", formatear_moneda(info['total_venta_dia']))
        k2.metric("Efectivo Contado", formatear_moneda(info.get('efectivo_en_caja', 0)))
        k3.metric("Ingreso Nequi", formatear_moneda(info.get('ingresos_nequi', 0)))
        k4.metric("Saldo Nequi App", formatear_moneda(info.get('nequi_total_dia', 0)))
        k5.metric("Efectivo Casa", formatear_moneda(info.get('efectivo_en_casa', 0)))

        st.divider()
        
        desglose = info.get('desglose_efectivo', {})
        if desglose:
            st.markdown("### 💵 Desglose de Billetes y Monedas")
            data_vis = []
            for b in BILLETES: data_vis.append({"Item": f"${b:,}", "Cant": desglose.get(f"b_{b}", 0)})
            for m in MONEDAS: data_vis.append({"Item": f"${m:,}", "Cant": desglose.get(f"m_{m}", 0)})
            df_vis = pd.DataFrame(data_vis)
            fig_bar_d = px.bar(df_vis[df_vis['Cant']>0], x='Item', y='Cant', color='Cant', title="Inventario de Efectivo en Caja", color_continuous_scale='Viridis')
            st.plotly_chart(fig_bar_d, use_container_width=True)
            st.markdown('<p class="graph-caption">🔍 Cuántos billetes y monedas de cada denominación tenías al final del día. Te ayuda a pedir cambio para el día siguiente.</p>', unsafe_allow_html=True)
        
        c_g, c_f = st.columns(2)
        with c_g:
            st.write("**Gastos del Día:**")
            st.dataframe(df_p[df_p['cierre_id']==info['id']][['concepto', 'valor', 'metodo_pago']], use_container_width=True, hide_index=True)
        with c_f:
            st.write("**Fiados del Día:**")
            st.dataframe(df_d[df_d['cierre_id']==info['id']][['cliente', 'monto', 'telefono']], use_container_width=True, hide_index=True)

# ==========================================
# TAB 4: ANÁLISIS AVANZADO (con descripciones)
# ==========================================
with tabs[3]:
    st.subheader("🔮 Métricas Avanzadas de Gestión")

    col_adv1, col_adv2 = st.columns(2)
    with col_adv1:
        fig_flujo = px.bar(df_diario, x='fecha_dt', y='flujo_neto_efectivo',
                           title="Flujo Neto de Efectivo Diario",
                           labels={'flujo_neto_efectivo': 'Flujo Neto ($)', 'fecha_dt': 'Fecha'},
                           color='flujo_neto_efectivo', color_continuous_scale=['red','yellow','green'])
        fig_flujo.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig_flujo, use_container_width=True)
        st.markdown('<p class="graph-caption">💵 Dinero en efectivo que realmente te queda después de pagar gastos en efectivo. Si es negativo varios días, podrías tener problemas de liquidez (necesitas más efectivo del que entra).</p>', unsafe_allow_html=True)

        if not df_d_f.empty:
            top_clientes = df_d_f.groupby('cliente')['monto'].sum().sort_values(ascending=False).head(10)
            fig_top_deudores = px.bar(top_clientes, x=top_clientes.values, y=top_clientes.index,
                                      orientation='h', title="Top 10 Clientes Deudores",
                                      labels={'x': 'Monto Total Adeudado', 'y': 'Cliente'},
                                      color=top_clientes.values, color_continuous_scale='Reds')
            st.plotly_chart(fig_top_deudores, use_container_width=True)
            st.markdown('<p class="graph-caption">🧾 Los clientes que más dinero te deben. Prioriza contactarlos para cobrar y evitar morosidad.</p>', unsafe_allow_html=True)
        else:
            st.info("No hay datos de deudas en el período.")

    with col_adv2:
        fig_deudas = px.bar(df_diario, x='fecha_dt', y='total_deudas',
                            title="Nuevas Deudas por Día",
                            labels={'total_deudas': 'Monto de nuevas deudas ($)', 'fecha_dt': 'Fecha'})
        st.plotly_chart(fig_deudas, use_container_width=True)
        st.markdown('<p class="graph-caption">📆 Monto de ventas fiadas cada día. Si aumenta, revisa si estás dando crédito sin control.</p>', unsafe_allow_html=True)

        if not df_p_f.empty:
            gastos_metodo = df_p_f.groupby('metodo_pago')['valor'].sum().reset_index()
            fig_gastos_metodo = px.pie(gastos_metodo, values='valor', names='metodo_pago',
                                       title="Distribución de Gastos por Método",
                                       hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_gastos_metodo, use_container_width=True)
            st.markdown('<p class="graph-caption">💳 Cómo pagas tus gastos: efectivo de hoy, efectivo de ahorros (ayer) o Nequi. Te ayuda a ver si dependes mucho de un método y su impacto en liquidez.</p>', unsafe_allow_html=True)
        else:
            st.info("No hay gastos en el período.")

    st.divider()

    st.subheader("Composición Promedio del Efectivo en Caja")
    denominaciones_acum = {f"b_{b}": 0 for b in BILLETES}
    denominaciones_acum.update({f"m_{m}": 0 for m in MONEDAS})
    count_dias_con_desglose = 0
    for _, row in df_c_f.iterrows():
        desg = row.get('desglose_efectivo')
        if desg and isinstance(desg, dict):
            count_dias_con_desglose += 1
            for key in denominaciones_acum:
                denominaciones_acum[key] += desg.get(key, 0)
    if count_dias_con_desglose > 0:
        for key in denominaciones_acum:
            denominaciones_acum[key] /= count_dias_con_desglose
        df_denom_prom = pd.DataFrame([
            {"Denominación": f"${k.split('_')[1]} {('billete' if k.startswith('b') else 'moneda')}",
             "Cantidad promedio": v}
            for k, v in denominaciones_acum.items() if v > 0
        ])
        fig_denom = px.bar(df_denom_prom, x='Denominación', y='Cantidad promedio',
                          title="Cantidad promedio de billetes/monedas por día",
                          color='Cantidad promedio', color_continuous_scale='Blues')
        st.plotly_chart(fig_denom, use_container_width=True)
        st.markdown('<p class="graph-caption">📊 En promedio, cuántos billetes y monedas de cada denominación tienes al final del día. Te sirve para saber qué cambio necesitas pedir al banco (por ejemplo, si siempre faltan monedas de $500).</p>', unsafe_allow_html=True)
    else:
        st.info("No hay datos de desglose de efectivo en el período.")

    st.subheader("Predicción de Ventas (Media Móvil)")
    ventas_series = df_diario.set_index('fecha_dt')['total_venta_dia']
    if len(ventas_series) >= 7:
        pred = ventas_series.rolling(7).mean().iloc[-1]
        st.metric("Pronóstico próximo día (media móvil 7d)", formatear_moneda(pred))
        st.markdown('<p class="graph-caption">🔮 Estimación de ventas para mañana basada en el promedio de los últimos 7 días. Úsalo como referencia, pero recuerda que pueden haber variaciones.</p>', unsafe_allow_html=True)
    else:
        st.info("Se necesitan al menos 7 días de datos para una predicción simple.")

# ==========================================
# TAB 5: BUSCADOR GLOBAL (sin cambios, pero añadimos caption)
# ==========================================
with tabs[4]:
    col_bus, col_top = st.columns([1, 1.5])
    with col_bus:
        st.subheader("🔍 Buscador de Registros")
        term = st.text_input("Buscar Proveedor o Cliente:")
        if term:
            rp = df_p[df_p['concepto'].str.contains(term, case=False, na=False)]
            rd = df_d[df_d['cliente'].str.contains(term, case=False, na=False)]
            if not rp.empty: 
                st.write("Pagos:", rp[['fecha','concepto','valor']])
            if not rd.empty: 
                st.write("Fiados:", rd[['fecha','cliente','monto']])
        st.markdown('<p class="graph-caption">🔎 Busca rápidamente movimientos por nombre de proveedor (en gastos) o cliente (en deudas).</p>', unsafe_allow_html=True)

    with col_top:
        st.subheader("💸 Principales Fugas de Efectivo")
        if not df_p_f.empty:
            top_g = df_p_f.groupby('concepto')['valor'].sum().sort_values(ascending=True).tail(10)
            fig_top = px.bar(top_g, orientation='h', title="Top 10 Gastos del Periodo", color_discrete_sequence=['#EF553B'])
            st.plotly_chart(fig_top, use_container_width=True)
            st.markdown('<p class="graph-caption">🚨 Los conceptos donde más dinero has gastado en total. Revisa si estos gastos son necesarios o si puedes reducirlos.</p>', unsafe_allow_html=True)

# --- FOOTER ---
if not df_c_f.empty:
    mejor = df_c_f.loc[df_c_f['total_venta_dia'].idxmax()]
    st.divider()
    st.caption(f"💡 **Perspectiva Estadística:** Su mejor desempeño fue el {mejor['fecha_dt'].date()} con una venta de {formatear_moneda(mejor['total_venta_dia'])}.")