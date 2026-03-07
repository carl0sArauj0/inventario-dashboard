import streamlit as st
import pandas as pd
import request 
from streamlit_lottie import st_lottie
from datetime import date
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda
from database import guardar_cierre, guardar_pagos, obtener_cierre_por_fecha, actualizar_cierre, supabase

st.set_page_config(page_title="Cierre de Caja", page_icon="📝", layout="wide")
st.title("📝 Registro y Actualización de Cierre")

# Función para cargar animaciones Lottie
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Elegimos una animación de éxito (puedes cambiar el link por otro de LottieFiles)
lottie_success = load_lottieurl("https://lottie.host/6253995f-9e32-4e58-9447-e6f77f525547/vL3h5M2U5q.json") # Animación de billetes/éxito

# --- 1. SELECCIÓN DE FECHA Y CARGA DE DATOS ---
col_fecha, col_info = st.columns([1, 2])
with col_fecha:
    fecha_cierre = st.date_input("Selecciona la Fecha", date.today())

# Verificar si ya existe registro para esta fecha
registro_previo = obtener_cierre_por_fecha(fecha_cierre)
id_existente = registro_previo['id'] if registro_previo else None

if registro_previo:
    st.warning(f"⚠️ Editando registro existente del {fecha_cierre}.")
else:
    st.info(f"✨ Creando nuevo registro para el {fecha_cierre}.")

# --- 2. DATOS GENERALES ---
st.divider()
c_gen1, c_gen2 = st.columns(2)
with c_gen1:
    def_resp = registro_previo.get('responsable', "") if registro_previo else ""
    responsable = st.text_input("Persona Responsable", value=def_resp)
with c_gen2:
    def_base = float(registro_previo.get('base_caja') or 100000.0) if registro_previo else 100000.0
    base_inicial = st.number_input("Base de Caja (Fondo)", value=def_base, step=1000.0)

# --- 3. CONTEO DE EFECTIVO ---
st.subheader("💰 Conteo de Billetes y Monedas")
col_bill, col_mon = st.columns(2)
cant_billetes = []
with col_bill:
    for b in BILLETES:
        cant = st.number_input(f"Billetes de {formatear_moneda(b)}", min_value=0, key=f"b_{b}_{fecha_cierre}")
        cant_billetes.append(cant)

cant_monedas = []
with col_mon:
    for m in MONEDAS:
        cant = st.number_input(f"Monedas de {formatear_moneda(m)}", min_value=0, key=f"m_{m}_{fecha_cierre}")
        cant_monedas.append(cant)

# --- 4. DINERO DIGITAL Y CASA ---
st.divider()
st.subheader("📱 Gestión de Dinero")
c_din1, c_din2, c_din3 = st.columns(3)
with c_din1:
    def_v_nequi = float(registro_previo.get('ingresos_nequi') or 0) if registro_previo else 0.0
    ingresos_nequi = st.number_input("Ingresos Nequi (Venta hoy)", value=def_v_nequi, step=1000.0, key=f"vn_{fecha_cierre}")
with c_din2:
    def_s_nequi = float(registro_previo.get('nequi_total_dia') or 0) if registro_previo else 0.0
    nequi_total_dia = st.number_input("Saldo Nequi (App)", value=def_s_nequi, step=1000.0, key=f"sn_{fecha_cierre}")
with c_din3:
    def_casa = float(registro_previo.get('efectivo_en_casa') or 0) if registro_previo else 0.0
    efectivo_en_casa = st.number_input("Efectivo en Casa", value=def_casa, step=1000.0, key=f"casa_{fecha_cierre}")

# --- 5. GASTOS Y FIADOS (TABLAS) ---
st.divider()
col_gastos, col_deudas = st.columns(2)

