from fastapi import FastAPI, HTTPException
try:
    from app.routes import QueryRequest, QueryResponse, Grading
except ImportError:
    from routes import QueryRequest, QueryResponse, Grading

from core.embeddings import EmbeddingManager
from core.llm import LLMManager
from core.guardrails import GuardrailManager
from core.repair import RepairManager
from evaluation.eval_runner import EvalRunner
import psycopg2
from config.settings import settings

app = FastAPI(title="HR AI Assistant API")

# Inicializamos managers
guardrail = GuardrailManager()
embed_manager = EmbeddingManager()
llm = LLMManager()
evaluator = EvalRunner()
repair_manager = RepairManager()

def get_context(query_text: str, threshold: float = 0.35):
    """Busca contexto en Neon con diagnósticos de recuperación."""
    query_embedding = embed_manager.generate_single_embedding(query_text)
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    
    # Recuperamos los top 5 sin filtrar por threshold inicialmente para diagnóstico
    query = """
        SELECT content, source, 1 - (embedding <=> %s::vector) AS similarity
        FROM documents 
        ORDER BY similarity DESC 
        LIMIT 5;
    """
    
    cur.execute(query, (query_embedding,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n🔍 [RETRIEVAL DIAGNOSTICS]")
    print(f"Query: {query_text}")
    print(f"Threshold: {threshold}")
    
    context = ""
    sources = set()
    filtered_results = []
    
    for content, source, similarity in results:
        passed = similarity >= threshold
        status = "✅ PASS" if passed else "❌ FAIL (Below threshold)"
        print(f"-> Source: {source} | Score: {similarity:.4f} | {status}")
        
        if passed:
            context += f"--- FUENTE: {source} (Similitud: {similarity:.2f}) ---\n{content}\n\n"
            sources.add(source)
            filtered_results.append(content)
    
    if not filtered_results:
        print("⚠️ DIAGNOSTIC: Threshold triggered. No documents reached the LLM.")
    else:
        print(f"📈 DIAGNOSTIC: {len(filtered_results)} documents sent to LLM.")
        
    return context, list(sources)

@app.post("/ask", response_model=QueryResponse)
async def ask_hr(request: QueryRequest):
    print(f"🤖 Procesando solicitud con motor: {settings.LLM_ENGINE.upper()}")
    # 0. Query Rewriting (Memoria / Mini-cerebro)
    rewritten_query = llm.rewrite_query(request.query, request.history)
    
    is_repaired = False # Inicialización por defecto
    
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
        
        # 3. Generation Inicial
        answer = llm.generate_answer(request.query, context, request.history)
        
        # 4. Ciclo de Validación y Reparación (Repair Loop)
        is_grounded = True
        groundedness_score = 1.0
        if settings.ENABLE_EVALUATION:
            try:
                # Primera validación de veracidad
                eval_res = evaluator.check_groundedness(answer, context)
                is_grounded = eval_res["status"] == "PASS"
                groundedness_score = eval_res["groundedness_score"]
                
                if not is_grounded:
                    # Intento de Reparación
                    answer = repair_manager.repair_answer(request.query, answer, context)
                    # Segunda validación de veracidad
                    eval_res = evaluator.check_groundedness(answer, context)
                    is_grounded = eval_res["status"] == "PASS"
                    groundedness_score = eval_res["groundedness_score"]
                    is_repaired = True # Señal para la UI
                    
                    if not is_grounded:
                        # Fallback final si la reparación falla
                        answer = "No encontré información suficiente en la base de conocimiento"
                        is_grounded = True 
                        groundedness_score = 1.0 # El fallback es veraz
                        is_repaired = False 
            except Exception as e:
                print(f"⚠️ FAIL-CLOSED: Error en auditoría, marcando como no verificado: {e}")
                is_grounded = False
                groundedness_score = 0.0
                is_repaired = False

        # 5. Grading Final (sobre la respuesta definitiva)
        grading_data = {"relevance": 5, "clarity": 5, "usefulness": 5, "total_score": 5.0}
        if settings.ENABLE_EVALUATION:
            try:
                grading_data = evaluator.get_grading(request.query, answer)
            except Exception as e:
                print(f"⚠️ Error en Grading: {e}")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            is_grounded=is_grounded,
            groundedness_score=groundedness_score,
            is_repaired=is_repaired,
            grading=Grading(**grading_data)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "HR AI Assistant API is running"}
