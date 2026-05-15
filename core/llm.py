from groq import Groq
from config.settings import settings
from pathlib import Path

class LLMManager:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = settings.GROQ_MODEL

    def call(self, prompt: str, temperature: float = 0.0, model_name: str = None) -> tuple[str, int]:
        target_model = model_name or self.model_name
        input_tokens = int(len(prompt.split()) * 1.3)
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=target_model,
                temperature=temperature,
            )
            content = chat_completion.choices[0].message.content
            output_tokens = int(len(content.split()) * 1.3)
            return content, input_tokens + output_tokens
        except Exception as e:
            if "429" in str(e) and target_model != settings.SLM_MODEL:
                print(f"⚠️ FALLBACK: {target_model} limitado. Usando {settings.SLM_MODEL}...")
                return self.call(prompt, 0.0, settings.SLM_MODEL)
            print(f"❌ Error GROQ ({target_model}): {e}")
            return "ERROR", 0

    def rewrite_query(self, query: str, history: list) -> tuple[str, int]:
        if not history: return query, 0
        
        prompt_path = Path(settings.BASE_DIR) / "prompts" / "rewriter_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
            
        history_text = "\n".join([f"{'User' if m['role']=='user' else 'AI'}: {m['content'][:200]}..." for m in history[-3:]])
        final_prompt = template.format(history=history_text or "Sin historial", query=query)
        
        return self.call(final_prompt, temperature=0.0, model_name=settings.SLM_MODEL)

    def generate_answer(self, query: str, context: str, history: list = []) -> tuple[str, int]:
        prompt_path = Path(settings.BASE_DIR) / "prompts" / "system_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
        history_text = "\n".join([f"{'User' if m['role']=='user' else 'AI'}: {m['content']}" for m in history[-3:]])
        final_prompt = template.format(history=history_text or "Sin historial", context=context, query=query)
        return self.call(final_prompt, temperature=0.0)
