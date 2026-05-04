import asyncio
import sys
import os
# Asegurar que el directorio raíz esté en el path
sys.path.append(os.getcwd())

from app.main import ask_hr
from app.routes import QueryRequest

async def test_refusal():
    request = QueryRequest(
        query="¿Cuántos días de vacaciones tengo si llevo 3 años?",
        history=[]
    )
    print("--- INICIANDO TEST DE TRAZABILIDAD ---")
    try:
        response = await ask_hr(request)
        print("\n--- RESPUESTA FINAL ---")
        print(f"Respuesta: {response.answer}")
        print(f"Grounded: {response.is_grounded}")
        print(f"Repaired: {response.is_repaired}")
        print(f"Score: {response.groundedness_score}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_refusal())
