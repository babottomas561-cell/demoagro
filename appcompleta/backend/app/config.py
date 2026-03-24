from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Lemon BI API"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./demoagro.db"

    secret_key: str = "lemon-bi-secret-key-change-in-production-2026"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no", "off"}:
                return False
            if normalized in {"development", "dev", "debug", "true", "1", "yes", "on"}:
                return True
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
