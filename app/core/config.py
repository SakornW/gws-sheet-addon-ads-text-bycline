import os
from typing import Optional  # Added Optional import

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Ads Text Generator"
    API_V1_STR: str = "/api/v1"

    # Database settings
    DATABASE_URL: PostgresDsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/adstext")

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Google Gemini API settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Google Workspace Add-on / GCP settings
    GCP_OAUTH_CLIENT_ID: Optional[str] = os.getenv("GCP_OAUTH_CLIENT_ID")
    SERVICE_ACCOUNT_EMAIL: Optional[str] = os.getenv("SERVICE_ACCOUNT_EMAIL")

    # Web scraping settings
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    SCRAPING_TIMEOUT: int = 30  # seconds
    MAX_RETRIES: int = 3

    # RAG settings
    VECTOR_DIMENSION: int = 768
    SIMILARITY_THRESHOLD: float = 0.7

    # Ad generation settings
    DEFAULT_MAX_LENGTH: int = 150
    DEFAULT_TONE: str = "Professional"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
