import os
import sys
import psycopg2

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import settings
from core.embeddings import EmbeddingManager
from core.llm import LLMManager
from core.guardrails import GuardrailManager
from evaluation.eval_runner import EvalRunner

def get_context_from_neon(query_text, limit=3):
    embed_manager = EmbeddingManager()
    query_embedding = embed_manager.generate_single_embedding(query_text)
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    query = "SELECT content, source FROM documents ORDER BY embedding <=> %s::vector LIMIT %s;"
    cur.execute(query, (query_embedding, limit))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    context = ""
    for content, source in results:
        context += f"--- FUENTE: {source} ---\n{content}\n\n"
    return context

def run_full_pipeline(user_query):
    print(f"\n--- INICIANDO PIPELINE PARA: '{user_query}' ---")
    
    # 1. Guardrail
    guardrail = GuardrailManager()
    if not guardrail.validate_query(user_query):
        print("❌ Bloqueado por Guardrails")
        return

    # 2. Retrieval
    context = get_context_from_neon(user_query)
    
    # 3. Generation
    llm = LLMManager()
    answer = llm.generate_answer(user_query, context)
    
    # 4. Evaluation
    evaluator = EvalRunner()
    is_grounded = evaluator.check_groundedness(answer, context)
    grading = evaluator.get_grading(user_query, answer)
    
    # MOSTRAR RESULTADOS
    print("\n" + "="*60)
    print("ASISTENTE DE RRHH:")
    print("-" * 60)
    print(answer)
    print("="*60)
    
    print("\n📊 REPORTE DE EVALUACIÓN:")
    print(f"Veracidad (Groundedness): {'✅ PASS' if is_grounded else '❌ FAIL'}")
    print(f"Puntajes: Relevance={grading['relevance']}, Clarity={grading['clarity']}, Usefulness={grading['usefulness']}")
    print(f"Puntaje Total: {grading['total_score']}/5.0")
    print("="*60)

if __name__ == "__main__":
    # Prueba legítima
    run_full_pipeline("¿Cuáles son los beneficios de gimnasio?")
    
    # Prueba de "Alucinación" (Preguntar algo que no existe para ver si falla el groundedness o el bot dice que no sabe)
    # run_full_pipeline("¿Cómo pido mi bono de navidad de 5000 dólares?")
