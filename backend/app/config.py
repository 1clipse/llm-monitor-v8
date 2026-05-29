from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DATABASE_URL = f"sqlite:///{(DATA_DIR / 'llm_monitor.db').as_posix()}"


class Settings(BaseSettings):
    app_name: str = "LLM Monitor v8"
    environment: str = "local"
    database_url: str = DEFAULT_DATABASE_URL
    auth_enabled: bool = False
    jwt_secret: str = "change-me-in-production"
    relay_config_path: Path = DATA_DIR / "relays.json"
    mock_latency_ms: int = 120
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    risk_high_threshold: float = 0.72
    risk_medium_threshold: float = 0.42

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
