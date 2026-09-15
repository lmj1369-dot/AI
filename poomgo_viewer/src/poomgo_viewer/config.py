from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    poomgo_api_key: str
    poomgo_api_url: str = "https://api.poomgo.com/open-api/invoice"
    poomgo_timeout_seconds: float = 20.0
    mariadb_database_url: str = ""
    auto_sync_enabled: bool = True
    auto_sync_times: str = "08:00,18:00"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
