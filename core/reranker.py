from core.llm import LLMManager, LLMError
import json
import re

class HRReranker:
    """Expert neural reranker to filter and prioritize HR context."""
    def __init__(self):
        self.llm = LLMManager()

    async def rerank(self, query: str, chunks: list, top_n: int = 5) -> tuple[list[int], int]:
        """Devuelve los INDICES seleccionados de `chunks` (no el texto).

        Devolver indices en vez de texto evita que el caller tenga que
        re-derivar a que posicion original pertenece cada fragmento buscandolo
        por igualdad de contenido (fragil si dos chunks tienen texto identico).
        """
        if not chunks: return [], 0
        
        numbered_chunks = ""
        for i, chunk in enumerate(chunks):
            # Proporcionamos suficiente contexto para que el reranker decida
            numbered_chunks += f"ID:{i} | {chunk[:600]}\n"

        prompt = f"""Instrucción: Actúa como un experto en clasificación de documentos de RRHH.
Tu tarea es analizar la 'Pregunta' y los 'Fragmentos' para seleccionar los que la contestan específicamente.

Pregunta: {query}

Fragmentos:
{numbered_chunks}

REGLAS:
1. Un fragmento califica solo si responde específicamente lo que se pregunta. Que hable del mismo tema general (ej: "beneficios") sin contestar el dato puntual pedido NO alcanza.
2. Si ningún fragmento contesta específicamente la pregunta, respondé {{"ids": []}}. Es preferible una lista vacía a incluir fragmentos que no contestan lo pedido.
3. Responde ÚNICAMENTE un JSON con los IDs de los fragmentos que sí califican, ordenados por relevancia.
4. Formato: {{"ids": [0, 1, 2]}}
5. Devuelve solo los números de ID como enteros.
6. No des ninguna explicación.

Respuesta en JSON:"""

        try:
            # Usamos Flash para máxima velocidad en el reranking
            res, tokens = await self.llm.call(prompt, temperature=0, use_pro=False)
        except LLMError as e:
            print(f"⚠️ Reranking no disponible: {e}. Fallback a los primeros fragmentos.")
            return list(range(min(top_n, len(chunks)))), 0

        try:
            
            # Limpieza robusta del JSON
            clean_json = res.replace("```json", "").replace("```", "").strip()
            # Intentamos extraer solo el bloque JSON si hay basura
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match:
                clean_json = match.group(0)
                
            data = json.loads(clean_json)
            raw_ids = data.get("ids", [])
            
            # Conversión segura a enteros y filtrado de IDs válidos
            valid_ids = []
            for rid in raw_ids:
                try:
                    # Extraemos solo los números si el LLM devuelve "ID0"
                    if isinstance(rid, str):
                        num_match = re.search(r'\d+', rid)
                        if num_match:
                            val = int(num_match.group(0))
                        else:
                            continue
                    else:
                        val = int(rid)
                        
                    if 0 <= val < len(chunks) and val not in valid_ids:
                        valid_ids.append(val)
                except:
                    continue
            
            # Tomamos los mejores hasta el límite top_n
            selected_ids = valid_ids[:top_n]
            return selected_ids, tokens

        except Exception as e:
            print(f"⚠️ Reranking Error: {e}. Fallback a los primeros fragmentos.")
            return list(range(min(top_n, len(chunks)))), 0

reranker = HRReranker()
