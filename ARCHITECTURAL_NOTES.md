# Bitácora de Aprendizaje: Arquitectura RAG (Recursos Humanos)

Este documento detalla las decisiones técnicas y los conceptos aprendidos durante la construcción del sistema de asistencia de RRHH bajo una arquitectura desacoplada de nivel empresarial.

## 1. El Flujo de Datos Profesional (ETL para RAG)
En la industria, no pasamos directamente de un archivo (PDF/Word) a la Base de Datos. Seguimos un proceso de **ETL (Extract, Transform, Load)**.
- **Extract (Extracción):** Sacar el texto crudo del PDF usando librerías como `pypdf`.
- **Transform (Transformación):** Limpiar el texto de caracteres raros y estructurarlo en un formato JSON intermedio. Esto permite normalizar datos de múltiples fuentes.
- **Load (Carga):** Guardar el resultado final en la base de datos vectorial (Neon).

## 2. ¿Por qué el paso intermedio a JSON?
- **Normalización:** Convierte cualquier origen (PDF, Excel, Email) en un estándar único para que la IA siempre lea lo mismo.
- **Depuración (Debugging):** Permite a los ingenieros abrir el archivo `hr_chunks.json` y verificar si el texto se cortó bien antes de gastar recursos subiéndolo.
- **Eficiencia (Caché):** Leer un PDF consume CPU y tiempo. Leer un JSON es casi instantáneo.

## 3. Estrategia de Chunking (Hierarchical Markdown Splitter + Metadata Enrichment)
El "Chunking" es dividir un documento largo en trozos que la IA pueda digerir.
- **Markdown-Aware:** Usamos `MarkdownHeaderTextSplitter` para respetar la jerarquía estructural (#, ##).
- **Metadata Enrichment (Parent Context):** Aplicamos una técnica de enriquecimiento donde cada fragmento es precedido por su contexto jerárquico (`[CONTEXTO: Titulo > Sección]`). Esto fortalece el vector semántico y asegura que la información de contexto y reglas se mantengan juntas.
- **Tamaño de Fragmento (Chunk Size):** Calibrado a **600 caracteres**. Este ajuste de grano fino asegura una mayor densidad semántica por vector, permitiendo que beneficios pequeños (ej: Kit de Idiomas) no se diluyan en fragmentos demasiado extensos y sean recuperados con mayor precisión.

## 4. El "Cerebro" Vectorial: Normalización L2 y pgvector
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`.
- **Normalización L2:** Implementamos una capa de normalización en `core/embeddings.py` que convierte todos los vectores a longitud 1. Esto permite usar Producto Punto como métrica de similitud con la misma precisión que Coseno pero mayor velocidad.
- **Neon (HNSW Index):** Creamos un índice **HNSW (Hierarchical Navigable Small World)** usando `vector_ip_ops` (Inner Product). Esto permite búsquedas ultra rápidas en milisegundos incluso con grandes volúmenes de datos.

## 5. Arquitectura Desacoplada (Enterprise Pattern)
Hemos evolucionado de un script monolítico a una estructura de servicios especializados:
- **DatabaseManager (`core/database.py`):** Implementa un **ThreadedConnectionPool** con Keep-Alive y reintentos automáticos.
- **HRRetriever (`core/retriever.py`):** Encapsula la lógica de búsqueda SQL y similitud vectorial.
- **RAGOrchestrator (`core/orchestrator.py`):** Centraliza el pipeline (Rewriting -> Guardrail -> Retrieval -> Generation -> Evaluation).
- **Prompt Centralization:** Todos los prompts del sistema viven exclusivamente en la carpeta `/prompts`.

## 6. Optimización: Similarity Threshold (Umbral)
- **Calibración:** Establecido en **0.25**. Un equilibrio perfecto para filtrar ruido sin perder información técnica relevante tras el enriquecimiento de metadatos.

## 7. Gestión de Cuotas y Límites de API (Rate Limits)
- **Toggles:** Interruptores en `.env` para desactivar módulos costosos durante el desarrollo.

## 8. Aumentación y Generación (LLM)
- **Arquitectura por Tiers (Gemini):** El sistema utiliza **Gemini 2.5 Flash** para tareas rápidas y de bajo costo (como reformulación de consultas) y **Gemini 2.5 Pro** para las tareas complejas de razonamiento, generación final y evaluación de veracidad.
- **Aumentación:** Inyección de hasta 10 fragmentos de contexto enriquecido en formato TOON.
- **Temperatura 0.0:** Configuramos el motor de IA con temperatura cero para garantizar respuestas deterministas y evitar alucinaciones creativas.

## 9. Guardrails (Seguridad)
- **GuardrailManager:** Clasificador basado en SLM que detecta si la consulta es del ámbito de RRHH antes de procesarla.

## 10. Capa de Evaluación (Auditoría Automática)
- **Groundedness:** Verifica la veracidad basada en evidencia con sanitización resiliente.
- **Grading:** Calificación 1-5 en Relevancia, Claridad y Utilidad.

## 11. Exposición vía API (FastAPI) y Validación
- **Contratos Pydantic:** Aseguran que el frontend (Streamlit) y el backend hablen el mismo idioma.

## 12. Equilibrio de Recuperación: El factor Top-K (LIMIT)
- **Ajuste:** Optimizado a **10 fragmentos** finales (Top-10) seleccionados mediante **Reranking SLM** de un pool inicial de 20 candidatos. Esto garantiza alta cobertura (Recall) y precisión extrema.

## 13. Memoria Conversacional y el problema de la "Amnesia"
- **Window Context:** Enviamos los últimos 3 mensajes para mantener el hilo de la charla.

## 14. Reescritura de Consultas (Query Rewriting)
- **Rewriter Minimalista:** Prompt diseñado para resolver referencias sin alterar las palabras clave originales ni generalizar temas.

## 15. Ciclo de Reparación "Ciego" (Self-Healing)
- **Blind Repair:** Corrección automática de alucinaciones sin meta-texto explicativo.

## 16. Optimización de Contexto: TOON (Token-Oriented Object Notation)
Implementamos **TOON** para el envío de documentos recuperados.
- **Técnica:** Estructura tabular compacta (`fuente|contenido`) que preserva la jerarquía de la información mediante una gestión inteligente de saltos de línea.
- **Impacto:** Ahorro masivo de tokens (~40%) sin sacrificar la capacidad del modelo para interpretar listados complejos y jerarquías internas.
