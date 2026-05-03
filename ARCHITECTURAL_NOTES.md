# Bitácora de Aprendizaje: Arquitectura RAG (Recursos Humanos)

Este documento detalla las decisiones técnicas y los conceptos aprendidos durante la construcción del sistema de asistencia de RRHH.

## 1. El Flujo de Datos Profesional (ETL para RAG)
En la industria, no pasamos directamente de un archivo (PDF/Word) a la Base de Datos. Seguimos un proceso de **ETL (Extract, Transform, Load)**.
- **Extract (Extracción):** Sacar el texto crudo del PDF usando librerías como `pypdf`.
- **Transform (Transformación):** Limpiar el texto de caracteres raros y estructurarlo en un formato JSON intermedio. Esto permite normalizar datos de múltiples fuentes.
- **Load (Carga):** Guardar el resultado final en la base de datos vectorial (Neon).

## 2. ¿Por qué el paso intermedio a JSON?
- **Normalización:** Convierte cualquier origen (PDF, Excel, Email) en un estándar único para que la IA siempre lea lo mismo.
- **Depuración (Debugging):** Permite a los ingenieros abrir el archivo `hr_chunks.json` y verificar si el texto se cortó bien antes de gastar recursos subiéndolo.
- **Eficiencia (Caché):** Leer un PDF consume CPU y tiempo. Leer un JSON es casi instantáneo.

## 3. Estrategia de Chunking (Fragmentación)
El "Chunking" es dividir un libro largo en trozos que la IA pueda digerir.
- **RecursiveCharacterTextSplitter:** Es el método más inteligente porque intenta no romper párrafos ni oraciones. Busca primero `\n\n`, luego `\n`, luego puntos y finalmente espacios.
- **Evolución del Tamaño:** 
    - Empezamos con 600 caracteres (muy pequeño, fragmentaba la información).
    - Subimos a 1500 (mejor cohesión).
    - **Lección Final:** Para documentos corporativos cortos, el tamaño debe ser lo suficientemente grande para que cada documento sea una unidad lógica completa (Document-as-a-Chunk).

## 4. El "Cerebro" Vectorial: Embeddings y pgvector
- **Embeddings:** Son traductores que convierten "palabras" en "listas de números" (vectores). Estos números representan el significado. Las palabras "Perro" y "Can" tendrán vectores muy parecidos.
- **Neon (pgvector):** Es una extensión de PostgreSQL que permite guardar estos vectores y buscar entre ellos usando matemáticas de distancias (como buscar la dirección más cercana en un mapa).

## 5. Búsqueda Semántica (Retrieval) e Indices de Similitud
El sistema no busca por "palabras exactas" (como Ctrl+F), sino por "intención". 
- **Distancia de Coseno:** Técnica matemática para medir el ángulo entre dos vectores. Si el ángulo es pequeño, las ideas son similares.

## 6. Optimización: Similarity Threshold (Umbral)
Para evitar que el bot diga cosas que no tienen sentido y para ahorrar dinero (tokens), aplicamos un filtro de calidad.
- **Concepto:** Solo los fragmentos con un puntaje de similitud alto pasan al LLM.
- **Calibración:** Descubrimos que **0.51** es el umbral ideal en este proyecto para separar temas de Vacaciones (0.52) de temas de RSE (0.50).

## 7. Gestión de Cuotas y Límites de API (Rate Limits)
- **Desafío:** Las APIs de IA (Gemini, Groq) limitan cuántas veces puedes preguntar por minuto (RPM) o por día (RPD).
- **Estrategia de Desarrollo:** Implementamos "Toggles" (interruptores) en el código para desactivar módulos costosos como la Evaluación mientras estamos construyendo la lógica base.

## 8. Aumentación y Generación (LLM)
- **Aumentación:** Es el acto de "rellenar" el prompt con la información encontrada en la base de datos.
- **Generación:** El modelo (Llama 3.3 o Gemini) redacta la respuesta basándose únicamente en ese "libro abierto" que le inyectamos.
- **Temperatura (0.1):** Mantiene a la IA "seria" y evita que se ponga creativa o invente datos.

## 9. Guardrails (Seguridad)
Son los "guardaespaldas" del bot. Usamos un prompt de clasificación que analiza la pregunta del usuario *antes* de procesarla.
- **PASS:** La pregunta es de RRHH y es segura.
- **FAIL:** La pregunta es ofensiva o fuera de ámbito.

## 10. Capa de Evaluación (Auditoría Automática)
Un sistema profesional no confía ciegamente en la IA. Tenemos dos auditores automáticos:
- **Groundedness:** Verifica que cada frase de la respuesta esté respaldada por los documentos originales. Evita las alucinaciones.
- **Grading:** Califica del 1 al 5 la Relevancia, Claridad y Utilidad de la respuesta.

## 11. Exposición vía API (FastAPI) y Validación
- **FastAPI:** Permite que cualquier aplicación (web, móvil, chat) use nuestro cerebro de IA mediante el protocolo HTTP.
- **Pydantic:** Es un "contrato de datos". Asegura que si el bot promete entregar un JSON con 4 campos, siempre entregue esos 4 campos y no se rompa el sistema.

## 12. Equilibrio de Recuperación: El factor Top-K (LIMIT)
- **Top-K:** Es el número de fragmentos que le permitimos leer a la IA. 
- **Ajuste:** Subir de 3 a 5 fragmentos mejora la cobertura de información (Recall), pero hace que el bot lea más texto (mayor costo).

## 13. Memoria Conversacional y el problema de la "Amnesia"
Sin memoria, la IA trata cada mensaje como si el usuario acabara de nacer. 
- **Problema:** Si el usuario pregunta "¿Y quién es su responsable?", la IA no sabe de qué "responsable" hablamos si no recuerda el mensaje anterior.
- **Solución:** Enviar una "ventana de contexto" con los últimos mensajes.

## 14. Reescritura de Consultas (Query Rewriting)
Pasar toda la historia de chat a la base de datos es caro y confuso. La técnica profesional es la **Reescritura**.
- **Proceso:** Tomar (Historia + Pregunta Nueva) ➔ Generar una única frase clara e independiente para buscar en la base de datos.
- **Ejemplo:** "Me gusta el de colecta, ¿me das más info?" ➔ Reescrito: "¿Cuáles son los detalles técnicos y responsables del programa Colecta Cuidado Verde?".

## 15. SLM vs LLM: El concepto de "Mini-Cerebro"
No todas las tareas requieren un modelo gigante (LLM).
- **LLM (Gerente):** Modelos como Llama 3.3 (70B). Son inteligentes, redactan bien, pero son más lentos y caros. Se usan para la **Respuesta Final**.
- **SLM (Asistente):** Modelos como Llama 3 (8B). Son pequeñitos, ultra rápidos y casi gratuitos. Se usan para tareas mecánicas como **Reescritura de Consultas** y **Guardrails**.
- **Ventaja en el mercado:** Usar un mini-cerebro para las tareas intermedias reduce el costo operativo del RAG en un 60-80%.
