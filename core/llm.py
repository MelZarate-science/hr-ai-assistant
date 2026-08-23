import google.generativeai as genai
from config.settings import settings
from pathlib import Path
import asyncio


class LLMError(RuntimeError):
    """Falla de la API de Gemini.

    Se propaga como excepcion en vez de devolver texto: una respuesta de
    error jamas debe poder confundirse con contenido generado. Antes de este
    cambio, "ERROR_CONEXION" viajaba como si fuera una respuesta del modelo,
    llegaba al juez de groundedness (que la marcaba FAIL) y al guardrail
    (que la dejaba pasar, porque no contenia ni PASS ni FAIL).
    """


class LLMManager:
    """Enterprise LLM Manager: Optimized for speed and tiered reasoning."""
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY no configurada.")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Cargamos ambos modelos para usarlos según la complejidad
        self.pro_model = genai.GenerativeModel(f'models/{settings.PRO_MODEL}') # Default Pro
        self.flash_model = genai.GenerativeModel(f'models/{settings.FLASH_MODEL}') # Default Flash

    def _sync_call(self, prompt: str, temperature: float, use_pro: bool):
        model = self.pro_model if use_pro else self.flash_model
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
        return response.text

    async def call(self, prompt: str, temperature: float = 0.0, use_pro: bool = False) -> tuple[str, int]:
        """Llamada asíncrona segura. Por defecto usa FLASH para ahorrar tiempo/costo."""
        input_tokens = int(len(prompt.split()) * 1.5)
        try:
            # Forzamos el uso de hilos para no bloquear el loop de Streamlit
            content = await asyncio.to_thread(self._sync_call, prompt, temperature, use_pro)
            output_tokens = int(len(content.split()) * 1.5)
            return content, input_tokens + output_tokens
        except Exception as e:
            modelo = settings.PRO_MODEL if use_pro else settings.FLASH_MODEL
            print(f"❌ Error Gemini ({'PRO' if use_pro else 'FLASH'}): {e}")
            raise LLMError(f"{modelo}: {e}") from e

    async def rewrite_query(self, query: str, history: list) -> tuple[str, int]:
        prompt_path = Path(settings.BASE_DIR) / "prompts" / "rewriter_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-10:]])
        final_prompt = template.replace("{history}", history_text).replace("{query}", query)
        # Rewriting usa FLASH (velocidad)
        return await self.call(final_prompt, temperature=0.0, use_pro=False)

    async def generate_answer(self, query: str, context: str, history: list = []) -> tuple[str, int]:
        prompt_path = Path(settings.BASE_DIR) / "prompts" / "system_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-10:]])
        final_prompt = template.replace("{history}", history_text).replace("{context}", context).replace("{query}", query)
        # Generación usa FLASH para latencia aceptable (Pro es demasiado lento para UX)
        return await self.call(final_prompt, temperature=0.0, use_pro=False)
