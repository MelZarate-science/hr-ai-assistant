from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str = Field(..., example="¿Cuántos días de vacaciones tengo?")
    history: List[dict] = Field(default=[], example=[{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "Hola, ¿en qué puedo ayudarte?"}])

class Grading(BaseModel):
    relevance: int
    clarity: int
    usefulness: int
    total_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    is_grounded: bool
    groundedness_score: float = 0.0
    is_repaired: bool = False
    grading: Grading
    reasoning: Optional[str] = "No se proporcionó razonamiento adicional."
    error: Optional[str] = None
