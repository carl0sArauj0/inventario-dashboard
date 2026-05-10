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

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Opciones")
    if st.button("🗑️ Vaciar historial de chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- MEJORA DEL EXTRACTOR DE DATOS (Más específico para Nequi/Efectivo) ---
def obtener_resumen_negocio():
    try:
        cierres_res = supabase.table("cierres").select("*").order("fecha", desc=True).limit(30).execute()
        df_c = pd.DataFrame(cierres_res.data)
        
        deudas_res = supabase.table("deudas").select("*").execute()
        df_d = pd.DataFrame(deudas_res.data)

        resumen = "DATOS ACTUALES DEL NEGOCIO (Últimos 30 días):\n"
        if not df_c.empty:
            total_v = df_c['total_venta_dia'].sum()
            total_n = df_c['ingresos_nequi'].sum()
            total_e = df_c['ingreso_efectivo'].sum()
            resumen += f"- Venta Total: {formatear_moneda(total_v)}\n"
            resumen += f"- Ventas por NEQUI: {formatear_moneda(total_n)}\n"
            resumen += f"- Ventas por EFECTIVO: {formatear_moneda(total_e)}\n"
            resumen += f"- Ticket promedio: {formatear_moneda(df_c['total_venta_dia'].mean())}\n"
        
        if not df_d.empty:
            resumen += f"- Total en Fiados: {formatear_moneda(df_d['monto'].sum())}\n"
        
        return resumen
    except Exception as e:
        return f"Error obteniendo datos: {e}"

# --- INTERFAZ DE CHAT ---
st.title("🤖 Asistente Inteligente de Negocio")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mensaje de Bienvenida corregido
if not st.session_state.messages:
    st.info("""
    👋 **¡Hola! Soy tu analista financiero.** 
    He analizado tus ventas (Efectivo y Nequi), gastos y deudas.
    
    **Preguntas recomendadas:**
    * 📱 *¿Cuánto he vendido por Nequi en total?*
    * 💰 *¿Cuál es el balance entre efectivo y Nequi este mes?*
    * 📉 *¿Mis gastos están superando mis ingresos?*
    """)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        contexto_real = obtener_resumen_negocio()
        
        mensajes_ia = [
            {
                "role": "system", 
                "content": f"""Eres un analista financiero de alto nivel.
                
                DATOS REALES DEL NEGOCIO:
                {contexto_real}
                
                REGLAS CRÍTICAS DE FORMATO:
                1. NUNCA uses comillas invertidas (backticks) ni bloques de código para mostrar números o texto.
                2. Escribe de forma totalmente plana, sin cuadros verdes ni fondos grises.
                3. Usa negrita (**) solo para resaltar nombres o totales importantes.
                4. Usa siempre el signo $ y puntos de mil.
                5. Responde de forma ejecutiva y directa."""
            }
        ]
        
        for m in st.session_state.messages[-6:]:
            mensajes_ia.append({"role": m["role"], "content": m["content"]})

        try:
            response = client.chat.completions.create(
                model=MODELO,
                messages=mensajes_ia,
                temperature=0.3, # Bajamos la temperatura para que sea menos "creativo" con el formato
                max_tokens=800
            )
            full_response = response.choices[0].message.content
            
            # Limpieza extra de seguridad por si la IA ignora el prompt
            full_response = full_response.replace('`', '') 
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error: {e}")