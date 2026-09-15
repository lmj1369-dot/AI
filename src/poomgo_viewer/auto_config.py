import json
from pathlib import Path
from typing import Any

from poomgo_viewer.config import Settings

CONFIG_PATH = Path("auto_settings.json")


def load_auto_config(settings: Settings) -> dict[str, Any]:
    config = {"enabled": settings.auto_sync_enabled, "times": settings.auto_sync_times}
    if not CONFIG_PATH.exists():
        return config
    try:
        stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    if isinstance(stored, dict):
        config["enabled"] = bool(stored.get("enabled", config["enabled"]))
        config["times"] = str(stored.get("times", config["times"]))
    return config


def save_auto_config(enabled: bool, times: str) -> dict[str, Any]:
    parsed_times = _validate_times(times)
    config = {"enabled": enabled, "times": ",".join(parsed_times)}
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def _validate_times(times: str) -> list[str]:
    parsed: list[str] = []
    for value in times.split(","):
        hour, minute = (int(part) for part in value.strip().split(":"))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("실행 시각은 HH:MM 형식이어야 합니다.")
        parsed.append(f"{hour:02d}:{minute:02d}")
    if not parsed:
        raise ValueError("실행 시각을 하나 이상 입력해야 합니다.")
    return sorted(set(parsed))
