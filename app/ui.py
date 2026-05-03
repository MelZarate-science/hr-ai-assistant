import streamlit as st
import requests
import json

# Configuración de la página
st.set_page_config(
    page_title="RRHH AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Título y estilo
st.title("🤖 Asistente de RRHH (RAG + Evaluation)")
st.markdown("---")

# URL del API de FastAPI
API_URL = "http://127.0.0.1:8000/ask"

# Estado de la sesión para el historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar para Evaluación y Metadatos
with st.sidebar:
    st.header("📊 Panel de Auditoría")
    st.info("Aquí verás los resultados de la evaluación en tiempo real.")
    
    # Espacio para mostrar la última evaluación
    if "last_eval" in st.session_state:
        eval_data = st.session_state.last_eval
        
        # Groundedness con color
        if eval_data["is_grounded"]:
            st.success("✅ Veracidad: PASS")
        else:
            st.error("❌ Veracidad: FAIL")
            
        st.write("**Puntajes de Calidad:**")
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

# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de chat
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Llamada al API
    with st.chat_message("assistant"):
        with st.spinner("Consultando base de conocimientos..."):
            try:
                # Enviamos la pregunta y el historial para el "Mini-cerebro"
                payload = {
                    "query": prompt,
                    "history": st.session_state.messages[:-1] # Excluimos el último mensaje que acabamos de agregar
                }
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Mostrar respuesta
                    st.markdown(data["answer"])
                    
                    # Guardar evaluación para el sidebar
                    st.session_state.last_eval = {
                        "is_grounded": data["is_grounded"],
                        "grading": data["grading"],
                        "sources": data["sources"]
                    }
                    
                    # Agregar a historial
                    st.session_state.messages.append({"role": "assistant", "content": data["answer"]})
                    
                    # Forzar recarga del sidebar
                    st.rerun()
                else:
                    st.error(f"Error del servidor: {response.text}")
            except Exception as e:
                st.error(f"No se pudo conectar con el API: {e}")
