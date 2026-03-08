import streamlit as st
import pandas as pd
from datetime import date
import requests
from streamlit_lottie import st_lottie
import time
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda, calcular_monto_total
from database import guardar_cierre, guardar_pagos, obtener_cierre_por_fecha, actualizar_cierre, supabase

st.set_page_config(page_title="Registro de Cierre", page_icon="📝", layout="wide")

# --- ANIMACIÓN LOTTIE ---
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
    fecha_cierre = st.date_input("Fecha de Trabajo", date.today())

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
    base_inicial = st.number_input("Base Caja (Fondo Informativo)", value=def_base, step=1000.0)

# --- 3. CONTEO FÍSICO ---
st.subheader("💰 Conteo de Billetes y Monedas (Auditoría)")
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

# --- 4. INGRESOS Y GESTIÓN ---
st.divider()
st.subheader("📱 Ingresos Manuales y Saldos")
c_in1, c_in2, c_in3, c_in4 = st.columns(4)

with c_in1:
    def_ief = float(registro_previo.get('ingreso_efectivo') or 0.0) if registro_previo else 0.0
    ingreso_efectivo_manual = st.number_input("Ingreso Efectivo (Venta)", value=def_ief, step=1000.0, key=f"ief_{fecha_cierre}")
with c_in2:
    def_vnequi = float(registro_previo.get('ingresos_nequi') or 0.0) if registro_previo else 0.0
    ingresos_nequi = st.number_input("Ingreso Nequi (Venta)", value=def_vnequi, step=1000.0, key=f"vn_{fecha_cierre}")
with c_in3:
    def_snequi = float(registro_previo.get('nequi_total_dia') or 0.0) if registro_previo else 0.0
    nequi_total_dia = st.number_input("Saldo App Nequi", value=def_snequi, step=1000.0, key=f"sn_{fecha_cierre}")
with c_in4:
    def_casa = float(registro_previo.get('efectivo_en_casa') or 0.0) if registro_previo else 0.0
    efectivo_en_casa = st.number_input("Efectivo en Casa", value=def_casa, step=1000.0, key=f"casa_{fecha_cierre}")

# --- 5. TABLAS DE GASTOS Y FIADOS ---
st.divider()
col_g, col_d = st.columns(2) # Definimos col_g y col_d

with col_g:
    st.subheader("💸 Gastos / Pagos")
    if registro_previo:
        res_p_data = supabase.table("pagos").select("*").eq("cierre_id", id_existente).execute().data
        df_p = pd.DataFrame(res_p_data)
        if not df_p.empty:
            df_p_init = df_p[['concepto', 'valor', 'metodo_pago']].rename(columns={'concepto':'Concepto','valor':'Valor','metodo_pago':'Metodo'})
        else:
            df_p_init = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    else:
        df_p_init = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    
    pagos_editados = st.data_editor(df_p_init, num_rows="dynamic", use_container_width=True, key=f"p_{fecha_cierre}",
        column_config={"Metodo": st.column_config.SelectboxColumn(options=["Efectivo hoy", "Efectivo ayer", "Nequi"])})

with col_d: # Corregido: antes decía col_deudas
    st.subheader("📝 Fiados (Créditos)")
    if registro_previo:
        res_d_data = supabase.table("deudas").select("*").eq("cierre_id", id_existente).execute().data
        df_d = pd.DataFrame(res_d_data)
        if not df_d.empty:
            df_d_init = df_d[['cliente', 'monto']].rename(columns={'cliente':'Quien Debe','monto':'Monto'})
        else:
            df_d_init = pd.DataFrame(columns=["Quien Debe", "Monto"])
    else:
        df_d_init = pd.DataFrame(columns=["Quien Debe", "Monto"])
    
    deudas_editadas = st.data_editor(df_d_init, num_rows="dynamic", use_container_width=True, key=f"d_{fecha_cierre}")

# --- 6. CÁLCULOS Y RESUMEN ---
st.divider()
lista_pagos = pagos_editados.to_dict('records')
lista_deudas = deudas_editadas.to_dict('records')

res = procesar_cierre(
    base_inicial, cant_billetes, cant_monedas, 
    ingreso_efectivo_manual, ingresos_nequi, 
    nequi_total_dia, efectivo_en_casa, 
    lista_pagos, lista_deudas
)

st.subheader("📊 Resumen del Día")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Venta Efectivo", formatear_moneda(res["ingreso_efectivo"]))
m2.metric("Venta Nequi", formatear_moneda(res["ingresos_nequi"]))
m3.metric("🚀 VENTA TOTAL", formatear_moneda(res["venta_total"]))
m4.metric("Efectivo en Caja", formatear_moneda(res["efectivo_caja"]), help="Suma física de billetes y monedas")

st.write(f"**Fiados de hoy (Informativo):** {formatear_moneda(res['total_fiado'])} | **Total Gastos:** {formatear_moneda(res['total_pagos'])}")

# --- 7. BOTÓN GUARDAR ---
if st.button("✅ GUARDAR / ACTUALIZAR", use_container_width=True, type="primary"):
    if not responsable:
        st.error("Por favor ingresa el nombre del responsable.")
    else:
        with st.spinner("Guardando en la base de datos..."):
            datos = {
                "fecha": str(fecha_cierre),
                "base_caja": res["base_inicial"],
                "ingreso_efectivo": res["ingreso_efectivo"],
                "ingresos_nequi": res["ingresos_nequi"],
                "efectivo_en_caja": res["efectivo_caja"],
                "nequi_total_dia": res["nequi_total_dia"],
                "efectivo_en_casa": res["efectivo_en_casa"],
                "total_venta_dia": res["venta_total"],
                "responsable": responsable
            }
            
            if registro_previo:
                actualizar_cierre(id_existente, datos)
                supabase.table("pagos").delete().eq("cierre_id", id_existente).execute()
                supabase.table("deudas").delete().eq("cierre_id", id_existente).execute()
            else:
                id_existente = guardar_cierre(datos)
            
            # Guardar Pagos
            p_db = [{"cierre_id": id_existente, "concepto": p['Concepto'], "valor": p['Valor'], "metodo_pago": p['Metodo']} 
                    for p in lista_pagos if p.get('Concepto') and p.get('Valor')]
            if p_db: guardar_pagos(p_db)
            
            # Guardar Deudas
            d_db = [{"cierre_id": id_existente, "cliente": d['Quien Debe'], "monto": d['Monto']} 
                    for d in lista_deudas if d.get('Quien Debe') and d.get('Monto')]
            if d_db: supabase.table("deudas").insert(d_db).execute()

        placeholder = st.empty()
        with placeholder.container():
            if lottie_success:
                st_lottie(lottie_success, height=300, key="success")
            st.success("¡Cierre sincronizado con éxito!")
            st.balloons()
            time.sleep(3)
        placeholder.empty()
        st.rerun()