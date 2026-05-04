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
    """Extrae el texto de un archivo PDF e intenta aplicar un formato Markdown básico."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if not page_text:
            continue
            
        lines = page_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detectar títulos (Líneas cortas en mayúsculas o que empiezan con números/secciones)
            if (line.isupper() and len(line) < 60) or any(line.startswith(s) for s in ["1.", "2.", "3.", "PROGRAMA", "POLÍTICA"]):
                formatted_lines.append(f"\n### {line}\n")
            # Detectar listas
            elif line.startswith("-") or line.startswith("•"):
                formatted_lines.append(f"* {line[1:].strip()}")
            # Detectar campos clave (Responsable, Interno, etc.)
            elif any(k in line for k in ["Responsable:", "Interno:", "Ubicación:", "Frecuencia:", "Requisitos:"]):
                # Poner la etiqueta en negrita
                parts = line.split(":", 1)
                formatted_lines.append(f"**{parts[0]}:** {parts[1].strip() if len(parts)>1 else ''}")
            else:
                formatted_lines.append(line)
        
        text += "\n".join(formatted_lines) + "\n"
    
    # Limpieza de saltos de línea duplicados
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
        
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
