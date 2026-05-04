import streamlit as st
import json
import asyncio
import sys
import os

# Asegurar que el directorio raíz y el directorio 'app' estén en el path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from main import ask_hr
from routes import QueryRequest

# Configuración de la página
st.set_page_config(
    page_title="RRHH AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Título y estilo
st.title("🤖 Asistente de RRHH (RAG + Evaluation)")

st.markdown("""
Bienvenido al prototipo de **Asistente de Inteligencia Artificial para RRHH**. 
Este sistema utiliza técnicas de **RAG (Retrieval-Augmented Generation)** para responder preguntas 
basándose exclusivamente en la documentación interna de la empresa.

---
""")

# Estado de la sesión para el historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar para Evaluación y Metadatos
with st.sidebar:
    st.header("📂 Conocimiento Base")
    st.markdown("""
    Documentos indexados actualmente:
    - 📄 **Política de Vacaciones y Licencias**
    - 📄 **Programa de Beneficios Corporativos**
    - 📄 **Programa de RSE**
    """)
    
    st.markdown("---")
    st.header("📊 Panel de Auditoría")
    st.info("Aquí verás los resultados de la evaluación en tiempo real.")
    
    # Espacio para mostrar la última evaluación
    if "last_eval" in st.session_state:
        eval_data = st.session_state.last_eval
        
        # Groundedness con color
        if eval_data["is_grounded"]:
            st.success("✅ Veracidad (Groundedness): PASS")
        else:
            st.error("❌ Veracidad (Groundedness): FAIL")
            
        st.write("**Puntajes de Calidad (LLM-as-a-Judge):**")
        st.progress(eval_data["grading"]["relevance"] / 5, text=f"Relevancia: {eval_data['grading']['relevance']}")
        st.progress(eval_data["grading"]["clarity"] / 5, text=f"Claridad: {eval_data['grading']['clarity']}")
        st.progress(eval_data["grading"]["usefulness"] / 5, text=f"Utilidad: {eval_data['grading']['usefulness']}")
        
        st.metric("Puntaje Total", f"{eval_data['grading']['total_score']}/5.0")
        
        if eval_data["sources"]:
            st.markdown("**Fuentes consultadas:**")
            for src in eval_data["sources"]:
                st.caption(f"📄 {src}")
    else:
        st.write("Esperando consulta...")

    st.markdown("---")
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.messages = []
        if "last_eval" in st.session_state:
            del st.session_state.last_eval
        st.rerun()

# Sección de preguntas sugeridas
st.subheader("💡 ¿No sabes qué preguntar? Prueba con estas:")
col1, col2, col3 = st.columns(3)

suggestions = [
    "¿Cuántos días de vacaciones tengo si llevo 3 años?",
    "¿Cuáles son los beneficios de salud disponibles?",
    "¿Qué actividades de RSE hace la empresa?"
]

selected_suggestion = None

with col1:
    if st.button(suggestions[0]):
        selected_suggestion = suggestions[0]
with col2:
    if st.button(suggestions[1]):
        selected_suggestion = suggestions[1]
with col3:
    if st.button(suggestions[2]):
        selected_suggestion = suggestions[2]

st.markdown("---")

# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de chat
prompt = st.chat_input("¿En qué puedo ayudarte hoy?")

# Si el usuario selecciona una sugerencia o escribe algo
if selected_suggestion or prompt:
    input_text = selected_suggestion if selected_suggestion else prompt
    
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": input_text})
    with st.chat_message("user"):
        st.markdown(input_text)

    # Llamada Directa a la Lógica
    with st.chat_message("assistant"):
        with st.spinner("Consultando base de conocimientos..."):
            try:
                # Preparamos el request
                request_data = QueryRequest(
                    query=input_text,
                    history=st.session_state.messages[:-1]
                )
                
                # Ejecutamos la lógica (ask_hr es asíncrona)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                data = loop.run_until_complete(ask_hr(request_data))
                
                # Mostrar respuesta
                st.markdown(data.answer)
                
                # Guardar evaluación para el sidebar
                st.session_state.last_eval = {
                    "is_grounded": data.is_grounded,
                    "grading": data.grading.dict(),
                    "sources": data.sources
                }
                
                # Agregar a historial
                st.session_state.messages.append({"role": "assistant", "content": data.answer})
                
                # Forzar recarga del sidebar
                st.rerun()
            except Exception as e:
                st.error(f"Error procesando la consulta: {e}")
