from core.llm import LLMManager
from config.settings import settings
from pathlib import Path

class RepairManager:
    def __init__(self):
        self.llm = LLMManager()
        self.prompt_path = Path(settings.BASE_DIR) / "prompts" / "repair_prompt.txt"

    def _load_prompt(self):
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def repair_answer(self, answer: str, context: str) -> tuple[str, int]:
        """Intenta corregir una respuesta alucinada usando el contexto."""
        prompt_tmpl = self._load_prompt()
        final_prompt = prompt_tmpl.format(
            answer=answer,
            context=context
        )
        
        try:
            print("🔧 Iniciando ciclo de reparación (Repair Loop)...")
            repaired_answer, tokens = self.llm.call(final_prompt, temperature=0)
            return repaired_answer.strip(), tokens
        except Exception as e:
            print(f"❌ Error en Repair Loop: {e}")
            return "No encontré información suficiente en la base de conocimiento", 0
