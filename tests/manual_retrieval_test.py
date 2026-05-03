import os
import sys
import psycopg2

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import settings
from core.embeddings import EmbeddingManager

def search_similar_docs(query_text, limit=3):
    """Prueba la búsqueda semántica en Neon."""
    # 1. Generar embedding de la pregunta
    embed_manager = EmbeddingManager()
    query_embedding = embed_manager.generate_single_embedding(query_text)
    
    # 2. Conectar a Neon y buscar por similitud de coseno
    # El operador <=> en pgvector calcula la distancia de coseno
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        query = """
            SELECT content, source, 1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        
        cur.execute(query, (query_embedding, query_embedding, limit))
        results = cur.fetchall()
        
        print(f"\n🔍 Resultados para: '{query_text}'")
        print("-" * 50)
        for i, (content, source, similarity) in enumerate(results):
            print(f"[{i+1}] Similitud: {similarity:.4f} | Fuente: {source}")
            print(f"Texto: {content[:150]}...")
            print("-" * 30)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error en la búsqueda: {e}")

if __name__ == "__main__":
    # Probemos con una pregunta que involucre a Javier Nielsen
    test_query = "¿Quién es el responsable de RSE y cómo lo contacto?"
    search_similar_docs(test_query)
