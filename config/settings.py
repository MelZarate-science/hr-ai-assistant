from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

class Settings(BaseSettings):
    # Base Dir
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Database
    DATABASE_URL: str

    # AI Models
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Motor de IA (Preferimos Gemini ahora)
    LLM_ENGINE: str = "google" 
    
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    SLM_MODEL: str = "llama-3.1-8b-instant"
    
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Toggles para ahorrar cuota
    ENABLE_GUARDRAILS: bool = True
    ENABLE_EVALUATION: bool = True

    # RAG Settings
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 150
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
