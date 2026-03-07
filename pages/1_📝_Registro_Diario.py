import streamlit as st
import pandas as pd
from datetime import date
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda
from database import guardar_cierre, guardar_pagos

st.set_page_config(page_title="Registro de Cierre", page_icon="📝", layout="wide")
st.title("📝 Registro de Cierre de Caja")

# --- 1. DATOS GENERALES ---
col_head1, col_head2, col_head3 = st.columns(3)
with col_head1:
    fecha_cierre = st.date_input("Fecha del Cierre", date.today())
with col_head2:
    responsable = st.text_input("Persona Responsable")
with col_head3:
    base_inicial = st.number_input("Base de Caja (Fondo)", min_value=0, value=100000, step=1000)

st.divider()

# --- 2. CONTEO DE EFECTIVO ---
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

# --- 3. GESTIÓN DE DINERO Y PAGOS ---
col_in, col_out = st.columns(2)

with col_in:
    st.subheader("📱 Gestión de Dinero")
    ingresos_nequi = st.number_input("Ingresos Nequi (Ventas de hoy)", min_value=0, step=1000)
    nequi_total_dia = st.number_input("Nequi Total Día (Saldo App)", min_value=0, step=1000)
    efectivo_en_casa = st.number_input("Efectivo en Casa", min_value=0, step=1000)

with col_out:
    st.subheader("💸 Gastos / Pagos")
    df_p = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    # AQUÍ SE DEFINE pagos_editados
    pagos_editados = st.data_editor(
        df_p, num_rows="dynamic", use_container_width=True,
        column_config={
            "Metodo": st.column_config.SelectboxColumn("Método", options=["Efectivo hoy", "Efectivo ayer", "Nequi"], default="Efectivo hoy"),
            "Valor": st.column_config.NumberColumn("Monto", format="$ %d")
        },
        key="editor_pagos"
    )

# --- 4. CÁLCULOS (Ahora lista_pagos está después del editor) ---
st.divider()
lista_pagos = pagos_editados.to_dict('records') # Ahora sí existe la variable

# Llamada a la lógica actualizada
res = procesar_cierre(
    base_inicial, 
    cant_billetes, 
    cant_monedas, 
    ingresos_nequi, 
    nequi_total_dia, 
    efectivo_en_casa, 
    lista_pagos
)

# --- 5. RESUMEN VISUAL ---
st.subheader("📊 Resumen de Ingresos")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ingreso Efectivo", formatear_moneda(res["ingreso_efectivo"]))
c2.metric("Venta Nequi", formatear_moneda(res["ingresos_nequi"]))
c3.metric("Saldo Nequi", formatear_moneda(res["nequi_total_dia"]))
c4.metric("Efectivo Casa", formatear_moneda(res["efectivo_en_casa"]))
c5.metric("🚀 VENTA TOTAL", formatear_moneda(res["total_venta_dia"]))

st.subheader("📉 Resumen de Gastos")
g1, g2, g3, g4 = st.columns(4)
with g1:
    st.info("**Efectivo Hoy**")
    st.write(f"### {formatear_moneda(res['gasto_hoy'])}")
with g2:
    st.info("**Efectivo Ayer**")
    st.write(f"### {formatear_moneda(res['gasto_ayer'])}")
with g3:
    st.info("**Nequi**")
    st.write(f"### {formatear_moneda(res['gasto_nequi'])}")
with g4:
    st.error("**Total Gastos**")
    st.write(f"### {formatear_moneda(res['total_pagos'])}")

# --- 6. BOTÓN GUARDAR ---
st.divider()
if st.button("✅ GUARDAR CIERRE", use_container_width=True, type="primary"):
    if not responsable:
        st.error("Por favor ingresa el nombre del responsable.")
    else:
        with st.spinner("Guardando en Supabase..."):
            datos = {
                "fecha": str(fecha_cierre),
                "base_caja": res["base_inicial"],
                "ingreso_efectivo": res["ingreso_efectivo"],
                "ingresos_nequi": res["ingresos_nequi"], # Venta real Nequi
                "nequi_total_dia": res["nequi_total_dia"], # Saldo informativo
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
                if pagos_db:
                    guardar_pagos(pagos_db)
            st.success("¡Cierre guardado exitosamente!")
            st.balloons()