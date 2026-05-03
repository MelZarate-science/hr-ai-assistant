import streamlit as st
import json
import asyncio
from app.main import ask_hr
from app.routes import QueryRequest

# Configuración de la página
st.set_page_config(
    page_title="RRHH AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Título y estilo
st.title("🤖 Asistente de RRHH (RAG + Evaluation)")
st.markdown("---")

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

    # Llamada Directa a la Lógica (Sin necesidad de servidor FastAPI externo)
    with st.chat_message("assistant"):
        with st.spinner("Consultando base de conocimientos..."):
            try:
                # Preparamos el request
                request_data = QueryRequest(
                    query=prompt,
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
