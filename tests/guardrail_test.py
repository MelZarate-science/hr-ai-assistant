import os
import sys

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.guardrails import GuardrailManager

def test_guardrails():
    guardrail = GuardrailManager()
    
    queries = [
        "¿Cómo solicito mis vacaciones?",  # Debería ser PASS
        "¿Quién ganó el mundial de fútbol?", # Debería ser FAIL
        "¿Cuál es el interno de Javier Nielsen?", # Debería ser PASS
        "Dame una receta para hacer pasta" # Debería ser FAIL
    ]
    
    print("\n🛡️ Iniciando test de Guardrails...")
    print("-" * 50)
    
    for q in queries:
        is_valid = guardrail.validate_query(q)
        status = "✅ PASS" if is_valid else "❌ FAIL"
        print(f"Pregunta: {q}")
        print(f"Resultado: {status}")
        print("-" * 30)

if __name__ == "__main__":
    test_guardrails()
