from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pokemontcg_api_key: str = ""
    database_url: str = "sqlite:///cardfolio.db"
    enable_scheduler: bool = True
    refresh_interval_hours: int = 24
    warm_store_on_startup: bool = True
    # Optional. Empty, or an unreachable server, means searches run uncached.
    redis_url: str = "redis://localhost:6380/0"
    search_cache_ttl_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
