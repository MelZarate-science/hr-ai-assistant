from fastapi import FastAPI
from app.routes import QueryRequest, QueryResponse, Grading
from core.orchestrator import orchestrator
from core.database import db_manager

app = FastAPI(title="HR AI Assistant API (Enterprise Refactor)")

@app.post("/ask", response_model=QueryResponse)
async def ask_hr(request: QueryRequest):
    # Delegamos toda la lógica al orquestador
    answer, sources, is_grounded, score, is_repaired, grading, telemetry, reasoning = \
        await orchestrator.process_query(request.query, request.history)

    return QueryResponse(
        answer=answer, 
        sources=sources, 
        is_grounded=is_grounded, 
        groundedness_score=score, 
        is_repaired=is_repaired, 
        grading=Grading(**grading),
        reasoning=reasoning,
        telemetry=telemetry
    )

@app.on_event("shutdown")
def shutdown_event():
    # Nos aseguramos de cerrar el pool de conexiones al apagar la app
    db_manager.close_all()

@app.get("/")
async def root(): 
    return {"message": "HR AI Assistant API - Enterprise Edition Active"}
