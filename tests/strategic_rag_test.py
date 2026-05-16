import asyncio
import sys
import os

# Asegurar que el directorio raíz esté en el path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import orchestrator

async def run_tests():
    test_cases = [
        {
            "name": "Prueba 1: Exhaustividad de Beneficios",
            "query": "Listame todos los beneficios corporativos por pilar",
            "history": []
        },
        {
            "name": "Prueba 2: Filtrado por Antigüedad (1 mes)",
            "query": "Tengo 1 mes en la empresa, ¿a qué programas de RSE me puedo anotar?",
            "history": []
        },
        {
            "name": "Prueba 3: Beneficios 'Invisibles' (Idiomas)",
            "query": "¿Qué es el Kit de Idiomas GlobalTalk?",
            "history": []
        },
        {
            "name": "Prueba 4: Calidad de Vida (Comedor y Flex)",
            "query": "¿Cuáles son los beneficios del Pilar 3 (Calidad de Vida)?",
            "history": []
        },
        {
            "name": "Prueba 5: Bono Vacacional (Anexo)",
            "query": "¿Existe algún bono especial relacionado con las vacaciones?",
            "history": []
        }
    ]

    print("🚀 Iniciando Batería de Pruebas Estratégicas...\n")

    for test in test_cases:
        print(f"--- {test['name']} ---")
        print(f"Pregunta: {test['query']}")
        
        answer, sources, is_grounded, score, is_repaired, grading, telemetry = await orchestrator.process_query(test['query'], test['history'])
        
        print(f"Respuesta AI:\n{answer}")
        print(f"Fuentes: {sources}")
        print(f"Groundedness: {score} | Repaired: {is_repaired}")
        print(f"Grading: {grading['total_score']}/5.0")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
