# config.py
from pathlib import Path
from pydantic import AnyUrl
from typing import Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Global application settings loaded from environment variables or .env file.
    Compatible with Pydantic v2+ (using pydantic-settings).
    """

    # === Model Configuration ===
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # allows HA_URL or ha_url
        extra="ignore"  # ignore undeclared env vars silently
    )

    # === Database ===
    db_path: Path = Path("./db/agent_memory.db")

    # === LangSmith ===
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    langsmith_endpoint: str | None = None
    langsmith_output_dir: Path = Path("./langsmith_logs")

    # === Ollama / LLM ===
    # Use AnyUrl if always valid URLs, or str if local dev may use placeholder values
    ollama_url: AnyUrl | None = None
    ollama_model: str | None = None

    # === Home Assistant ===
    ha_url: AnyUrl  # required, ensures valid scheme+host
    ha_token: str   # required, secret token
    
    monitor_interval_seconds: int = 300
    
    decisor_interval: int = 300

    # === Application Meta ===
    env: str = "development"
    log_level: str = "INFO"


# Singleton instance accessible throughout the app
settings = Settings()
