import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_env_path() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys.executable).resolve().parent / ".env"
    return Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    nims_api_key: str = ""
    nims_api_url: str = "https://www.nims.or.kr/api/bsshinfo_st_v1.do"
    nims_timeout_seconds: float = 15.0
    server_port: int = 8010

    model_config = SettingsConfigDict(env_file=str(resolve_env_path()), env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
