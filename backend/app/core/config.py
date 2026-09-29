from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ScrapePulse Lead Engine"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str = "sqlite:///./database/lisesca.db"
    api_prefix: str = "/api"
    browser_headless: bool = False
    browser_user_data_dir: str = "./database/browser_profile"
    browser_cdp_url: str | None = None
    browser_timeout_ms: int = 30000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()