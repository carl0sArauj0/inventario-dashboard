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

# --- BARRA LATERAL (Configuración) ---
with st.sidebar:
    st.title("⚙️ Opciones")
    if st.button("🗑️ Vaciar historial de chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("El asistente analiza las ventas, gastos y deudas de los últimos registros guardados en la base de datos.")

# --- FUNCIÓN PARA OBTENER CONTEXTO REAL ---
def obtener_resumen_negocio():
    try:
        # Traer datos clave de Supabase
        cierres_res = supabase.table("cierres").select("*").order("fecha", desc=True).limit(15).execute()
        cierres = cierres_res.data
        deudas_res = supabase.table("deudas").select("*").execute()
        deudas = deudas_res.data
        gastos_res = supabase.table("pagos").select("*").limit(15).execute()
        gastos = gastos_res.data

        resumen = "DATOS DEL NEGOCIO (Últimos registros):\n"
        if cierres:
            df_c = pd.DataFrame(cierres)
            resumen += f"- Ventas totales (periodo actual): {formatear_moneda(df_c['total_venta_dia'].sum())}\n"
            resumen += f"- Ticket promedio diario: {formatear_moneda(df_c['total_venta_dia'].mean())}\n"
            resumen += f"- Venta más alta registrada: {formatear_moneda(df_c['total_venta_dia'].max())}\n"
        
        if deudas:
            df_d = pd.DataFrame(deudas)
            resumen += f"- Total por cobrar (Fiados): {formatear_moneda(df_d['monto'].sum())}\n"
            # Top 3 deudores
            top_deudores = df_d.groupby('cliente')['monto'].sum().nlargest(3)
            resumen += f"- Principales deudores: {', '.join([f'{c} ({formatear_moneda(m)})' for c, m in top_deudores.items()])}\n"
            
        if gastos:
            df_g = pd.DataFrame(gastos)
            resumen += f"- Gastos recientes: {', '.join([f'{g.get('concepto')} ({formatear_moneda(g.get('valor'))})' for g in gastos[:5]])}\n"
        
        return resumen
    except Exception as e:
        return f"Error obteniendo datos: {e}"

# --- INTERFAZ DE CHAT ---
st.title("🤖 Asistente Inteligente de Negocio")

# Inicializar historial
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mensaje de Bienvenida y Recomendaciones (Solo si el chat está vacío)
if not st.session_state.messages:
    st.info("""
    👋 **¡Hola! Soy tu analista financiero.** He leído tus datos actuales de Supabase y estoy listo para ayudarte.
    
    **Puedes preguntarme cosas como:**
    * 📊 *¿Cómo van mis ventas comparadas con los gastos de la última semana?*
    * 💸 *¿Quiénes son los clientes que más dinero me deben y cuánto es el total?*
    * 💡 *Dame 3 consejos para mejorar mi utilidad basados en mis gastos actuales.*
    * 📈 *¿Cuál ha sido la tendencia de mis ventas en Nequi frente al efectivo?*
    """)

# Mostrar historial de la conversación
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del usuario
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Guardar y mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generar respuesta de la IA
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # 1. Obtenemos el contexto fresco de la DB en cada pregunta
        contexto_real = obtener_resumen_negocio()
        
        mensajes_ia = [
            {
                "role": "system", 
                "content": f"""Eres un consultor de negocios experto en cafeterías. 
                Tu misión es analizar los datos que se te proporcionan y dar respuestas útiles, estratégicas y amables.
                DATOS REALES DEL NEGOCIO:
                {contexto_real}
                INSTRUCCIONES:
                - Usa siempre el signo $ y puntos de mil para los montos.
                - Responde de forma concisa (máximo 2 párrafos).
                - Si te preguntan por deudas, menciona nombres específicos si están en los datos.
                - Si los gastos son muy altos respecto a las ventas, advierte al dueño."""
            }
        ]
        
        # Agregamos los últimos mensajes de la conversación para tener memoria
        for m in st.session_state.messages[-6:]:
            mensajes_ia.append({"role": m["role"], "content": m["content"]})

        try:
            # Llamada a Groq
            response = client.chat.completions.create(
                model=MODELO,
                messages=mensajes_ia,
                temperature=0.5, # Menor temperatura para respuestas más precisas numéricamente
                max_tokens=800
            )
            full_response = response.choices[0].message.content
            message_placeholder.markdown(full_response)
            
            # Guardar respuesta en el historial
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error en el motor de IA: {e}")