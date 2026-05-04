from groq import Groq
from config.settings import settings
from pathlib import Path

class LLMManager:
    def __init__(self):
        """Inicializa el motor de IA (Groq) según la configuración."""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = settings.GROQ_MODEL

    def call(self, prompt: str, temperature: float = 0.1, model_name: str = None):
        """Hace una llamada directa al LLM con un prompt completo."""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name or self.model_name,
                temperature=temperature,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"❌ Error llamando a GROQ: {e}")
            return "ERROR"

    def rewrite_query(self, query: str, history: list) -> str:
        """
        Usa el SLM (Mini-cerebro) para convertir una pregunta ambigua basada en la historia
        en una consulta independiente y clara para el buscador de vectores.
        """
        if not history:
            return query

        # Construir el contexto de la historia para el SLM
        history_text = ""
        for msg in history[-3:]: # Solo tomamos los últimos 3 mensajes para ahorrar tokens
            role = "Empleado" if msg["role"] == "user" else "Asistente"
            history_text += f"{role}: {msg['content']}\n"

        prompt = f"""
        Eres un experto en reformular consultas para sistemas de búsqueda. 
        Tu tarea es tomar el 'Historial de Chat' y la 'Pregunta Actual' y generar una ÚNICA frase 
        que sea independiente y contenga toda la intención de búsqueda.

        HISTORIAL:
        {history_text}

        PREGUNTA ACTUAL: {query}

        REGLAS:
        1. Responde SOLO con la consulta reformulada.
        2. Si la pregunta ya es clara, no la cambies.
        3. No saludes ni des explicaciones.
        4. Mantén el idioma español.

        CONSULTA REFORMULADA:"""
        
        # Usamos el modelo pequeño (SLM) para esta tarea rápida
        rewritten = self.call(prompt, temperature=0, model_name=settings.SLM_MODEL)
        
        if rewritten == "ERROR" or not rewritten:
            return query
            
        print(f"🔄 Consulta reescrita: '{query}' -> '{rewritten.strip()}'")
        return rewritten.strip()

    def generate_answer(self, query: str, context: str, history: list = []):
        """Lógica específica para el asistente de RRHH con conciencia de contexto conversacional."""
        prompt_path = Path(settings.BASE_DIR) / "prompts" / "system_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
            
        # Formatear la historia para el prompt
        history_text = "Sin historial previo."
        if history:
            history_text = ""
            for msg in history[-5:]: # Aumentamos un poco el contexto histórico
                role = "Empleado" if msg["role"] == "user" else "Asistente"
                history_text += f"{role}: {msg['content']}\n"
            
        final_prompt = template.format(
            history=history_text,
            context=context,
            query=query
        )
        return self.call(final_prompt, temperature=0.1)
