# HR AI Assistant (RAG + Evaluation) 🤖💼

Este es un asistente de Recursos Humanos de nivel profesional que utiliza una arquitectura **RAG (Retrieval-Augmented Generation)** para responder dudas sobre políticas internas, beneficios y programas corporativos basándose exclusivamente en documentación oficial.

## 🚀 Características Principales

- **Arquitectura RAG Avanzada:** Recuperación de documentos desde una base de datos vectorial (**Neon + pgvector**).
- **Conversational Memory (Query Rewriting):** Utiliza un **SLM (Small Language Model)** para reescribir consultas ambiguas basándose en el historial de chat, permitiendo conversaciones fluidas y precisas.
- **Doble Motor de IA:** Implementado con **Groq (Llama 3.3 y 3.1)** para una velocidad de inferencia líder en la industria.
- **Capa de Auditoría Automática:** 
  - **Groundedness:** Verifica que la respuesta no tenga alucinaciones y esté respaldada por los documentos.
  - **Grading:** Califica la relevancia, claridad y utilidad de la respuesta.
- **Guardrails de Seguridad:** Filtro inteligente que asegura que el bot solo responda temas relacionados con RRHH.
- **Interfaz Intuitiva:** Desarrollada con **Streamlit** para una experiencia de usuario limpia y profesional.

## 🏗️ Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** Streamlit
- **Base de Datos:** Neon (PostgreSQL + pgvector)
- **Embeddings:** HuggingFace (`all-MiniLM-L6-v2`)
- **LLMs:** 
  - Generación: Llama 3.3 70B (Groq)
  - Reescritura (SLM): Llama 3.1 8B (Groq)
  - Auditoría: Llama 3.3 70B (Groq)

## 📂 Estructura del Proyecto

```text
├── app/                # API FastAPI y Frontend Streamlit
├── config/             # Configuraciones y variables de entorno
├── core/               # Lógica central (RAG, LLM, Guardrails, Embeddings)
├── data/               # Documentos raw (PDF) y procesados (JSON)
├── evaluation/         # Módulos de auditoría y métricas
├── prompts/            # Prompts del sistema y evaluadores
├── scripts/            # Ingesta de datos y construcción de índice
└── tests/              # Pruebas de integración del pipeline
```

## 🛠️ Instalación y Uso Local

1. **Clonar el repositorio:**
   ```bash
   git clone <tu-repo-url>
   cd "RRHH RAG"
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno:**
   Crea un archivo `.env` con las siguientes claves:
   ```env
   DATABASE_URL=tu_url_de_neon
   GROQ_API_KEY=tu_api_key_de_groq
   LLM_ENGINE=groq
   ENABLE_GUARDRAILS=True
   ENABLE_EVALUATION=True
   ```

4. **Ingesta de datos:**
   ```bash
   python scripts/ingest_data.py
   python scripts/build_index.py
   ```

5. **Ejecutar la aplicación:**
   - Backend: `uvicorn app.main:app --reload`
   - Frontend: `streamlit run app/ui.py`

## 🌐 Despliegue en Streamlit Cloud

Para desplegar este proyecto:
1. Sube el código a GitHub.
2. Conecta tu repositorio en [Streamlit Cloud](https://share.streamlit.io/).
3. Configura los **Secrets** en el panel de Streamlit con las variables de tu `.env`.

---
*Desarrollado como un sistema robusto de IA aplicado a la gestión de talento y comunicación interna.*
