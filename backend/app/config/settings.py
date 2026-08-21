import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "recovr_db"
    ANTHROPIC_API_KEY: str = "mock-key-for-now"

    # Read from .env file in the backend directory
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
