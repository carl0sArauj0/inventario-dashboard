import streamlit as st
import pandas as pd
from groq import Groq
from database import supabase
from logic import formatear_moneda

# Configuración de página
st.set_page_config(page_title="AI Analista - Cafetería", page_icon="🤖", layout="centered")

# --- INICIALIZACIÓN DE LA IA ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# CAMBIO AQUÍ: Usamos el modelo más reciente y estable de Groq
MODELO = "llama-3.3-70b-versatile" 

# --- FUNCIÓN PARA OBTENER DATOS REALES (Contexto) ---
def obtener_resumen_negocio():
    """Extrae datos de Supabase y los convierte en un resumen textual para la IA"""
    try:
        # 1. Traer últimos cierres
        cierres_res = supabase.table("cierres").select("*").order("fecha", desc=True).limit(10).execute()
        cierres = cierres_res.data
        
        # 2. Traer deudas pendientes
        deudas_res = supabase.table("deudas").select("*").execute()
        deudas = deudas_res.data
        
        # 3. Traer gastos recientes
        gastos_res = supabase.table("pagos").select("*").limit(10).execute()
        gastos = gastos_res.data

        resumen = "DATOS REALES DEL NEGOCIO:\n"
        
        if cierres:
            df_c = pd.DataFrame(cierres)
            resumen += f"- Ventas totales últimos 10 días: {formatear_moneda(df_c['total_venta_dia'].sum())}\n"
            resumen += f"- Ticket promedio de venta: {formatear_moneda(df_c['total_venta_dia'].mean())}\n"
            resumen += f"- Última venta registrada ({df_c.iloc[0]['fecha']}): {formatear_moneda(df_c.iloc[0]['total_venta_dia'])}\n"
        
        if deudas:
            df_d = pd.DataFrame(deudas)
            resumen += f"- Total dinero en fiados (por cobrar): {formatear_moneda(df_d['monto'].sum())}\n"
            resumen += f"- Clientes que más deben: {', '.join(df_d.nlargest(3, 'monto')['cliente'].tolist())}\n"

        if gastos:
            resumen += f"- Últimos gastos: {', '.join([f'{g.get('concepto')} ({formatear_moneda(g.get('valor'))})' for g in gastos[:5]])}\n"

        return resumen
    except Exception as e:
        return f"Error obteniendo contexto: {e}"

# --- INTERFAZ DE CHAT ---
st.title("🤖 Asistente Inteligente de Negocio")
st.caption(f"Utilizando el modelo: {MODELO}")

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del usuario
if prompt := st.chat_input("Escribe tu pregunta sobre el negocio..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Obtener contexto fresco
        contexto_negocio = obtener_resumen_negocio()
        
        mensajes_ia = [
            {
                "role": "system", 
                "content": f"""Eres un analista financiero experto en cafeterías. 
                Tu objetivo es ayudar al dueño a tomar decisiones basadas en datos reales.
                CONTEXTO DEL NEGOCIO:
                {contexto_negocio}
                INSTRUCCIONES:
                - Responde de forma profesional pero cercana.
                - Sé MUY BREVE y directo.
                - Usa $ y puntos de miles.
                - Si el usuario te pregunta algo que no está en los datos, dilo con honestidad."""
            }
        ]
        
        for m in st.session_state.messages[-4:]:
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
            st.error(f"Hubo un error con la IA: {e}")