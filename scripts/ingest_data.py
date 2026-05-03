import os
import sys
import json
from pathlib import Path
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import psycopg2

# Añadir el directorio raíz al path para poder importar la configuración
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import settings

def extract_text_from_pdf(pdf_path):
    """Extrae el texto de un archivo PDF."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        # Limpieza básica de texto
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def chunk_text(text):
    """Divide el texto en trozos pequeños según la configuración."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_text(text)

def save_to_json(data, output_path):
    """Guarda los trozos procesados en un archivo JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Archivo JSON generado exitosamente en: {output_path}")

def setup_database():
    """Habilita pgvector y asegura que la tabla exista en Neon."""
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                content text,
                embedding vector(384),
                source text,
                chunk_id int
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Base de datos Neon preparada (pgvector + tabla).")
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")

def main():
    # 1. Preparar DB (Solo asegurar estructura)
    setup_database()
    
    # 2. Procesar PDFs
    docs_dir = Path(settings.BASE_DIR) / "data/raw/hr_docs"
    processed_data = []
    
    print(f"\nIniciando procesamiento de documentos en {docs_dir}...")
    
    for pdf_path in docs_dir.glob("*.pdf"):
        print(f"📄 Procesando: {pdf_path.name}")
        
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            processed_data.append({
                "content": chunk.strip(),
                "metadata": {
                    "source": pdf_path.name,
                    "chunk_id": i
                }
            })
        print(f"   - {len(chunks)} fragmentos extraídos.")

    # 3. Guardar en JSON (El paso intermedio de inspección)
    output_json = Path(settings.BASE_DIR) / "data/processed/hr_chunks.json"
    save_to_json(processed_data, output_json)
    
    print(f"\nTotal de fragmentos listos para embedding: {len(processed_data)}")

if __name__ == "__main__":
    main()
