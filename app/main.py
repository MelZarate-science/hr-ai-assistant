from fastapi import FastAPI, HTTPException
try:
    from app.routes import QueryRequest, QueryResponse, Grading
except ImportError:
    from routes import QueryRequest, QueryResponse, Grading

from core.embeddings import EmbeddingManager
from core.llm import LLMManager
from core.guardrails import GuardrailManager
from evaluation.eval_runner import EvalRunner
import psycopg2
from config.settings import settings

app = FastAPI(title="HR AI Assistant API")

# Inicializamos managers
guardrail = GuardrailManager()
embed_manager = EmbeddingManager()
llm = LLMManager()
evaluator = EvalRunner()

def get_context(query_text: str, threshold: float = 0.45):
    """Busca contexto en Neon aplicando un umbral más permisivo para chunks grandes."""
    query_embedding = embed_manager.generate_single_embedding(query_text)
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    
    query = """
        SELECT content, source, 1 - (embedding <=> %s::vector) AS similarity
        FROM documents 
        WHERE 1 - (embedding <=> %s::vector) >= %s
        ORDER BY similarity DESC 
        LIMIT 5;
    """
    
    cur.execute(query, (query_embedding, query_embedding, threshold))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n--- DEBUG RETRIEVAL (Threshold: {threshold}) ---")
    context = ""
    sources = set()
    for content, source, similarity in results:
        print(f"-> Fragmento de [{source}] con similitud: {similarity:.4f}")
        context += f"--- FUENTE: {source} (Similitud: {similarity:.2f}) ---\n{content}\n\n"
        sources.add(source)
    
    if not results:
        print("⚠️ No se encontraron fragmentos que superen el umbral.")
    return context, list(sources)

@app.post("/ask", response_model=QueryResponse)
async def ask_hr(request: QueryRequest):
    # 0. Query Rewriting (Memoria / Mini-cerebro)
    rewritten_query = llm.rewrite_query(request.query, request.history)
    
    # 1. Guardrail (Opcional) - Usamos la query reescrita para evitar bloqueos falsos
    if settings.ENABLE_GUARDRAILS:
        try:
            if not guardrail.validate_query(rewritten_query):
                return QueryResponse(
                    answer="Lo siento, solo puedo responder preguntas relacionadas con Recursos Humanos.",
                    sources=[],
                    is_grounded=False,
                    grading=Grading(relevance=0, clarity=0, usefulness=0, total_score=0),
                    error="Blocked by guardrails"
                )
        except Exception as e:
            print(f"⚠️ Error en Guardrail: {e}. Continuando por defecto.")

    try:
        # 2. Retrieval - Usamos la query reescrita para una búsqueda más precisa
        context, sources = get_context(rewritten_query)
        
        if not context:
            return QueryResponse(
                answer="No encontré información suficiente en la base de conocimiento para responder a esa pregunta.",
                sources=[],
                is_grounded=True,
                grading=Grading(relevance=1, clarity=5, usefulness=1, total_score=1.0)
            )
        
        # 3. Generation - Ahora le pasamos la historia para que sea consistente
        # Usamos request.query (la original) para que el LLM entienda el tono y contexto conversacional,
        # mientras que el context ya fue recuperado usando la rewritten_query.
        answer = llm.generate_answer(request.query, context, request.history)
        
        # 4. Evaluation (Opcional)
        is_grounded = True
        grading_data = {"relevance": 5, "clarity": 5, "usefulness": 5, "total_score": 5.0}
        
        if settings.ENABLE_EVALUATION:
            try:
                is_grounded = evaluator.check_groundedness(answer, context)
                grading_data = evaluator.get_grading(request.query, answer)
            except Exception as e:
                print(f"⚠️ Error en Evaluación: {e}. Usando valores por defecto.")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            is_grounded=is_grounded,
            grading=Grading(**grading_data)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "HR AI Assistant API is running"}
