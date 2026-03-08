import streamlit as st
import pandas as pd
from datetime import date
import requests
from streamlit_lottie import st_lottie
import time
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda, calcular_monto_total
from database import guardar_cierre, guardar_pagos, obtener_cierre_por_fecha, actualizar_cierre, supabase

st.set_page_config(page_title="Cierre de Caja", page_icon="📝", layout="wide")

# --- FUNCIONES DE APOYO ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_success = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_s2lryxtd.json")

st.title("📝 Registro y Actualización de Cierre")

# --- 1. SELECCIÓN DE FECHA ---
col_fecha, col_info = st.columns([1, 2])
with col_fecha:
    fecha_cierre = st.date_input("Fecha", date.today())

registro_previo = obtener_cierre_por_fecha(fecha_cierre)
id_existente = registro_previo['id'] if registro_previo else None

if registro_previo:
    st.warning(f"⚠️ Editando registro del {fecha_cierre}.")
else:
    st.info(f"✨ Nuevo registro para el {fecha_cierre}.")

# --- 2. DATOS GENERALES ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    def_resp = registro_previo.get('responsable', "") if registro_previo else ""
    responsable = st.text_input("Persona Responsable", value=def_resp)
with c2:
    def_base = float(registro_previo.get('base_caja') or 100000.0) if registro_previo else 100000.0
    base_inicial = st.number_input("Base Caja", value=def_base, step=1000.0)

# --- 3. CONTEO DE EFECTIVO ---
st.subheader("💰 Conteo de Billetes y Monedas")
col_bill, col_mon = st.columns(2)
cant_billetes = []
with col_bill:
    for b in BILLETES:
        c = st.number_input(f"Billetes de {formatear_moneda(b)}", min_value=0, key=f"b_{b}_{fecha_cierre}")
        cant_billetes.append(c)

cant_monedas = []
with col_mon:
    for m in MONEDAS:
        c = st.number_input(f"Monedas de {formatear_moneda(m)}", min_value=0, key=f"m_{m}_{fecha_cierre}")
        cant_monedas.append(c)

# --- CÁLCULO PREVIO DE EFECTIVO (Para evitar NameError) ---
efectivo_en_caja = calcular_monto_total(cant_billetes, BILLETES) + calcular_monto_total(cant_monedas, MONEDAS)
ingreso_efectivo_calculado = efectivo_en_caja - base_inicial

# --- 4. GESTIÓN DE DINERO ---
st.divider()
st.subheader("📱 Gestión de Dinero e Ingresos")
c_din1, c_din2, c_din3, c_din4 = st.columns(4)

with c_din1:
    st.info("**Ingreso Efectivo**")
    st.write(f"### {formatear_moneda(ingreso_efectivo_calculado)}")
    st.caption("(Efectivo Caja - Base)")

with c_din2:
    def_v_nequi = float(registro_previo.get('ingresos_nequi') or 0) if registro_previo else 0.0
    ingresos_nequi = st.number_input("Ingresos Nequi (Venta hoy)", value=def_v_nequi, step=1000.0, key=f"vn_{fecha_cierre}")

with c_din3:
    def_s_nequi = float(registro_previo.get('nequi_total_dia') or 0) if registro_previo else 0.0
    nequi_total_dia = st.number_input("Saldo Nequi (App)", value=def_s_nequi, step=1000.0, key=f"sn_{fecha_cierre}")

with c_din4:
    def_casa = float(registro_previo.get('efectivo_en_casa') or 0) if registro_previo else 0.0
    efectivo_en_casa = st.number_input("Efectivo en Casa", value=def_casa, step=1000.0, key=f"casa_{fecha_cierre}")

# --- 5. TABLAS DE GASTOS Y FIADOS ---
st.divider()
col_g, col_d = st.columns(2)

with col_g:
    st.subheader("💸 Gastos / Pagos")
    if registro_previo:
        res_p = supabase.table("pagos").select("*").eq("cierre_id", id_existente).execute()
        df_p = pd.DataFrame(res_p.data)[['concepto', 'valor', 'metodo_pago']]
        df_p.columns = ['Concepto', 'Valor', 'Metodo']
    else:
        df_p = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    
    pagos_editados = st.data_editor(df_p, num_rows="dynamic", use_container_width=True, key=f"p_{fecha_cierre}",
        column_config={"Metodo": st.column_config.SelectboxColumn(options=["Efectivo hoy", "Efectivo ayer", "Nequi"])})

with col_d:
    st.subheader("📝 Fiados (Créditos)")
    if registro_previo:
        res_d = supabase.table("deudas").select("*").eq("cierre_id", id_existente).execute()
        df_d = pd.DataFrame(res_d.data)[['cliente', 'monto']] if res_d.data else pd.DataFrame(columns=['cliente', 'monto'])
        df_d.columns = ['Quien Debe', 'Monto']
    else:
        df_d = pd.DataFrame(columns=["Quien Debe", "Monto"])
    
    deudas_editadas = st.data_editor(df_d, num_rows="dynamic", use_container_width=True, key=f"d_{fecha_cierre}")

# --- 6. CÁLCULOS FINALES ---
st.divider()
lista_pagos = pagos_editados.to_dict('records')
lista_deudas = deudas_editadas.to_dict('records')

res = procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas)

st.subheader("📊 Resumen del Día")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Efectivo en Caja", formatear_moneda(res["efectivo_en_caja"]))
m2.metric("Venta Nequi", formatear_moneda(res["ingresos_nequi"]))
m3.metric("Venta Fiados", formatear_moneda(res["total_fiado"]))
m4.metric("Base Restada", f"- {formatear_moneda(res['base_inicial'])}")
m5.metric("🚀 VENTA TOTAL", formatear_moneda(res["total_venta_dia"]))

# --- 7. BOTÓN GUARDAR ---
st.divider()
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
            
            # Guardar secundarios
            pagos_db = [{"cierre_id": id_existente, "concepto": p['Concepto'], "valor": p['Valor'], "metodo_pago": p['Metodo']} 
                        for p in lista_pagos if p.get('Concepto') and p.get('Valor')]
            if pagos_db: guardar_pagos(pagos_db)
            
            deudas_db = [{"cierre_id": id_existente, "cliente": d['Quien Debe'], "monto": d['Monto']} 
                         for d in lista_deudas if d.get('Quien Debe') and d.get('Monto')]
            if deudas_db: supabase.table("deudas").insert(deudas_db).execute()
            
        with placeholder.container():
            if lottie_success: st_lottie(lottie_success, height=300, key="success")
            st.success("¡Sincronizado!")
            st.balloons()
            time.sleep(3)
        placeholder.empty()
        st.rerun()