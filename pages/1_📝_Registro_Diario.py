import streamlit as st
import pandas as pd
from datetime import date
import requests
from streamlit_lottie import st_lottie
import time
import re # Para limpiar el texto
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda, calcular_monto_total
from database import guardar_cierre, guardar_pagos, obtener_cierre_por_fecha, actualizar_cierre, supabase

st.set_page_config(page_title="Cierre de Caja", page_icon="📝", layout="wide")

# --- FUNCIÓN ESPECIAL PARA INPUT CON COMAS ---
def input_moneda_inteligente(label, value_def, key):
    """Crea un cuadro de texto que muestra comas al dar Enter"""
    # 1. Formatear el valor inicial con comas
    val_formateado = f"{int(value_def):,}" if value_def > 0 else ""
    
    # 2. Crear el text_input
    texto_usuario = st.text_input(label, value=val_formateado, key=key, help="Presiona Enter para aplicar el formato")
    
    # 3. Limpiar el texto (quitar comas y puntos) para convertirlo en número
    numero_limpio = re.sub(r'[^\d]', '', texto_usuario)
    
    return int(numero_limpio) if numero_limpio else 0

def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_success = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_s2lryxtd.json")

st.title("📝 Registro de Cierre Automatizado")

# --- 1. FECHA ---
col_f, col_i = st.columns([1, 2])
with col_f:
    fecha_cierre = st.date_input("Fecha de Trabajo", date.today())

registro_previo = obtener_cierre_por_fecha(fecha_cierre)
id_existente = registro_previo['id'] if registro_previo else None
desglose_previo = registro_previo.get('desglose_efectivo') or {} if registro_previo else {}

# --- 2. DATOS GENERALES ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    def_resp = registro_previo.get('responsable', "") if registro_previo else ""
    responsable = st.text_input("Persona Responsable", value=def_resp)
with c2:
    # --- CAMBIO A INPUT INTELIGENTE ---
    def_base = int(registro_previo.get('base_caja') or 100000) if registro_previo else 100000
    base_inicial = input_moneda_inteligente("Base Caja (Fondo)", def_base, f"base_{fecha_cierre}")

# --- 3. CONTEO FÍSICO ---
st.subheader("💰 1. Conteo de Dinero en Caja")
col_bill, col_mon = st.columns(2)

cant_billetes = []
with col_bill:
    for b in BILLETES:
        val_default = int(desglose_previo.get(f"b_{b}", 0))
        # Para billetes mantenemos number_input porque son cantidades pequeñas (1, 2, 5...)
        cant = st.number_input(f"Billetes de {formatear_moneda(b)}", min_value=0, value=val_default, key=f"b_{b}_{fecha_cierre}", format="%d")
        cant_billetes.append(cant)

cant_monedas = []
with col_mon:
    for m in MONEDAS:
        val_default = int(desglose_previo.get(f"m_{m}", 0))
        cant = st.number_input(f"Monedas de {formatear_moneda(m)}", min_value=0, value=val_default, key=f"m_{m}_{fecha_cierre}", format="%d")
        cant_monedas.append(cant)

# --- 4. TABLAS ---
st.divider()
st.subheader("💸 2. Gastos y Fiados")
col_g, col_d = st.columns(2)

with col_g:
    st.write("**Gastos / Pagos**")
    if registro_previo:
        df_p = pd.DataFrame(supabase.table("pagos").select("*").eq("cierre_id", id_existente).execute().data)
        df_p_init = df_p[['concepto', 'valor', 'metodo_pago']].rename(columns={'concepto':'Concepto','valor':'Valor','metodo_pago':'Metodo'}) if not df_p.empty else pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    else:
        df_p_init = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    
    pagos_editados = st.data_editor(df_p_init, num_rows="dynamic", use_container_width=True, key=f"p_{fecha_cierre}",
        column_config={
            "Metodo": st.column_config.SelectboxColumn(options=["Efectivo hoy", "Efectivo ayer", "Nequi"]),
            "Valor": st.column_config.NumberColumn("Valor ($)", format="$ %d")
        })

with col_d:
    st.write("**Ventas Fiadas (Créditos)**")
    if registro_previo:
        df_d = pd.DataFrame(supabase.table("deudas").select("*").eq("cierre_id", id_existente).execute().data)
        df_d_init = df_d[['cliente', 'monto', 'telefono']].rename(columns={'cliente':'Quien Debe','monto':'Monto', 'telefono':'Teléfono'}) if not df_d.empty else pd.DataFrame(columns=["Quien Debe", "Monto", "Teléfono"])
    else:
        df_d_init = pd.DataFrame(columns=["Quien Debe", "Monto", "Teléfono"])
    
    deudas_editadas = st.data_editor(df_d_init, num_rows="dynamic", use_container_width=True, key=f"d_{fecha_cierre}",
        column_config={
            "Monto": st.column_config.NumberColumn("Monto ($)", format="$ %d")
        })

