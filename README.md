# HR AI Assistant (RAG + Audit Architecture) 🤖💼

> **Enterprise-grade RAG system for HR Knowledge Management.**
>
> Este proyecto es un asistente de Recursos Humanos diseñado bajo una arquitectura de **Generación Aumentada por Recuperación (RAG)** de nivel profesional. No es solo un chatbot; es un sistema auditable que implementa ciclos de validación, reescritura de consultas y una capa de auditoría automática para garantizar respuestas veraces y seguras.

---

## 🏗️ Arquitectura del Sistema (Deep Dive)

El sistema implementa un pipeline modular diseñado para resolver los problemas comunes de las implementaciones RAG básicas (alucinaciones, falta de contexto conversacional y ruido semántico).

### 1. Ingesta y Estrategia de Datos (ETL)
*   **Markdown-Aware Extraction:** Transformamos PDFs corporativos en texto con formato Markdown. Esto permite inyectar jerarquía estructural (títulos, listas, secciones) en el contexto, lo que ayuda al LLM a entender la relevancia de las reglas de RRHH según su nivel jerárquico.
*   **Chunking Metodológico:** Utilizamos `RecursiveCharacterTextSplitter` con un tamaño de fragmento de **1500 caracteres** y un solapamiento (overlap) del 10%. Esta configuración fue calibrada para mantener la cohesión de las políticas de beneficios sin fragmentar unidades lógicas de información.
*   **Normalización:** El proceso de ingesta genera un paso intermedio en JSON para validación técnica antes de la indexación vectorial.

### 2. El "Mini-Cerebro" (Query Rewriting con SLM)
Para resolver la "amnesia" conversacional y las referencias ambiguas (ej: "¿Y cuánto para el de 5 años?"), implementamos un **SLM (Small Language Model)** encargado exclusivamente de reescribir la consulta.
*   **Lógica:** Toma el historial reciente + la pregunta actual ➔ Genera una consulta independiente optimizada para búsqueda vectorial.
*   **Eficiencia:** Usamos **Llama 3.1 8B** (vía Groq) para esta tarea, reduciendo la latencia y el costo operativo en un 60% comparado con modelos 70B.

### 3. Recuperación Vectorial (Neon + pgvector)
*   **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (HuggingFace), optimizado para entender semántica en español.
*   **Búsqueda Semántica:** Implementada sobre **Neon** mediante la extensión `pgvector` usando **distancia de coseno (`<=>`)**.
*   **Threshold Optimizado (0.35):** Calibrado para filtrar ruido y asegurar que solo información altamente relevante llegue al motor de generación.

### 4. Ciclo de Veracidad y Reparación (Repair Loop)
Una de las características más avanzadas del proyecto es su capacidad de **auto-corrección**:
1.  **Generación Inicial:** El LLM redacta una respuesta basada en el contexto.
2.  **Validación de Veracidad:** Un auditor interno (LLM-as-a-judge) verifica si hay alucinaciones.
3.  **Reparación:** Si se detecta un fallo de veracidad, el **RepairManager** toma la respuesta fallida y el contexto original para redactar una versión corregida.
4.  **Refusal Fallback:** Si la reparación falla dos veces, el sistema prefiere admitir ignorancia antes que alucinar.

---

## 🛠️ Tech Stack & Herramientas

*   **LLM Engine:** Groq (Llama 3.3 70B para razonamiento complejo).
*   **SLM Engine:** Groq (Llama 3.1 8B para tareas mecánicas).
*   **Vector Database:** Neon (PostgreSQL + pgvector).
*   **API Framework:** FastAPI (Backend modular y tipado).
*   **UI Framework:** Streamlit (Panel de control con métricas de auditoría).
*   **Embeddings:** Sentence-Transformers (Local/HF).
*   **Seguridad:** GuardrailManager personalizado para filtrado de ámbito (RRHH-only).

---

## 📂 Estructura del Proyecto

```text
├── app/
│   ├── main.py         # Orquestador del pipeline (API)
│   ├── routes.py       # Contratos de datos (Pydantic)
│   └── ui.py           # Interfaz de usuario y visualización de auditoría
├── core/
│   ├── embeddings.py   # Gestión de vectores de HuggingFace
│   ├── guardrails.py   # Clasificación de seguridad y ámbito
│   ├── llm.py          # Interfaz agnóstica para Groq/Gemini
│   └── repair.py       # Lógica de auto-corrección de alucinaciones
├── evaluation/
│   └── eval_runner.py  # Sistema de auditoría (Groundedness & Grading)
├── scripts/
│   ├── ingest_data.py  # Pipeline de ETL y limpieza de documentos
│   └── build_index.py  # Indexación masiva en Neon
└── prompts/            # Prompts del sistema versionados
```

---

## 📊 Capa de Auditoría y Evaluación
El asistente incluye un panel lateral que muestra en tiempo real:
- **Groundedness Score:** Porcentaje de veracidad basado en evidencia documental.
- **Calidad (Grading):** Métricas de Relevancia, Claridad y Utilidad (1-5).
- **Diagnóstico de Recuperación:** Visualización técnica de los puntajes de similitud obtenidos de la base de datos.

---

## 🚀 Guía de Instalación y Despliegue

### Requisitos Previos
- Python 3.10+
- Instancia de Neon (Postgres) con extensión `vector`.
- API Key de Groq.

### Pasos de Arranque
1.  **Clonar y configurar:**
    ```bash
    git clone <url-del-repo>
    cd "RRHH RAG"
    python -m venv .venv
    source .venv/bin/activate  # o .venv\Scripts\activate en Windows
    pip install -r requirements.txt
    ```

2.  **Configurar el entorno:**
    Crea un archivo `.env` con las credenciales de Base de Datos y API Keys (Ver `.env.example`).

3.  **Ingesta de Conocimiento (ETL):**
    ```bash
    python scripts/ingest_data.py   # Procesa los PDFs en data/raw/
    python scripts/build_index.py   # Genera vectores y sube a la DB
    ```

4.  **Lanzamiento:**
    ```bash
    uvicorn app.main:app --reload   # Inicia el backend
    streamlit run app/ui.py         # Inicia la interfaz
    ```

---

## 💡 Nota Metodológica (Para Recrutadores IT)
Este proyecto demuestra el dominio de conceptos críticos en IA moderna:
- **Separation of Concerns:** Desacoplamiento de la lógica de recuperación, generación y auditoría.
- **Cost & Latency Optimization:** Uso inteligente de SLMs para tareas de baja complejidad.
- **Defensive Prompting:** Instrucciones diseñadas para evitar fugas de contexto y alucinaciones.
- **Data Engineering:** Pipeline de ETL robusto con pasos intermedios de validación.

---
*Desarrollado como una solución de IA confiable, transparente y auditable para entornos corporativos de alta demanda.*
