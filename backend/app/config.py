from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pokemontcg_api_key: str = ""
    database_url: str = "sqlite:///cardfolio.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
