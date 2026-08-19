from core.llm import LLMManager, LLMError
from config.settings import settings
from pathlib import Path

class RepairManager:
    """Self-healing component for hallucinatory or ungrounded responses."""
    def __init__(self):
        self.llm = LLMManager()
        self.prompt_path = Path(settings.BASE_DIR) / "prompts" / "repair_prompt.txt"

    async def repair_answer(self, answer: str, context: str) -> tuple[str, int]:
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # PRO tier required for precise healing.
        # Si Gemini falla aca no hay texto reparado que devolver: se re-lanza
        # y el orquestador decide (antes, "ERROR_CONEXION" se mostraba al
        # usuario como si fuera la respuesta corregida).
        res, tokens = await self.llm.call(
            template.format(answer=answer, context=context),
            temperature=0,
            use_pro=True
        )
        return res.strip(), tokens
