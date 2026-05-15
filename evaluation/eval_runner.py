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

    def check_groundedness(self, answer, context) -> tuple[dict, int]:
        prompt_tmpl = self._load_prompt("groundedness_prompt.txt")
        # Escapamos comillas dobles para no romper el prompt que usa "{context}" y "{answer}"
        safe_context = context.replace('"', "'")
        safe_answer = answer.replace('"', "'")
        final_prompt = prompt_tmpl.format(context=safe_context, answer=safe_answer)
        res, tokens = self.llm.call(final_prompt, temperature=0)
        try:
            # Extraer JSON de posibles bloques de código
            if "```json" in res:
                res = res.split("```json")[1].split("```")[0]
            elif "```" in res:
                res = res.split("```")[1].split("```")[0]
            
            clean_json = res.strip()
            data = json.loads(clean_json)
            return {
                "groundedness_score": float(data.get("groundedness_score", 0.0)),
                "status": str(data.get("status", "FAIL")).upper(),
                "reasoning": data.get("reasoning", "")
            }, tokens
        except Exception as e:
            print(f"❌ Error parsing Groundedness JSON: {e} | Res: {res[:100]}...")
            return {"groundedness_score": 0.0, "status": "FAIL", "reasoning": f"JSON Error: {str(e)}"}, tokens

    def get_grading(self, query, answer) -> tuple[dict, int]:
        prompt_tmpl = self._load_prompt("grading_prompt.txt")
        safe_query = query.replace('"', "'")
        safe_answer = answer.replace('"', "'")
        final_prompt = prompt_tmpl.format(query=safe_query, answer=safe_answer)
        res, tokens = self.llm.call(final_prompt, temperature=0)
        try:
            if "```json" in res:
                res = res.split("```json")[1].split("```")[0]
            elif "```" in res:
                res = res.split("```")[1].split("```")[0]
                
            clean_json = res.strip()
            return json.loads(clean_json), tokens
        except Exception as e:
            print(f"❌ Error parsing Grading JSON: {e}")
            return {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0.0}, tokens
