import os
import sys
import json
import psycopg2
from psycopg2.extras import execute_values

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import settings
from core.embeddings import EmbeddingManager

def load_chunks_from_json(json_path):
    """Carga los chunks desde el archivo JSON generado en la ingesta."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def upload_to_neon(data_with_embeddings):
    """Sube los datos y los vectores a la base de datos Neon."""
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        # Limpiar tabla antes de cargar para evitar duplicados en este ejercicio
        print("Limpiando tabla 'documents'...")
        cur.execute("DELETE FROM documents;")
        
        # Preparar los datos para una inserción masiva (Batch Insert)
        # Formato: (content, embedding, source, chunk_id)
        values = [
            (
                item["content"], 
                item["embedding"], 
                item["metadata"]["source"], 
                item["metadata"]["chunk_id"]
            ) 
            for item in data_with_embeddings
        ]
        
        print(f"Subiendo {len(values)} fragmentos a Neon...")
        execute_values(cur, """
            INSERT INTO documents (content, embedding, source, chunk_id) 
            VALUES %s
        """, values)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ ¡Carga en Neon completada exitosamente!")
    except Exception as e:
        print(f"❌ Error subiendo datos a Neon: {e}")

def main():
    json_path = os.path.join(settings.BASE_DIR, "data/processed/hr_chunks.json")
    
    # 1. Cargar Chunks
    print(f"Cargando chunks desde {json_path}...")
    chunks = load_chunks_from_json(json_path)
    
    # 2. Inicializar Manager de Embeddings
    embed_manager = EmbeddingManager()
    
    # 3. Generar Embeddings para todos los contenidos
    print("Generando embeddings (esto puede tardar unos segundos la primera vez)...")
    texts = [item["content"] for item in chunks]
    embeddings = embed_manager.generate_embeddings(texts)
    
    # 4. Combinar datos originales con sus embeddings
    for i, item in enumerate(chunks):
        item["embedding"] = embeddings[i]
        
    # 5. Subir a Neon
    upload_to_neon(chunks)

if __name__ == "__main__":
    main()
