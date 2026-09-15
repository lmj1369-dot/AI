import json
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from poomgo_viewer.config import Settings

CONFIG_PATH = Path("db_settings.json")


def load_db_config(settings: Settings) -> dict[str, Any]:
    config = {"host": "", "port": 3306, "database": "", "username": "", "has_password": False}
    if settings.mariadb_database_url:
        parsed = make_url(settings.mariadb_database_url)
        config.update({
            "host": parsed.host or "",
            "port": parsed.port or 3306,
            "database": parsed.database or "",
            "username": parsed.username or "",
            "has_password": bool(parsed.password),
        })
    if not CONFIG_PATH.exists():
        return config
    try:
        stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    if isinstance(stored, dict):
        config.update({key: stored[key] for key in ("host", "port", "database", "username") if key in stored})
        config["has_password"] = bool(stored.get("password"))
    return config


def get_database_url(settings: Settings) -> str:
    if CONFIG_PATH.exists():
        try:
            stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if stored.get("host") and stored.get("database") and stored.get("username") and stored.get("password"):
                return build_database_url(stored)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
    return settings.mariadb_database_url


def save_db_config(values: dict[str, Any]) -> dict[str, Any]:
    required = ("host", "port", "database", "username")
    if any(not str(values.get(key, "")).strip() for key in required):
        raise ValueError("호스트, 포트, 데이터베이스, 사용자명은 필수입니다.")
    port = int(values["port"])
    if not 1 <= port <= 65535:
        raise ValueError("포트는 1부터 65535 사이여야 합니다.")
    existing_password = ""
    if CONFIG_PATH.exists():
        try:
            existing_password = str(json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("password", ""))
        except (OSError, json.JSONDecodeError):
            pass
    password = str(values.get("password") or existing_password)
    if not password:
        raise ValueError("비밀번호를 입력해야 합니다.")
    stored = {"host": str(values["host"]).strip(), "port": port, "database": str(values["database"]).strip(), "username": str(values["username"]).strip(), "password": password}
    CONFIG_PATH.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"host": stored["host"], "port": stored["port"], "database": stored["database"], "username": stored["username"], "has_password": True}


def build_database_url(values: dict[str, Any]) -> str:
    return "mariadb+aiomysql://{}:{}@{}:{}/{}".format(
        quote_plus(str(values["username"])),
        quote_plus(str(values["password"])),
        values["host"],
        int(values["port"]),
        quote_plus(str(values["database"])),
    )


async def test_db_connection(values: dict[str, Any], settings: Settings) -> None:
    password = str(values.get("password") or "")
    if not password and CONFIG_PATH.exists():
        try:
            password = str(json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("password", ""))
        except (OSError, json.JSONDecodeError):
            pass
    test_values = {**values, "password": password}
    if not password:
        fallback = get_database_url(settings)
        if fallback:
            database_url = fallback
        else:
            raise ValueError("비밀번호를 입력해야 합니다.")
    else:
        database_url = build_database_url(test_values)
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()
