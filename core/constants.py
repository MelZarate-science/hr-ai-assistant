"""Constantes compartidas del dominio.

El mensaje de rechazo vive acá y en un solo lugar. Los prompts, el ciclo de
reparación y la interfaz deben usar exactamente el mismo texto: sin una frase
canónica no hay forma de medir con qué frecuencia el asistente se abstiene
correctamente de responder.
"""

REFUSAL_MESSAGE = "No se encuentra información disponible en los documentos oficiales"


# Estados posibles de una consulta. Existen para poder contarlos: sin ellos,
# una consulta bloqueada por el guardrail era indistinguible de una alucinacion.
STATUS_ANSWERED = "answered"
STATUS_BLOCKED = "blocked"
STATUS_REFUSED = "refused"


def is_refusal(text: str) -> bool:
    """Indica si una respuesta es una abstención del asistente."""
    return REFUSAL_MESSAGE.lower() in (text or "").lower()
