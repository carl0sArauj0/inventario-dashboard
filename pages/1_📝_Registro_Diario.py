import streamlit as st
import pandas as pd
from datetime import date
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda
from database import guardar_cierre, guardar_pagos

st.set_page_config(page_title="Registro de Cierre", page_icon="📝", layout="wide")
st.title("📝 Registro de Cierre de Caja")

# --- SECCIÓN 1: DATOS GENERALES ---
col_head1, col_head2, col_head3 = st.columns(3)
with col_head1:
    fecha_cierre = st.date_input("Fecha del Cierre", date.today())
with col_head2:
    responsable = st.text_input("Persona Responsable")
with col_head3:
    base_inicial = st.number_input("Base de Caja (Fondo)", min_value=0, value=100000, step=1000)

st.divider()

# --- SECCIÓN 2: CONTEO DE EFECTIVO ---
st.subheader("💰 Conteo de Efectivo (Billetes y Monedas)")
col_bill, col_mon = st.columns(2)
cant_billetes = []
with col_bill:
    for b in BILLETES:
        cant = st.number_input(f"Billetes de {formatear_moneda(b)}", min_value=0, step=1, key=f"b_{b}")
        cant_billetes.append(cant)

cant_monedas = []
with col_mon:
    for m in MONEDAS:
        cant = st.number_input(f"Monedas de {formatear_moneda(m)}", min_value=0, step=1, key=f"m_{m}")
        cant_monedas.append(cant)

st.divider()

# --- SECCIÓN 3: GESTIÓN Y PAGOS ---
col_in, col_out = st.columns(2)
with col_in:
    st.subheader("📱 Gestión de Dinero")
    nequi_total_dia = st.number_input("Nequi Total Día", min_value=0, step=1000)
    efectivo_en_casa = st.number_input("Efectivo en Casa", min_value=0, step=1000)

with col_out:
    st.subheader("💸 Gastos / Pagos")
    df_p = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    pagos_editados = st.data_editor(
        df_p, num_rows="dynamic", use_container_width=True,
        column_config={
            "Metodo": st.column_config.SelectboxColumn("Método", options=["Efectivo hoy", "Efectivo ayer", "Nequi"], default="Efectivo hoy"),
            "Valor": st.column_config.NumberColumn("Monto", format="$ %d")
        }
    )

# --- SECCIÓN 4: CÁLCULOS Y RESUMEN VISUAL ---
st.divider()
lista_pagos = pagos_editados.to_dict('records')
res = procesar_cierre(base_inicial, cant_billetes, cant_monedas, nequi_total_dia, efectivo_en_casa, lista_pagos)

st.subheader("📊 Resumen de Ingresos")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ingreso Efectivo", formatear_moneda(res["ingreso_efectivo"]))
c2.metric("Nequi Total", formatear_moneda(res["nequi_total_dia"]))
c3.metric("Efectivo en Casa", formatear_moneda(res["efectivo_en_casa"]))
c4.metric("🚀 VENTA TOTAL", formatear_moneda(res["total_venta_dia"]))

# Nueva fila diseñada para los Gastos
st.subheader("📉 Resumen de Egresos (Gastos)")
g1, g2, g3, g4 = st.columns(4)

with g1:
    st.write("**Efectivo Hoy**")
    st.write(f"### {formatear_moneda(res['gasto_hoy'])}")

with g2:
    st.write("**Efectivo Ayer**")
    st.write(f"### {formatear_moneda(res['gasto_ayer'])}")

with g3:
    st.write("**Nequi**")
    st.write(f"### {formatear_moneda(res['gasto_nequi'])}")

with g4:
    st.write("**Total Gastos**")
    st.write(f"### :red[{formatear_moneda(res['total_pagos'])}]")

st.divider()

# Mostrar desglose de gastos antes de guardar
st.write(f"**Gastos de hoy:** {formatear_moneda(res['gasto_hoy'])} | **Gastos de ayer:** {formatear_moneda(res['gasto_ayer'])} | **Gastos Nequi:** {formatear_moneda(res['gasto_nequi'])}")

# --- BOTÓN GUARDAR ---
if st.button("✅ GUARDAR CIERRE", use_container_width=True, type="primary"):
    if not responsable:
        st.error("Ingresa el responsable")
    else:
        with st.spinner("Guardando..."):
            datos = {
                "fecha": str(fecha_cierre),
                "base_caja": res["base_inicial"],
                "ingreso_efectivo": res["ingreso_efectivo"],
                "nequi_total_dia": res["nequi_total_dia"],
                "efectivo_en_casa": res["efectivo_en_casa"],
                "total_venta_dia": res["total_venta_dia"],
                "responsable": responsable
            }
            c_id = guardar_cierre(datos)
            if c_id and lista_pagos:
                pagos_db = []
                for p in lista_pagos:
                    if p.get('Concepto') and p.get('Valor'):
                        pagos_db.append({
                            "cierre_id": c_id,
                            "concepto": p['Concepto'],
                            "valor": p['Valor'],
                            "metodo_pago": p['Metodo']
                        })
                guardar_pagos(pagos_db)
            st.success("¡Guardado!")
            st.balloons()