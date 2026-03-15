import streamlit as st
import pandas as pd
from groq import Groq
from database import supabase
from logic import formatear_moneda

# Configuración de página
st.set_page_config(page_title="AI Analista - Cafetería", page_icon="🤖", layout="centered")

# --- INICIALIZACIÓN DE LA IA ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODELO = "llama-3.1-70b-versatile"

# --- FUNCIÓN PARA OBTENER DATOS REALES (Contexto) ---
def obtener_resumen_negocio():
    """Extrae datos de Supabase y los convierte en un resumen textual para la IA"""
    # 1. Traer últimos cierres
    cierres = supabase.table("cierres").select("*").order("fecha", desc=True).limit(10).execute().data
    # 2. Traer deudas pendientes
    deudas = supabase.table("deudas").select("*").execute().data
    # 3. Traer gastos recientes
    gastos = supabase.table("pagos").select("*").limit(10).execute().data

    # Convertimos los datos en un formato que la IA entienda bien
    resumen = "DATOS ACTUALES DEL NEGOCIO:\n"
    
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
        df_g = pd.DataFrame(gastos)
        resumen += f"- Últimos gastos: {', '.join([f'{g['concepto']} ({formatear_moneda(g['valor'])})' for g in gastos[:5]])}\n"

    return resumen

# --- INTERFAZ DE CHAT ---
st.title("🤖 Asistente Inteligente de Negocio")
st.markdown("""
Esta IA tiene acceso a tus datos de inventario y ventas. Puedes preguntarle cosas como:
* *¿Cómo van mis ventas comparadas con los gastos?*
* *¿A qué clientes debo cobrarles hoy?*
* *Dame 3 consejos para mejorar mi utilidad este mes.*
""")

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del usuario
if prompt := st.chat_input("Escribe tu pregunta sobre el negocio..."):
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generar respuesta de la IA
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # 1. Obtener contexto fresco de la base de datos
        contexto_negocio = obtener_resumen_negocio()
        
        # 2. Preparar los mensajes para Groq
        mensajes_ia = [
            {
                "role": "system", 
                "content": f"""Eres un analista financiero experto en cafeterías. 
                Tu objetivo es ayudar al dueño a tomar decisiones basadas en datos.
                Aquí tienes el resumen real de la cafetería hoy:
                {contexto_negocio}
                Responde de forma profesional, amable y muy breve. Usa el signo $ y puntos de miles."""
            }
        ]
        
        # Añadimos el historial previo (últimos 4 mensajes para no saturar)
        for m in st.session_state.messages[-4:]:
            mensajes_ia.append({"role": m["role"], "content": m["content"]})

        try:
            # 3. Llamada a Groq
            response = client.chat.completions.create(
                model=MODELO,
                messages=mensajes_ia,
                temperature=0.7, # Creatividad balanceada
                max_tokens=500
            )
            full_response = response.choices[0].message.content
            message_placeholder.markdown(full_response)
            
            # Guardar en historial
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Hubo un error con la IA: {e}")