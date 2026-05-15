from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from config.settings import settings

class EmbeddingManager:
    def __init__(self):
        """Inicializa el modelo de HuggingFace configurado."""
        self.model_name = settings.EMBEDDING_MODEL
        # El modelo se descarga la primera vez y luego se usa localmente
        self.model = SentenceTransformer(self.model_name)
        print(f"✅ Modelo de embeddings cargado: {self.model_name}")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Convierte una lista de textos en una lista de vectores (embeddings).
        Aplica normalización L2 para permitir búsquedas eficientes por Producto Punto.
        """
        try:
            embeddings = self.model.encode(texts)
            # Normalización L2: cada vector tendrá longitud 1
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            normalized_embeddings = embeddings / norms
            return normalized_embeddings.tolist()
        except Exception as e:
            print(f"❌ Error generando embeddings: {e}")
            return []

    def generate_single_embedding(self, text: str) -> List[float]:
        """Genera el vector para un solo texto (útil para consultas)."""
        return self.generate_embeddings([text])[0]
