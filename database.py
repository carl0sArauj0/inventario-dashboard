import os
from supabase import create_client, Client
import streamlit as st

# Configuración de conexión
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNCIONES PARA INSERTAR DATOS ---

def guardar_cierre(datos_cierre):
    """Guarda el resumen del cierre diario"""
    try:
        response = supabase.table("cierres").insert(datos_cierre).execute()
        return response.data[0]['id'] # Retorna el ID para vincular pagos y desglose
    except Exception as e:
        st.error(f"Error al guardar cierre: {e}")
        return None

def guardar_desglose(desglose):
    """Guarda el detalle de billetes y monedas"""
    try:
        supabase.table("desglose_efectivo").insert(desglose).execute()
    except Exception as e:
        st.error(f"Error al guardar desglose: {e}")

def guardar_pagos(lista_pagos):
    """Guarda la lista de gastos/pagos del día"""
    try:
        if lista_pagos:
            supabase.table("pagos").insert(lista_pagos).execute()
    except Exception as e:
        st.error(f"Error al guardar pagos: {e}")

def obtener_cierre_por_fecha(fecha):
    """Busca si ya existe un cierre para esa fecha"""
    try:
        res = supabase.table("cierres").select("*").eq("fecha", str(fecha)).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        return None

def actualizar_cierre(cierre_id, datos_cierre):
    """Actualiza un registro existente"""
    try:
        supabase.table("cierres").update(datos_cierre).eq("id", cierre_id).execute()
        return True
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False

# --- FUNCIONES PARA CONSULTAR DATOS (Análisis) ---

def obtener_resumen_mensual():
    """Trae datos para el dashboard"""
    try:
        # Traemos los cierres de los últimos 30 días
        response = supabase.table("cierres").select("*").order("fecha", desc=True).limit(30).execute()
        return response.data
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return []