with col_gastos:
    st.subheader("💸 Gastos / Pagos")
    if registro_previo:
        res_p = supabase.table("pagos").select("*").eq("cierre_id", id_existente).execute()
        df_p_init = pd.DataFrame(res_p.data)[['concepto', 'valor', 'metodo_pago']]
        df_p_init.columns = ['Concepto', 'Valor', 'Metodo']
    else:
        df_p_init = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    
    pagos_editados = st.data_editor(df_p_init, num_rows="dynamic", use_container_width=True, key=f"edit_p_{fecha_cierre}",
        column_config={"Metodo": st.column_config.SelectboxColumn(options=["Efectivo hoy", "Efectivo ayer", "Nequi"])})

with col_deudas:
    st.subheader("📝 Fiados (Ventas a Crédito)")
    if registro_previo:
        res_d = supabase.table("deudas").select("*").eq("cierre_id", id_existente).execute()
        df_d_init = pd.DataFrame(res_d.data)[['cliente', 'monto']] if res_d.data else pd.DataFrame(columns=['cliente', 'monto'])
        df_d_init.columns = ['Quien Debe', 'Monto']
    else:
        df_d_init = pd.DataFrame(columns=["Quien Debe", "Monto"])
    
    deudas_editadas = st.data_editor(df_d_init, num_rows="dynamic", use_container_width=True, key=f"edit_d_{fecha_cierre}")

# --- 6. CÁLCULOS Y RESUMEN ---
st.divider()
lista_pagos = pagos_editados.to_dict('records')
lista_deudas = deudas_editadas.to_dict('records')

res = procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas)

st.subheader("📊 Resumen del Día")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Efectivo Hoy", formatear_moneda(res["ingreso_efectivo"]))
m2.metric("Nequi Hoy", formatear_moneda(res["ingresos_nequi"]))
m3.metric("Fiados Hoy", formatear_moneda(res["total_fiado"]))
m4.metric("Saldo Nequi", formatear_moneda(res["nequi_total_dia"]))
m5.metric("Efectivo Casa", formatear_moneda(res["efectivo_en_casa"]))
m6.metric("🚀 VENTA TOTAL", formatear_moneda(res["total_venta_dia"]))

# --- 7. BOTÓN GUARDAR / ACTUALIZAR ---
label_btn = "🔄 ACTUALIZAR REGISTRO" if registro_previo else "✅ GUARDAR CIERRE"
if st.button(label_btn, use_container_width=True, type="primary"):
    if not responsable:
        st.error("Ingresa el responsable")
    else:
        placeholder = st.empty()
        with st.spinner("Sincronizando..."):
            datos = {
                "fecha": str(fecha_cierre),
                "base_caja": res["base_inicial"],
                "ingreso_efectivo": res["ingreso_efectivo"],
                "ingresos_nequi": res["ingresos_nequi"],
                "nequi_total_dia": res["nequi_total_dia"],
                "efectivo_en_casa": res["efectivo_en_casa"],
                "total_venta_dia": res["total_venta_dia"],
                "responsable": responsable
            }
            
            if registro_previo:
                actualizar_cierre(id_existente, datos)
                supabase.table("pagos").delete().eq("cierre_id", id_existente).execute()
                supabase.table("deudas").delete().eq("cierre_id", id_existente).execute()
            else:
                id_existente = guardar_cierre(datos)
            
            # Guardar Pagos
            pagos_db = [{"cierre_id": id_existente, "concepto": p['Concepto'], "valor": p['Valor'], "metodo_pago": p['Metodo']} 
                        for p in lista_pagos if p.get('Concepto') and p.get('Valor')]
            if pagos_db: guardar_pagos(pagos_db)
            
            # Guardar Deudas
            deudas_db = [{"cierre_id": id_existente, "cliente": d['Quien Debe'], "monto": d['Monto']} 
                         for d in lista_deudas if d.get('Quien Debe') and d.get('Monto')]
            if deudas_db: supabase.table("deudas").insert(deudas_db).execute()
            
        with placeholder.container():
            st_lottie(lottie_success, height=300, key="success_anim")
            st.success(f"🔥 ¡Cierre del {fecha_cierre} sincronizado con éxito!")
            st.balloons() # Dejamos los globos también para más impacto
            
        # Esperar unos segundos y limpiar la animación (opcional)
        import time
        time.sleep(3)
        placeholder.empty()