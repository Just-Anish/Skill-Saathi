import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env from backend/ or project root
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")

class Settings:
    APP_NAME: str = "SkillSaathi Family Consensus API"
    VERSION: str = "0.1.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./skillsaathi.db")
    
    # CORS: Allow local Vite dev origins
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:4173",
        ).split(",")
        if origin.strip()
    ]

    # AI Provider configuration (Grounded LLM integration)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "5.0"))

settings = Settings()
