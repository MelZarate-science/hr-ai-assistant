from core.llm import LLMManager, LLMError
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

        try:
            res, tokens = await self.llm.call(template.format(query=query), temperature=0, use_pro=False)
        except LLMError as e:
            # Fail-closed ante un error real de la API: antes, "ERROR_CONEXION"
            # no contenia ni PASS ni FAIL y la consulta pasaba sin control
            # durante cualquier caida de Gemini. La estrategia fail-open sigue
            # aplicando solo a respuestas ambiguas del modelo, no a fallos de
            # infraestructura.
            print(f"❌ Guardrail no disponible, bloqueando por seguridad: {e}")
            return False, 0

        # FAIL-OPEN STRATEGY: Solo bloqueamos si el modelo dice explícitamente FAIL.
        # Si la respuesta es ambigua, dejamos pasar la consulta.
        if "FAIL" in res.upper() and "PASS" not in res.upper():
            print(f"⚠️ Guardrail BLOQUEÓ la consulta: {query}")
            return False, tokens

        return True, tokens
