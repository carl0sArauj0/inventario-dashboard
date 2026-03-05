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
st.subheader("💰 Conteo de Efectivo (Físico en Caja)")
col_bill, col_mon = st.columns(2)

cant_billetes = []
with col_bill:
    st.write("**Billetes**")
    for b in BILLETES:
        cant = st.number_input(f"Billetes de {formatear_moneda(b)}", min_value=0, step=1, key=f"b_{b}")
        cant_billetes.append(cant)

cant_monedas = []
with col_mon:
    st.write("**Monedas**")
    for m in MONEDAS:
        cant = st.number_input(f"Monedas de {formatear_moneda(m)}", min_value=0, step=1, key=f"m_{m}")
        cant_monedas.append(cant)

st.divider()

# --- SECCIÓN 3: OTROS INGRESOS Y PAGOS ---
col_in, col_out = st.columns(2)

with col_in:
    st.subheader("📱 Ingresos Digitales")
    ingreso_nequi = st.number_input("Total Ingresos Nequi", min_value=0, step=1000)

with col_out:
    st.subheader("💸 Gastos / Pagos del Día")
    st.info("Escribe los pagos realizados (como en el Excel)")
    
    # Editor de tabla interactiva para los pagos
    df_pagos_input = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
    pagos_editados = st.data_editor(
        df_pagos_input, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Metodo": st.column_config.SelectboxColumn(
                options=["Efectivo", "Nequi"],
                default="Efectivo"
            ),
            "Valor": st.column_config.NumberColumn(format="$ %d")
        }
    )

# --- SECCIÓN 4: CÁLCULOS EN TIEMPO REAL ---
st.divider()
lista_pagos = pagos_editados.to_dict('records')

# Ejecutar lógica matemática
resultados = procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingreso_nequi, lista_pagos)
res = resultados["resumen"]

st.subheader("📊 Resumen del Cierre")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Efectivo Contado", formatear_moneda(res["efectivo_contado"]))
c2.metric("Ingreso Real Efectivo", formatear_moneda(res["ingreso_efectivo"]), help="Efectivo contado menos la base")
c3.metric("Ingreso Nequi", formatear_moneda(res["ingreso_nequi"]))
c4.metric("VENTA TOTAL DEL DÍA", formatear_moneda(res["total_venta_dia"]), delta_color="normal")

# --- BOTÓN DE GUARDAR ---
if st.button("✅ GUARDAR CIERRE DE CAJA", use_container_width=True, type="primary"):
    if not responsable:
        st.error("Por favor ingresa el nombre del responsable.")
    else:
        with st.spinner("Guardando en base de datos..."):
            datos_cierre = {
                "fecha": str(fecha_cierre),
                "base_caja": res["base_inicial"],
                "ingreso_efectivo": res["ingreso_efectivo"],
                "ingreso_nequi": res["ingreso_nequi"],
                "total_venta_dia": res["total_venta_dia"],
                "responsable": responsable
            }
            
            cierre_id = guardar_cierre(datos_cierre)
            
            if cierre_id:
                if lista_pagos:
                    pagos_formateados = []
                    for p in lista_pagos:
                        # Solo guardar si tiene concepto y valor
                        if p.get('Concepto') and p.get('Valor'):
                            pagos_formateados.append({
                                "cierre_id": cierre_id,
                                "concepto": p['Concepto'],
                                "valor": p['Valor'],
                                "metodo_pago": p['Metodo']
                            })
                    if pagos_formateados:
                        guardar_pagos(pagos_formateados)
                
                st.success(f"¡Cierre del {fecha_cierre} guardado exitosamente!")
                st.balloons()