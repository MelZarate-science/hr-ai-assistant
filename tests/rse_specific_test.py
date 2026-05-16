import asyncio
import sys
import os

# Asegurar que el directorio raíz esté en el path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import orchestrator

async def run_targeted_tests():
    test_cases = [
        "Tengo un mes, ¿a qué programas de RSE me puedo sumar?",
        "¿Cuáles son los voluntariados de RSE?",
        "Si soy voluntaria en algún programa, ¿obtengo algún beneficio?"
    ]

    print("🧪 Ejecutando Pruebas Específicas de RSE...\n")

    for query in test_cases:
        print(f"Pregunta: {query}")
        answer, sources, is_grounded, score, is_repaired, grading, telemetry = await orchestrator.process_query(query, [])
        print(f"Respuesta AI:\n{answer}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_targeted_tests())
