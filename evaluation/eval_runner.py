import json
from config.settings import settings
from pathlib import Path
from core.llm import LLMManager, LLMError

class EvalRunner:
    """Asynchronous Auditor for Groundedness and Quality Scoring."""
    def __init__(self):
        self.llm = LLMManager()
        self.prompts_dir = Path(settings.BASE_DIR) / "prompts"

    def _load_prompt(self, filename):
        with open(self.prompts_dir / filename, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _unmeasured(motivo: str) -> dict:
        """Resultado sin veredicto: la auditoria no llego a ejecutarse.

        Se distingue de FAIL a proposito. Un fallo de API o de parseo es un
        problema de infraestructura, no una alucinacion del modelo, y no debe
        disparar el repair loop ni contarse como falta de veracidad.
        """
        return {"groundedness_score": None, "status": "UNMEASURED", "reasoning": motivo}

    async def check_groundedness(self, answer: str, context: str) -> tuple[dict, int]:
        """Verifies factuality against provided context."""
        prompt_tmpl = self._load_prompt("groundedness_prompt.txt")
        # Sanitize for prompt injection safety
        safe_context = context.replace('"', "'")
        safe_answer = answer.replace('"', "'")
        final_prompt = prompt_tmpl.format(context=safe_context, answer=safe_answer)

        try:
            res, tokens = await self.llm.call(final_prompt, temperature=0, use_pro=False)
        except LLMError as e:
            print(f"❌ Groundedness no disponible: {e}")
            return self._unmeasured(f"Auditoria no disponible: {e}"), 0

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
            return self._unmeasured(f"Error de formato en la respuesta del juez: {e}"), tokens

    async def get_grading(self, query: str, answer: str) -> tuple[dict, int]:
        """Executes LLM-as-a-Judge for UX quality metrics."""
        prompt_tmpl = self._load_prompt("grading_prompt.txt")
        safe_query = query.replace('"', "'")
        safe_answer = answer.replace('"', "'")
        final_prompt = prompt_tmpl.format(query=safe_query, answer=safe_answer)

        try:
            res, tokens = await self.llm.call(final_prompt, temperature=0, use_pro=False)
        except LLMError as e:
            print(f"❌ Grading no disponible: {e}")
            return None, 0

        try:
            clean_json = res.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json), tokens
        except Exception as e:
            print(f"❌ Grading Parsing Error: {e}")
            return None, tokens