# --- 5. INGRESOS DIGITALES (INPUTS INTELIGENTES) ---
st.divider()
st.subheader("📱 3. Nequi y Otros")
c_in1, c_in2, c_in3 = st.columns(3)

with c_in1:
    def_vn = int(registro_previo.get('ingresos_nequi') or 0) if registro_previo else 0
    ingresos_nequi = input_moneda_inteligente("Ingreso Nequi (Venta hoy)", def_vn, f"vn_{fecha_cierre}")

with c_in2:
    def_sn = int(registro_previo.get('nequi_total_dia') or 0) if registro_previo else 0
    nequi_total_dia = input_moneda_inteligente("Saldo App Nequi", def_sn, f"sn_{fecha_cierre}")

with c_in3:
    def_casa = int(registro_previo.get('efectivo_en_casa') or 0) if registro_previo else 0
    efectivo_en_casa = input_moneda_inteligente("Efectivo en Casa", def_casa, f"casa_{fecha_cierre}")

# --- 6. CÁLCULOS ---
st.divider()
res = procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, pagos_editados.to_dict('records'), deudas_editadas.to_dict('records'))

st.subheader("📊 Resumen de Resultados")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Venta Efectivo", formatear_moneda(res["ingreso_efectivo"]))
m2.metric("Venta Nequi", formatear_moneda(res["ingresos_nequi"]))
m3.metric("Venta Fiados", formatear_moneda(res["total_fiado"]))
m4.metric("🚀 VENTA TOTAL", formatear_moneda(res["venta_total"]))

st.divider()
st.subheader("📉 Auditoría de Gastos y Caja")
e1, e2, e3, e4 = st.columns(4)
with e1:
    st.error("**Total Gastos**")
    st.write(f"### {formatear_moneda(res['total_pagos'])}")
    st.markdown(f"De hoy: **{formatear_moneda(res['gasto_hoy'])}**")
    st.markdown(f"De ayer: **{formatear_moneda(res['gasto_ayer'])}**")
    st.markdown(f"Nequi: **{formatear_moneda(res['gasto_nequi'])}**")
with e2:
    st.info("**Efectivo en Caja**")
    st.write(f"### {formatear_moneda(res['efectivo_caja'])}")
with e3:
    st.info("**Efectivo en Casa**")
    st.write(f"### {formatear_moneda(res['efectivo_en_casa'])}")
with e4:
    st.warning("**Saldo Nequi App**")
    st.write(f"### {formatear_moneda(res['nequi_total_dia'])}")

# --- 7. GUARDAR ---
if st.button("✅ GUARDAR / ACTUALIZAR", use_container_width=True, type="primary"):
    if not responsable: st.error("Ingresa responsable")
    else:
        with st.spinner("Guardando..."):
            dict_desglose = {}
            for b, cant in zip(BILLETES, cant_billetes): dict_desglose[f"b_{b}"] = cant
            for m, cant in zip(MONEDAS, cant_monedas): dict_desglose[f"m_{m}"] = cant

            datos = {
                "fecha": str(fecha_cierre), "base_caja": res["base_inicial"], "ingreso_efectivo": res["ingreso_efectivo"],
                "ingresos_nequi": res["ingresos_nequi"], "efectivo_en_caja": res["efectivo_caja"],
                "nequi_total_dia": res["nequi_total_dia"], "efectivo_en_casa": res["efectivo_en_casa"],
                "total_venta_dia": res["venta_total"], "responsable": responsable,
                "desglose_efectivo": dict_desglose 
            }
            if registro_previo:
                actualizar_cierre(id_existente, datos)
                supabase.table("pagos").delete().eq("cierre_id", id_existente).execute()
                supabase.table("deudas").delete().eq("cierre_id", id_existente).execute()
            else: id_existente = guardar_cierre(datos)
            
            p_db = [{"cierre_id": id_existente, "concepto": p['Concepto'], "valor": p['Valor'], "metodo_pago": p['Metodo']} for p in pagos_editados.to_dict('records') if p.get('Concepto')]
            if p_db: guardar_pagos(p_db)
            d_db = [{"cierre_id": id_existente, "cliente": d['Quien Debe'], "monto": d['Monto'], "telefono": d.get('Teléfono')} for d in deudas_editadas.to_dict('records') if d.get('Quien Debe')]
            if d_db: supabase.table("deudas").insert(d_db).execute()

        placeholder = st.empty()
        with placeholder.container():
            if lottie_success: st_lottie(lottie_success, height=200, key="success")
            st.success("¡Sincronizado!")
            st.balloons()
            time.sleep(2)
        st.rerun()