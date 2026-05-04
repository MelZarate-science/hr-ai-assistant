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

    def check_groundedness(self, answer, context) -> dict:
        """Verifica veracidad usando el prompt de auditoría y devuelve score y status."""
        prompt_tmpl = self._load_prompt("groundedness_prompt.txt")
        final_prompt = prompt_tmpl.format(context=context, answer=answer)
        
        try:
            res = self.llm.call(final_prompt, temperature=0)
            # Limpiar posibles bloques de código Markdown
            clean_json = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Asegurar estructura esperada
            return {
                "groundedness_score": float(data.get("groundedness_score", 0.0)),
                "status": str(data.get("status", "FAIL")).upper(),
                "reasoning": data.get("reasoning", "")
            }
        except Exception as e:
            print(f"❌ Error en Groundedness: {e}")
            return {"groundedness_score": 0.0, "status": "FAIL", "reasoning": str(e)}

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
