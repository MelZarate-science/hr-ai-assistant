import streamlit as st
import json
import asyncio
import sys
import os
from pathlib import Path

# Absolute Path Setup
sys.path.append(os.getcwd())

from app.main import ask_hr
from app.routes import QueryRequest

# --- UI CONFIGURATION ---
st.set_page_config(
    page_title="Asistente IA de RRHH",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished look
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .source-tag { 
        background-color: #e1e4e8; 
        color: #0366d6; 
        padding: 2px 8px; 
        border-radius: 5px; 
        font-size: 0.8em; 
        font-weight: bold;
        margin-right: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing" not in st.session_state:
    st.session_state.processing = False
if "last_eval" in st.session_state and not isinstance(st.session_state.last_eval, dict):
    # Fix for legacy data
    st.session_state.last_eval = None

# --- SIDEBAR: KNOWLEDGE & AUDIT ---
with st.sidebar:
    st.title("📂 Centro de Control")
    
    tab1, tab2 = st.tabs(["Auditoría", "Documentos"])
    
    with tab1:
        if "last_eval" in st.session_state and st.session_state.last_eval:
            e = st.session_state.last_eval
            st.subheader("🔍 Verificación en Tiempo Real")
            
            # Groundedness Metric
            score = e.get("score", 0.0)
            status_color = "green" if score > 0.8 else "orange" if score > 0.5 else "red"
            st.markdown(f"**Nivel de Veracidad:** <span style='color:{status_color}'>{score*100:.0f}%</span>", unsafe_allow_html=True)
            st.progress(score)
            
            if e.get("is_repaired"):
                st.warning("🔧 Respuesta auto-corregida para mayor precisión.")
            
            st.markdown("---")
            st.write("**Calidad de Respuesta (1-5):**")
            c = st.columns(3)
            c[0].metric("Relevancia", e['grading']['relevance'])
            c[1].metric("Claridad", e['grading']['clarity'])
            c[2].metric("Utilidad", e['grading']['usefulness'])
            
            with st.expander("📝 Razonamiento de Auditoría"):
                st.write(e.get("reasoning", "Sin detalles adicionales."))
        else:
            st.info("Realiza una pregunta para ver el análisis de veracidad.")

    with tab2:
        st.subheader("📄 Documentación Indexada")
        st.caption("Haz clic para verificar el contenido base.")
        
        doc_files = {
            "Política de Vacaciones": "data/raw/hr_docs_extended/POLITICA_VACACIONES_V2.txt",
            "Programa de Beneficios": "data/raw/hr_docs_extended/PROGRAMA_BENEFICIOS_V2.txt",
            "Programa de RSE": "data/raw/hr_docs_extended/PROGRAMA_RSE_V2.txt"
        }
        
        for name, path in doc_files.items():
            if st.button(f"👁️ Ver {name}", key=path):
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        st.session_state.viewing_doc = (name, f.read())
                else:
                    st.error("Archivo no encontrado.")

    if st.button("🗑️ Limpiar Conversación", use_container_width=True):
        st.session_state.messages = []
        if "last_eval" in st.session_state: del st.session_state.last_eval
        st.rerun()

# --- MAIN INTERFACE ---
st.title("🤖 Asistente de RRHH Inteligente")
st.caption("Consultas basadas en políticas oficiales de la empresa")

# Document Viewer Modal (Simulated)
if "viewing_doc" in st.session_state:
    with st.expander(f"📖 Previsualización: {st.session_state.viewing_doc[0]}", expanded=True):
        st.text_area("Contenido del documento", st.session_state.viewing_doc[1], height=300)
        if st.button("Cerrar Vista"):
            del st.session_state.viewing_doc
            st.rerun()

# Suggestions (Interactive Tiles)
if not st.session_state.messages:
    st.subheader("🚀 Comienza con una pregunta sugerida:")
    suggestions = [
        "¿Cuántos días de vacaciones me corresponden?",
        "¿Cuáles son los beneficios de salud y gimnasio?",
        "¿A qué programas de RSE puedo sumarme?"
    ]
    cols = st.columns(len(suggestions))
    for i, s in enumerate(suggestions):
        if cols[i].button(s, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": s})
            st.session_state.active_prompt = s

# Thread Rendering
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- CHAT CONTROLLER ---
user_input = st.chat_input("Escribe tu consulta aquí...", disabled=st.session_state.processing)

# Logic to trigger processing
final_query = None
if user_input:
    final_query = user_input
    st.session_state.messages.append({"role": "user", "content": final_query})
    st.rerun() # Refresh to show user message and disable input

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and not st.session_state.processing:
    final_query = st.session_state.messages[-1]["content"]
    
    with st.chat_message("assistant"):
        st.session_state.processing = True
        # Mensajes amigables en español
        status_placeholder = st.empty()
        status_placeholder.status("🔍 Consultando políticas oficiales...", expanded=True)
        
        try:
            # Event Loop Bridge
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            request = QueryRequest(query=final_query, history=st.session_state.messages[:-1])
            
            # Step 1: Processing
            data = loop.run_until_complete(ask_hr(request))
            
            # Step 2: Show result
            status_placeholder.empty()
            st.markdown(data.answer)
            
            # Step 3: Show Sources found as tags
            if data.sources:
                st.markdown(" ".join([f"<span class='source-tag'>{s}</span>" for s in data.sources]), unsafe_allow_html=True)
            
            # Update Audit State
            st.session_state.last_eval = {
                "score": data.groundedness_score,
                "is_grounded": data.is_grounded,
                "is_repaired": data.is_repaired,
                "grading": data.grading.model_dump(),
                "sources": data.sources,
                "reasoning": data.reasoning
            }
            
            st.session_state.messages.append({"role": "assistant", "content": data.answer})
            
        except Exception as ex:
            st.error(f"Hubo un problema técnico al procesar tu consulta. Por favor, intenta de nuevo.")
            print(f"DEBUG Error: {ex}")
        finally:
            st.session_state.processing = False
            loop.close()
            st.rerun()
