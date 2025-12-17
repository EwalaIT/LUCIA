# config.py
from pathlib import Path
from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------
    # Database
    # ------------------
    db_path: Path = Field(
        default=Path("/data/db/lucia.db"),
        description="SQLite database path"
    )

    # ------------------
    # Home Assistant
    # ------------------
    ha_url: AnyUrl = Field(...)
    ha_token: str = Field(...)

    # ------------------
    # LangChain
    # ------------------
    langchain_backend_url: AnyUrl = Field(
        default="http://langchain-backend:8000"
    )

    # ------------------
    # App
    # ------------------
    env: str = "development"
    log_level: str = "INFO"


settings = Settings()
