import streamlit as st
import pandas as pd
from datetime import date
from logic import BILLETES, MONEDAS, procesar_cierre, formatear_moneda
from database import guardar_cierre, guardar_pagos, obtener_cierre_por_fecha, actualizar_cierre, supabase

st.set_page_config(page_title="Registro/Actualización", page_icon="📝", layout="wide")

# --- LÓGICA DE CARGA DE DATOS ---
if "datos_cargados" not in st.session_state:
    st.session_state.datos_cargados = None

st.title("📝 Registro y Actualización de Cierre")

# 1. Selección de Fecha (Disparador de carga)
col_fecha, col_res = st.columns([1, 2])
with col_fecha:
    fecha_cierre = st.date_input("Selecciona la Fecha", date.today())

# Buscar si ya existe cierre para esa fecha
registro_previo = obtener_cierre_por_fecha(fecha_cierre)

if registro_previo:
    st.warning(f"⚠️ Ya existe un registro para el {fecha_cierre}. Los datos se han cargado para que los actualices.")
    id_existente = registro_previo['id']
else:
    st.info(f"✨ No hay registros para el {fecha_cierre}. Creando nuevo cierre.")
    id_existente = None

# --- FORMULARIO ---
with st.container():
    col_head2, col_head3 = st.columns(2)
    with col_head2:
        # Si existe registro, usamos su valor, si no, vacío
        def_responsable = registro_previo['responsable'] if registro_previo else ""
        responsable = st.text_input("Persona Responsable", value=def_responsable)
    with col_head3:
        def_base = float(registro_previo['base_caja']) if registro_previo else 100000.0
        base_inicial = st.number_input("Base de Caja", value=def_base, step=1000.0)

st.divider()

# 2. EFECTIVO (Billetes y Monedas)
# Nota: Para simplificar la edición, en esta versión el usuario ingresa el total físico 
# contado si está editando, o puede volver a contar.
st.subheader("💰 Conteo de Efectivo")
col_bill, col_mon = st.columns(2)

cant_billetes = []
with col_bill:
    for b in BILLETES:
        # Aquí podrías cargar el desglose si crearas una tabla de desglose, 
        # por ahora el usuario re-ingresa o dejamos los campos limpios.
        cant = st.number_input(f"Billetes de {formatear_moneda(b)}", min_value=0, key=f"b_{b}_{fecha_cierre}")
        cant_billetes.append(cant)

cant_monedas = []
with col_mon:
    for m in MONEDAS:
        cant = st.number_input(f"Monedas de {formatear_moneda(m)}", min_value=0, key=f"m_{m}_{fecha_cierre}")
        cant_monedas.append(cant)

st.divider()

# 3. GESTIÓN DE DINERO (Donde se actualizará el Nequi)
col_in, col_out = st.columns(2)
with col_in:
    st.subheader("📱 Gestión de Dinero (Nequi)")
    # Cargamos valores previos si existen
    def_in_nequi = float(registro_previo['ingresos_nequi']) if registro_previo else 0.0
    def_tot_nequi = float(registro_previo['nequi_total_dia']) if registro_previo else 0.0
    def_casa = float(registro_previo['efectivo_en_casa']) if registro_previo else 0.0
    
    ingresos_nequi = st.number_input("Ingresos Nequi (Venta hoy)", value=def_in_nequi, step=1000.0)
    nequi_total_dia = st.number_input("Nequi Total Día (Saldo App)", value=def_tot_nequi, step=1000.0)
    efectivo_en_casa = st.number_input("Efectivo en Casa", value=def_casa, step=1000.0)

with col_out:
    st.subheader("💸 Gastos / Pagos")
    # Cargar pagos previos si existen
    if registro_previo:
        res_p = supabase.table("pagos").select("*").eq("cierre_id", id_existente).execute()
        df_p_previo = pd.DataFrame(res_p.data)[['concepto', 'valor', 'metodo_pago']]
        df_p_previo.columns = ['Concepto', 'Valor', 'Metodo']
    else:
        df_p_previo = pd.DataFrame(columns=["Concepto", "Valor", "Metodo"])
        
    pagos_editados = st.data_editor(df_p_previo, num_rows="dynamic", use_container_width=True, key=f"editor_{fecha_cierre}")

# --- CÁLCULOS Y RESUMEN ---
st.divider()
lista_pagos = pagos_editados.to_dict('records')
res = procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos)

# Muestra el resumen que ya teníamos...
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ingreso Efectivo", formatear_moneda(res["ingreso_efectivo"]))
c2.metric("Venta Nequi", formatear_moneda(res["ingresos_nequi"]))
c3.metric("Saldo Nequi", formatear_moneda(res["nequi_total_dia"]))
c4.metric("Efectivo Casa", formatear_moneda(res["efectivo_en_casa"]))
c5.metric("🚀 VENTA TOTAL", formatear_moneda(res["total_venta_dia"]))

# --- BOTÓN GUARDAR / ACTUALIZAR ---
st.divider()
label_boton = "🔄 ACTUALIZAR REGISTRO" if registro_previo else "✅ GUARDAR NUEVO CIERRE"

if st.button(label_boton, use_container_width=True, type="primary"):
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
    
    with st.spinner("Procesando..."):
        if registro_previo:
            # ACTUALIZAR
            exito = actualizar_cierre(id_existente, datos)
            # Borramos pagos viejos y subimos los nuevos para evitar duplicados
            supabase.table("pagos").delete().eq("cierre_id", id_existente).execute()
        else:
            # CREAR NUEVO
            id_existente = guardar_cierre(datos)
            exito = True if id_existente else False
            
        # Guardar lista de pagos
        if exito and lista_pagos:
            pagos_db = [{"cierre_id": id_existente, "concepto": p['Concepto'], "valor": p['Valor'], "metodo_pago": p['Metodo']} 
                        for p in lista_pagos if p.get('Concepto') and p.get('Valor')]
            guardar_pagos(pagos_db)
            
        st.success("¡Datos sincronizados correctamente!")
        st.balloons()