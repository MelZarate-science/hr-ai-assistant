import json
from config.settings import settings
from pathlib import Path
from core.llm import LLMManager

class EvalRunner:
    def __init__(self):
        self.llm = LLMManager()
        self.prompts_dir = Path(settings.BASE_DIR) / "prompts"

    def _load_prompt(self, filename):
        with open(self.prompts_dir / filename, "r", encoding="utf-8") as f:
            return f.read()

    def check_groundedness(self, answer, context) -> bool:
        """Verifica veracidad usando el prompt de auditoría."""
        prompt_tmpl = self._load_prompt("groundedness_prompt.txt")
        final_prompt = prompt_tmpl.format(context=context, answer=answer)
        
        try:
            res = self.llm.call(final_prompt, temperature=0)
            return "PASS" in res.upper()
        except Exception as e:
            print(f"❌ Error en Groundedness: {e}")
            return False

    def get_grading(self, query, answer) -> dict:
        """Califica la calidad usando el prompt de grading."""
        prompt_tmpl = self._load_prompt("grading_prompt.txt")
        final_prompt = prompt_tmpl.format(query=query, answer=answer)
        
        try:
            res = self.llm.call(final_prompt, temperature=0)
            clean_json = res.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            print(f"❌ Error en Grading: {e}")
            return {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0}
