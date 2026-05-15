import sys
import os
import psycopg2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.embeddings import EmbeddingManager
from config.settings import settings

def test_retrieval(query_text):
    embed_manager = EmbeddingManager()
    query_embedding = embed_manager.generate_single_embedding(query_text)
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    
    # Usar el mismo operador que en main.py
    query = """
        SELECT content, source, (embedding <#> %s::vector) * -1 AS similarity
        FROM documents 
        ORDER BY embedding <#> %s::vector
        LIMIT 10;
    """
    
    cur.execute(query, (query_embedding, query_embedding))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n🔍 [RETRIEVAL TEST] Query: {query_text}")
    for i, (content, source, similarity) in enumerate(results):
        print(f"[{i+1}] Source: {source} | Score: {similarity:.4f}")
        print(f"Content snippet: {content[:150]}...")
        print("-" * 50)

if __name__ == "__main__":
    query = "¿Qué antigüedad necesito para el programa de Mentoría y qué rango debo tener?"
    test_retrieval(query)
