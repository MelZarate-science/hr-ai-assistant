from core.llm import LLMManager
from config.settings import settings
import json

class HRReranker:
    def __init__(self):
        self.llm = LLMManager()

    def rerank(self, query: str, chunks: list, top_n: int = 5) -> tuple[list, int]:
        """
        Usa un SLM (Llama 8B) para re-ordenar los chunks recuperados por relevancia real.
        Recibe una lista de strings (chunks) y devuelve los top_n mejores.
        """
        if not chunks:
            return [], 0

        # Preparamos los chunks con un ID para que el LLM los identifique fácilmente
        numbered_chunks = ""
        for i, chunk in enumerate(chunks):
            # Limpiamos un poco el texto para el reranker
            clean_text = chunk.replace("\n", " ")[:300] 
            numbered_chunks += f"ID:{i} | {clean_text}\n"

        prompt = f"""Instrucción: Actúa como un experto en clasificación de documentos de RRHH.
Tu tarea es analizar la 'Pregunta del Usuario' y los 'Fragmentos Recuperados'.
Selecciona los {top_n} fragmentos más relevantes que contienen la respuesta exacta.

Pregunta: {query}

Fragmentos:
{numbered_chunks}

REGLAS:
1. Responde ÚNICAMENTE con una lista de IDs en formato JSON, del más relevante al menos relevante.
2. Formato: {{"ids": [ID1, ID2, ID3, ID4, ID5]}}
3. No des explicaciones.

Respuesta en JSON:"""

        try:
            # Usamos el modelo pequeño (SLM) para velocidad y bajo costo
            res, tokens = self.llm.call(prompt, temperature=0, model_name=settings.SLM_MODEL)
            
            # Limpieza y parsing del JSON
            clean_json = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            selected_ids = data.get("ids", [])[:top_n]
            
            # Re-filtramos los chunks originales basados en los IDs seleccionados
            reranked_chunks = [chunks[i] for i in selected_ids if i < len(chunks)]
            return reranked_chunks, tokens
            
        except Exception as e:
            print(f"⚠️ Error en Reranking: {e}. Usando fallback (primeros N).")
            # Fallback: devolver los primeros N tal cual vinieron de la DB
            return chunks[:top_n], 0

reranker = HRReranker()
