import os
import sys
import json
import re
from pathlib import Path
from pypdf import PdfReader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import psycopg2

# Añadir el directorio raíz al path para poder importar la configuración
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import settings

def extract_text_from_pdf(pdf_path):
    """Extrae el texto de un archivo PDF con reglas estrictas para evitar fragmentación lógica."""
    reader = PdfReader(pdf_path)
    text = ""
    # El primer título que encontremos será el Título del Documento (#)
    doc_title_found = False
    
    for page in reader.pages:
        page_text = page.extract_text()
        if not page_text: continue
            
        lines = page_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
                
            # 1. Título del Documento (Solo el primero que sea todo mayúsculas o muy corto arriba)
            if not doc_title_found and ((line.isupper() and len(line) < 60) or "POLÍTICA" in line or "PROGRAMA" in line):
                formatted_lines.append(f"\n# {line}\n")
                doc_title_found = True
            # 2. Secciones Principales (Ej: 1. INTRODUCCIÓN, 2. PROGRAMAS ACTIVOS, 2. SALUD (Pilar 1))
            # Regla: Número solo (sin punto secundario) seguido de texto en mayúsculas, espacios, paréntesis y números
            elif re.match(r'^\d+\.\s+[A-ZÁÉÍÓÚÑ \(\)\d]+$', line):
                formatted_lines.append(f"\n## {line}\n")
            # 3. Todo lo demás: Negrita para jerarquía visual pero NO para corte
            elif re.match(r'^\d+\.\d+\.', line) or re.match(r'^\d+\.', line) or line.isupper():
                formatted_lines.append(f"\n**{line}**")
            # 4. Listas
            elif line.startswith("-") or line.startswith("•") or line.startswith("*"):
                formatted_lines.append(f"* {line[1:].strip()}")
            # 5. Campos clave
            elif any(k in line for k in ["Responsable:", "Interno:", "Ubicación:", "Frecuencia:", "Vigencia:", "Requisitos:"]):
                parts = line.split(":", 1)
                formatted_lines.append(f"**{parts[0]}:** {parts[1].strip() if len(parts)>1 else ''}")
            else:
                formatted_lines.append(line)
        
        text += "\n".join(formatted_lines) + "\n"
    
    return re.sub(r'\n{3,}', '\n\n', text)

def chunk_text(text):
    """Divide el texto estructuralmente SOLO en secciones principales (##)."""
    headers_to_split_on = [("#", "Document"), ("##", "Section")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(text)
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE, # Tamaño dinámico según configuración
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    final_chunks = []
    for doc in md_header_splits:
        # Enriquecimiento de Metadatos (Parent Context Injection)
        doc_title = doc.metadata.get("Document", "General")
        section_title = doc.metadata.get("Section", "Contenido")
        
        enriched_prefix = f"[CONTEXTO: {doc_title} > {section_title}]\n"
        
        # Si el contenido es largo, lo dividimos usando el text_splitter
        # El CHUNK_SIZE de settings (600) se aplicará aquí
        if len(doc.page_content) > settings.CHUNK_SIZE:
            sub_chunks = text_splitter.split_text(doc.page_content)
            for sc in sub_chunks:
                final_chunks.append(f"{enriched_prefix}{sc}")
        else:
            final_chunks.append(f"{enriched_prefix}{doc.page_content}")
            
    return final_chunks

def setup_database():
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("DROP TABLE IF EXISTS interactions;")
        cur.execute("DROP TABLE IF EXISTS documents;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                created_at timestamptz DEFAULT now(),
                query text, rewritten_query text, answer text,
                is_grounded boolean, groundedness_score float, sources text[]
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                content text, embedding vector(384), source text, chunk_id int
            );
        """)
        cur.execute("CREATE INDEX idx_documents_embedding_dot_product ON documents USING hnsw (embedding vector_ip_ops);")
        conn.commit(); cur.close(); conn.close()
        print("✅ DB Preparada.")
    except Exception as e: print(f"❌ DB Error: {e}")

def main():
    setup_database()
    docs_dir = Path(settings.BASE_DIR) / "data/raw/hr_docs"
    processed_data = []
    for pdf_path in docs_dir.glob("*.pdf"):
        print(f"📄 Procesando: {pdf_path.name}")
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            processed_data.append({"content": chunk.strip(), "metadata": {"source": pdf_path.name, "chunk_id": i}})
        print(f"   - {len(chunks)} fragmentos de alta integridad.")

    with open(Path(settings.BASE_DIR) / "data/processed/hr_chunks.json", 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Total: {len(processed_data)} fragmentos.")

if __name__ == "__main__":
    main()
