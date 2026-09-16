import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path("logs") / "poomgo_sync.log"
LOG_RETENTION_DAYS = 30
KOREA = timezone(timedelta(hours=9))


def write_execution_log(
    *,
    run_type: str,
    started_at: str,
    status: str,
    range_start: str | None = None,
    range_end: str | None = None,
    fetched_count: int = 0,
    saved_count: int = 0,
    skipped_count: int = 0,
    error_message: str | None = None,
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "run_type": run_type,
        "started_at": started_at,
        "finished_at": datetime.now(KOREA).isoformat(),
        "status": status,
        "range_start": range_start,
        "range_end": range_end,
        "fetched_count": fetched_count,
        "saved_count": saved_count,
        "skipped_count": skipped_count,
        "error_message": error_message,
    }
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    _prune_old_logs()


def read_execution_logs(limit: int = 100) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return list(reversed(records))


def _prune_old_logs() -> None:
    cutoff = datetime.now(KOREA) - timedelta(days=LOG_RETENTION_DAYS)
    kept_lines: list[str] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            timestamp = datetime.fromisoformat(record["started_at"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=KOREA)
            if timestamp >= cutoff:
                kept_lines.append(line)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            kept_lines.append(line)
    LOG_PATH.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""), encoding="utf-8")
