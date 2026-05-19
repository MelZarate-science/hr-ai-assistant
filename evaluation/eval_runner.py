import json
from config.settings import settings
from pathlib import Path
from core.llm import LLMManager

class EvalRunner:
    """Asynchronous Auditor for Groundedness and Quality Scoring."""
    def __init__(self):
        self.llm = LLMManager()
        self.prompts_dir = Path(settings.BASE_DIR) / "prompts"

    def _load_prompt(self, filename):
        with open(self.prompts_dir / filename, "r", encoding="utf-8") as f:
            return f.read()

    async def check_groundedness(self, answer: str, context: str) -> tuple[dict, int]:
        """Verifies factuality against provided context."""
        prompt_tmpl = self._load_prompt("groundedness_prompt.txt")
        # Sanitize for prompt injection safety
        safe_context = context.replace('"', "'")
        safe_answer = answer.replace('"', "'")
        final_prompt = prompt_tmpl.format(context=safe_context, answer=safe_answer)
        
        res, tokens = await self.llm.call(final_prompt, temperature=0, use_pro=False)
        try:
            # Robust JSON extraction
            clean_json = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return {
                "groundedness_score": float(data.get("groundedness_score", 0.0)),
                "status": str(data.get("status", "FAIL")).upper(),
                "reasoning": data.get("reasoning", "")
            }, tokens
        except Exception as e:
            print(f"❌ Groundedness Parsing Error: {e}")
            return {"groundedness_score": 0.0, "status": "FAIL", "reasoning": "Parse Error"}, tokens

    async def get_grading(self, query: str, answer: str) -> tuple[dict, int]:
        """Executes LLM-as-a-Judge for UX quality metrics."""
        prompt_tmpl = self._load_prompt("grading_prompt.txt")
        safe_query = query.replace('"', "'")
        safe_answer = answer.replace('"', "'")
        final_prompt = prompt_tmpl.format(query=safe_query, answer=safe_answer)
        
        res, tokens = await self.llm.call(final_prompt, temperature=0, use_pro=False)
        try:
            clean_json = res.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json), tokens
        except Exception as e:
            print(f"❌ Grading Parsing Error: {e}")
            return {"relevance": 0, "clarity": 0, "usefulness": 0, "total_score": 0.0}, tokens
