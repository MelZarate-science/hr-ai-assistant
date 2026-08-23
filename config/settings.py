from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

class Settings(BaseSettings):
    # Base Dir
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Database
    DATABASE_URL: str

    # AI Models
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Motor de IA principal
    LLM_ENGINE: str = "google" 
    
    # Modelos de Gemini (Tiered Architecture)
    PRO_MODEL: str = "gemini-2.5-pro"
    FLASH_MODEL: str = "gemini-2.5-flash"
    
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Toggles para ahorrar cuota
    ENABLE_GUARDRAILS: bool = True
    ENABLE_EVALUATION: bool = True

    # RAG Settings
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 150
    # Tope de caracteres del contexto final enviado al LLM de generacion.
    # Protege contra un futuro aumento de top_n de reranking o de CHUNK_SIZE
    # que infle el contexto sin que nadie lo note.
    MAX_CONTEXT_CHARS: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
