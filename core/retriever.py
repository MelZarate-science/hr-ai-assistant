from core.database import db_manager
from core.embeddings import EmbeddingManager

class HRRetriever:
    def __init__(self):
        self.embed_manager = EmbeddingManager()

    def get_relevant_context(self, query_text: str, threshold: float = 0.20, top_k: int = 20):
        """
        Busca contexto en la base de datos usando similitud vectorial.
        Devuelve una lista de fragmentos (chunks) para ser procesados por el Reranker.
        """
        query_embedding = self.embed_manager.generate_single_embedding(query_text)
        conn = db_manager.get_connection()
        chunks = []
        sources = []
        
        try:
            cur = conn.cursor()
            sql = """
                SELECT content, source, (embedding <#> %s::vector) * -1 AS similarity
                FROM documents 
                ORDER BY embedding <#> %s::vector
                LIMIT %s;
            """
            cur.execute(sql, (query_embedding, query_embedding, top_k))
            results = cur.fetchall()
            
            for content, source, similarity in results:
                if similarity >= threshold:
                    # Guardamos el chunk con su metadata enriquecida
                    chunks.append(content)
                    sources.append(source)
            
            cur.close()
        except Exception as e:
            print(f"❌ Error durante el retrieval: {e}")
        finally:
            db_manager.release_connection(conn)
            
        return chunks, sources

# Instancia única del recuperador
retriever = HRRetriever()
