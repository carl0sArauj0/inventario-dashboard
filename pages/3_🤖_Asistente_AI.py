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

# --- EXTRACTOR DE DATOS ---
def obtener_resumen_negocio():
    try:
        # 1. Traer TODOS los cierres para análisis histórico
        cierres_res = supabase.table("cierres").select("*").order("fecha", desc=False).execute()
        df_c = pd.DataFrame(cierres_res.data)
        
        if df_c.empty:
            return "No hay datos registrados aún."

        df_c['fecha'] = pd.to_datetime(df_c['fecha'])
        df_c['mes_nombre'] = df_c['fecha'].dt.strftime('%B %Y')
        
        # 2. Agrupación por Mes (Análisis de largo plazo)
        resumen_mensual = df_c.groupby(df_c['fecha'].dt.to_period('M')).agg({
            'total_venta_dia': 'sum',
            'ingresos_nequi': 'sum',
            'ingreso_efectivo': 'sum'
        }).reset_index()
        
        # 3. Datos para el contexto de la IA
        fecha_inicio = df_c['fecha'].min().strftime('%d de %B de %Y')
        total_historico = df_c['total_venta_dia'].sum()
        promedio_historico = df_c['total_venta_dia'].mean()
        
        # Construir el texto de contexto
        resumen = f"HISTORIAL COMPLETO DESDE: {fecha_inicio}\n"
        resumen += f"- Venta Total Acumulada: {formatear_moneda(total_historico)}\n"
        resumen += f"- Venta Promedio Diaria Histórica: {formatear_moneda(promedio_historico)}\n\n"
        
        resumen += "RESUMEN POR MESES:\n"
        for _, row in resumen_mensual.iterrows():
            resumen += f"* {row['fecha']}: Total {formatear_moneda(row['total_venta_dia'])} (Nequi: {formatear_moneda(row['ingresos_nequi'])})\n"
        
        resumen += "\nÚLTIMOS 7 DÍAS (Detalle):\n"
        ultimos_7 = df_c.tail(7)
        for _, row in ultimos_7.iterrows():
            resumen += f"* {row['fecha'].strftime('%Y-%m-%d')}: {formatear_moneda(row['total_venta_dia'])}\n"

        # 4. Deudas actuales
        deudas_res = supabase.table("deudas").select("monto").execute()
        total_deudas = sum(d['monto'] for d in deudas_res.data)
        resumen += f"\n- Deudas Pendientes por Cobrar: {formatear_moneda(total_deudas)}\n"

        return resumen
    except Exception as e:
        return f"Error procesando datos históricos: {e}"

# --- INTERFAZ DE CHAT ---
st.title("🤖 Asistente Inteligente de Negocio")

if "messages" not in st.session_state:
    st.session_state.messages = []


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
                "content": f"""Eres un analista financiero experto. 
                
                DATOS REALES DEL NEGOCIO:
                {contexto_real}
                
                REGLAS OBLIGATORIAS DE FORMATO:
                1. Usa texto plano y sencillo. NUNCA uses formato LaTeX, ecuaciones matemáticas ni notación científica.
                2. NUNCA pongas espacios entre las letras de una palabra (ejemplo: NO escribas 'V e n t a').
                3. Usa negrita simple ** solo para resaltar el nombre de un dato y su valor.
                4. CADA vez que menciones un valor de dinero, pon el signo $ adelante (ejemplo: $500.000).
                5. No uses comillas invertidas (backticks).
                6. Responde de forma directa, como si hablaras por WhatsApp con el dueño."""
            }
        ]
        
        for m in st.session_state.messages[-6:]:
            mensajes_ia.append({"role": m["role"], "content": m["content"]})

        try:
            response = client.chat.completions.create(
                model=MODELO,
                messages=mensajes_ia,
                temperature=0.2, 
                max_tokens=800
            )
            full_response = response.choices[0].message.content
            
            # --- LIMPIEZA DE SEGURIDAD ---
            full_response = full_response.replace('`', '') # Quita código verde
            full_response = full_response.replace('* *', '**') 
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error: {e}")