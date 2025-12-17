# config.py
from pathlib import Path
from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings loaded from environment variables or .env file.
    Compatible with Pydantic v2+ (pydantic-settings).
    """

    # ------------------
    # Pydantic Settings
    # ------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------
    # Database (SQLite)
    # ------------------
    db_path: Path = Field(
        default=Path("/data/db/lucia.db"),
        description="Path to SQLite database file"
    )

    # ------------------
    # Ollama / LLM
    # ------------------
    ollama_url: AnyUrl = Field(
        ...,
        description="Base URL for Ollama server"
    )
    ollama_model: str = Field(
        ...,
        description="Ollama model name"
    )

    # ------------------
    # Home Assistant
    # ------------------
    ha_url: AnyUrl = Field(
        ...,
        description="Home Assistant base URL"
    )
    ha_token: str = Field(
        ...,
        description="Home Assistant long-lived access token"
    )

    # ------------------
    # Agent Scheduling
    # ------------------
    monitor_interval_seconds: int = Field(
        default=300,
        ge=10,
        description="Monitoring loop interval in seconds"
    )

    decisor_interval: int = Field(
        default=300,
        ge=10,
        description="Decisor agent execution interval"
    )

    # ------------------
    # Application Meta
    # ------------------
    env: str = Field(
        default="development",
        description="Execution environment"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )


# Singleton
settings = Settings()
