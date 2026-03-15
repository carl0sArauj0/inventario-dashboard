import streamlit as st
import pandas as pd
from groq import Groq
from database import supabase
from logic import formatear_moneda

# Configuración de página
st.set_page_config(page_title="AI Analista - Cafetería", page_icon="🤖", layout="centered")

# --- INICIALIZACIÓN DE LA IA ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODELO = "llama-3.3-70b-versatile" 

# --- BARRA LATERAL (Utilidades) ---
with st.sidebar:
    st.title("⚙️ Configuración")
    if st.button("🗑️ Vaciar historial de chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.info("Al vaciar el chat, la IA olvidará los mensajes anteriores pero seguirá teniendo acceso a los datos más recientes del negocio.")

# --- FUNCIÓN PARA OBTENER CONTEXTO ---
def obtener_resumen_negocio():
    try:
        cierres_res = supabase.table("cierres").select("*").order("fecha", desc=True).limit(10).execute()
        cierres = cierres_res.data
        deudas_res = supabase.table("deudas").select("*").execute()
        deudas = deudas_res.data
        gastos_res = supabase.table("pagos").select("*").limit(10).execute()
        gastos = gastos_res.data

        resumen = "DATOS REALES DEL NEGOCIO:\n"
        if cierres:
            df_c = pd.DataFrame(cierres)
            resumen += f"- Ventas totales últimos 10 días: {formatear_moneda(df_c['total_venta_dia'].sum())}\n"
            resumen += f"- Ticket promedio: {formatear_moneda(df_c['total_venta_dia'].mean())}\n"
        if deudas:
            df_d = pd.DataFrame(deudas)
            resumen += f"- Fiados pendientes: {formatear_moneda(df_d['monto'].sum())}\n"
        if gastos:
            resumen += f"- Gastos recientes: {', '.join([f'{g.get('concepto')} ({formatear_moneda(g.get('valor'))})' for g in gastos[:5]])}\n"
        return resumen
    except Exception as e:
        return f"Error obteniendo contexto: {e}"

# --- INTERFAZ DE CHAT ---
st.title("🤖 Asistente Inteligente de Negocio")

# Inicializar historial
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del usuario
if prompt := st.chat_input("Pregúntame algo sobre tus ventas o gastos..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        contexto_negocio = obtener_resumen_negocio()
        
        mensajes_ia = [
            {
                "role": "system", 
                "content": f"""Eres un analista financiero experto. 
                DATOS REALES: {contexto_negocio}
                INSTRUCCIONES: Responde breve, profesional, usa $ y puntos de mil."""
            }
        ]
        
        # Mantener contexto de la conversación actual (últimos 5 mensajes)
        for m in st.session_state.messages[-5:]:
            mensajes_ia.append({"role": m["role"], "content": m["content"]})

        try:
            response = client.chat.completions.create(
                model=MODELO,
                messages=mensajes_ia,
                temperature=0.6,
                max_tokens=600
            )
            full_response = response.choices[0].message.content
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error: {e}")