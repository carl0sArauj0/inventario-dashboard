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
    if registro_previo:
        def_in_nequi = float(registro_previo.get('ingresos_nequi') or 0)
        def_tot_nequi = float(registro_previo.get('nequi_total_dia') or 0)
        def_casa = float(registro_previo.get('efectivo_en_casa') or 0)
    else:
        def_in_nequi = 0.0
        def_tot_nequi = 0.0
        def_casa = 0.0
    
    ingresos_nequi = st.number_input("Ingresos Nequi (Venta hoy)", value=def_in_nequi, step=1000.0, key=f"nequi_v_{fecha_cierre}")
    nequi_total_dia = st.number_input("Nequi Total Día (Saldo App)", value=def_tot_nequi, step=1000.0, key=f"nequi_s_{fecha_cierre}")
    efectivo_en_casa = st.number_input("Efectivo en Casa", value=def_casa, step=1000.0, key=f"casa_{fecha_cierre}")

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

with col_deuda:
    st.subheader("📝 Ventas a Crédito (Fiados)")
    # Cargar deudas previas si existen (Para actualización)
    if registro_previo:
        res_d = supabase.table("deudas").select("*").eq("cierre_id", id_existente).execute()
        df_d_previo = pd.DataFrame(res_d.data)[['cliente', 'monto']]
        df_d_previo.columns = ['Quien Debe', 'Monto']
    else:
        df_d_previo = pd.DataFrame(columns=["Quien Debe", "Monto"])
        
    deudas_editadas = st.data_editor(df_d_previo, num_rows="dynamic", use_container_width=True, key=f"d_{fecha_cierre}")


# --- CÁLCULOS Y RESUMEN ---
lista_pagos = pagos_editados.to_dict('records')
lista_deudas = deudas_editadas.to_dict('records')

res = procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas)

# --- RESUMEN ---
st.subheader("📊 Resumen del Día")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Efectivo Hoy", formatear_moneda(res["ingreso_efectivo"]))
m2.metric("Nequi Hoy", formatear_moneda(res["ingresos_nequi"]))
m3.metric("Fiados Hoy", formatear_moneda(res["total_fiado"]))
m4.metric("Saldo Nequi", formatear_moneda(res["nequi_total_dia"]))
m5.metric("Efectivo Casa", formatear_moneda(res["efectivo_en_casa"]))
m6.metric("🚀 VENTA TOTAL", formatear_moneda(res["total_venta_dia"]))

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
        
        if registro_previo:
            supabase.table("deudas").delete().eq("cierre_id", id_existente).execute()
        
        if lista_deudas:
            deudas_db = [{"cierre_id": id_existente, "cliente": d['Quien Debe'], "monto": d['Monto']} 
                     for d in lista_deudas if d.get('Quien Debe') and d.get('Monto')]
        if deudas_db:
            supabase.table("deudas").insert(deudas_db).execute()
            
        # Guardar lista de pagos
        if exito and lista_pagos:
            pagos_db = [{"cierre_id": id_existente, "concepto": p['Concepto'], "valor": p['Valor'], "metodo_pago": p['Metodo']} 
                        for p in lista_pagos if p.get('Concepto') and p.get('Valor')]
            guardar_pagos(pagos_db)
            
        st.success("¡Datos sincronizados correctamente!")
        st.balloons()