# 🚀 Plan de Rescate y Optimización: Fase 2

Este documento detalla las acciones inmediatas para estabilizar el sistema, eliminar alucinaciones cruzadas y reducir drásticamente la latencia y el consumo de tokens.

## 1. Diagnóstico de Latencia y Tokens
Actualmente, el sistema consume entre **4000 y 8000 tokens** por consulta, lo que genera:
- Latencia alta (tiempos de espera largos).
- Errores 429 (Rate Limit) en la API de Groq.
- Alucinaciones cruzadas (mezcla de beneficios de distintos documentos).

---

## 2. Acciones Técnicas Inmediatas

### A. Re-Ingesta Minimalista (Scripts/ingest_data.py)
- **Reducir Chunk Size a 800 caracteres.** (Actualmente 1500).
- **Objetivo:** Lograr fragmentos "atómicos" que contengan solo una regla o programa, evitando que el buscador traiga ruido irrelevante.

### B. Ajuste de Reranking (Core/orchestrator.py)
- **Reducir Top-N de 10 a 4.** 
- **Objetivo:** Entregarle a la IA grande solo la "crema" de la información. Esto bajará el consumo de tokens a menos de 2000 por consulta.

### C. Implementación de Telemetría de Latencia (End-to-End)
Añadiremos medición de milisegundos en cada paso en `core/orchestrator.py`:
1.  **Rewriting Time**
2.  **Retrieval Time**
3.  **Reranking Time**
4.  **Generation Time**
5.  **Audit/Repair Time**
*Esto permitirá identificar exactamente cuál es el cuello de botella.*

### D. Reglas de Aislamiento de Fuentes (Prompts/system_prompt.txt)
Añadir una instrucción de seguridad:
- *"Cada documento es independiente. No apliques beneficios de salud a programas de voluntariado a menos que el texto lo diga explícitamente en la misma línea."*

---

## 3. Hoja de Ruta de Ejecución
1.  **Ejecutar Limpieza**: `pip install torchvision` para silenciar avisos finales.
2.  **Actualizar Parámetros**: Modificar `ingest_data.py` (800 chars) y `orchestrator.py` (K=4).
3.  **Re-Indexar**: `python scripts/ingest_data.py` y `python scripts/build_index.py`.
4.  **Validar**: Realizar pruebas de "Antigüedad 1 mes" para confirmar el filtrado correcto y la baja latencia.

---
*Este plan garantiza un sistema ágil, económico y libre de alucinaciones para un entorno de producción real.*
