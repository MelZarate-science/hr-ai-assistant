from core.llm import LLMManager
from config.settings import settings
from pathlib import Path

class GuardrailManager:
    """Security Layer to enforce HR-domain specificity."""
    def __init__(self):
        self.llm = LLMManager()
        self.prompt_path = Path(settings.BASE_DIR) / "prompts" / "guardrail_prompt.txt"

    async def validate_query(self, query: str) -> tuple[bool, int]:
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        res, tokens = await self.llm.call(template.format(query=query), temperature=0, use_pro=False)
        
        # FAIL-OPEN STRATEGY: Solo bloqueamos si el modelo dice explícitamente FAIL.
        # Si hay un error de conexión o respuesta inesperada, dejamos pasar la consulta.
        if "FAIL" in res.upper() and "PASS" not in res.upper():
            print(f"⚠️ Guardrail BLOQUEÓ la consulta: {query}")
            return False, tokens
            
        return True, tokens
