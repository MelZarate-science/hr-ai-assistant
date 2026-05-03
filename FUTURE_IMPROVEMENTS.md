# 🚀 Hoja de Ruta: Mejoras Futuras (Backlog de Ingeniería)

Este documento detalla las ideas y estrategias para llevar el Asistente de RRHH al siguiente nivel de sofisticación y usabilidad.

## 🎨 1. Experiencia de Usuario (UI/UX)
- **Streaming de Respuestas:** Implementar el efecto de escritura en tiempo real (palabra por palabra) para mejorar la percepción de velocidad.
- **Branding Personalizado:** Inyectar CSS personalizado en Streamlit para alinear la paleta de colores con una identidad corporativa.
- **Botón de Reset:** Añadir una opción para limpiar el `session_state` y reiniciar la conversación desde cero.
- **Carga de Archivos Dinámica:** Permitir que un administrador suba nuevos PDFs directamente desde la interfaz y se indexen automáticamente.

## 🧠 2. Optimización del Motor RAG (Inteligencia)
- **Reranking (Paso de Re-ordenamiento):**
    - Implementar un modelo de Cross-Encoder (ej: `BGE-Reranker`) que analice los top 5 resultados de Neon y los ordene por relevancia semántica real antes de enviarlos al LLM.
- **Búsqueda Híbrida:**
    - Combinar **Vector Search** (significado) con **Keyword Search** (BM25) para mejorar la precisión en términos técnicos, nombres de personas o números de internos específicos.
- **Extracción de Tablas:**
    - Utilizar librerías como `Unstructured` o modelos de visión para capturar tablas de beneficios o calendarios de vacaciones con alta fidelidad estructural.
- **Query Expansion:**
    - Generar múltiples variaciones de la pregunta del usuario para cubrir más ángulos de búsqueda en la base de datos vectorial.

## 🛡️ 3. Robustez y Seguridad
- **Evaluación por Referencia:** Comparar las respuestas de la IA contra un "Ground Truth" (respuestas maestras redactadas por humanos) para obtener métricas de precisión exactas.
- **PII Masking:** Implementar un filtro que detecte y enmascare información sensible (DNI, salarios, etc.) antes de enviarla a los modelos externos de IA.

## 📈 4. Análisis y Producto (Feedback Loop)
- **Análisis de Brechas (Gap Analysis):**
    - Crear un log de preguntas donde el bot respondió "No encontré información". Esto servirá como guía para que RRHH sepa qué documentación falta crear o actualizar.
- **Feedback Directo (Thumbs up/down):**
    - Agregar botones de calificación en cada respuesta para recolectar datos sobre la satisfacción del usuario y ajustar los prompts en consecuencia.
- **Dashboard de Auditoría:**
    - Una vista interna para ver el promedio de los puntajes de `Grading` y `Groundedness` de todas las consultas de los usuarios.

---
*Este documento sirve como guía estratégica para la Fase 2 del proyecto.*
