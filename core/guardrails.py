from core.llm import LLMManager
from config.settings import settings
from pathlib import Path

class GuardrailManager:
    def __init__(self):
        self.llm = LLMManager()
        self.prompt_path = Path(settings.BASE_DIR) / "prompts" / "guardrail_prompt.txt"

    def _load_prompt(self):
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def validate_query(self, query: str) -> bool:
        """Usa el LLM para validar la pregunta con el prompt de guardrail."""
        prompt_tmpl = self._load_prompt()
        final_prompt = prompt_tmpl.format(query=query)
        
        try:
            # Usamos call() directamente para el guardrail con temperatura 0
            result = self.llm.call(final_prompt, temperature=0)
            
            if "PASS" in result.upper():
                return True
            else:
                print(f"⚠️ Guardrail activado para: {query}")
                return False
        except Exception as e:
            print(f"❌ Error en Guardrail: {e}")
            return True
