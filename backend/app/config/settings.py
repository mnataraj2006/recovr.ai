import os
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "recovr_db"
    ANTHROPIC_API_KEY: str = "mock-key-for-now"
    JWT_SECRET: str = "dev-jwt-secret-key-recovr-change-in-production-12345"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    WEBHOOK_SECRET: str = "dev-webhook-secret-key-recovr-change-in-production-12345"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    RATE_LIMIT_PER_MINUTE: int = 120

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENVIRONMENT.lower() == "production":
            if "localhost" in self.MONGO_URI or "127.0.0.1" in self.MONGO_URI:
                raise ValueError("Production ENVIRONMENT cannot use localhost MONGO_URI.")
            if "dev-jwt-secret" in self.JWT_SECRET:
                raise ValueError("Production ENVIRONMENT must configure a secure JWT_SECRET.")
            if "dev-webhook-secret" in self.WEBHOOK_SECRET:
                raise ValueError("Production ENVIRONMENT must configure a secure WEBHOOK_SECRET.")
            if self.ANTHROPIC_API_KEY == "mock-key-for-now" or not self.ANTHROPIC_API_KEY:
                raise ValueError("Production ENVIRONMENT must provide a valid ANTHROPIC_API_KEY.")
        return self

    # Read from .env file in the backend directory
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

