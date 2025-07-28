from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Anonymiseur Juridique RGPD"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
        "http://localhost:9992",
        "http://127.0.0.1:9992"
    ]
    
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "backend"
    ]
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Session settings
    SESSION_EXPIRE_MINUTES: int = 30
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Ollama settings (NOUVEAU)
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    
    # RGPD compliance settings
    RGPD_CONFIG: dict = {
        "data_processing": "local_only",
        "external_apis": False,
        "data_retention": 0,
        "audit_logging": True,
        "user_consent": "explicit"
    }
    
    # Supported file types
    SUPPORTED_FILE_TYPES: List[str] = [".pdf", ".docx"]
    
    class Config:
        env_file = ".env"

settings = Settings()