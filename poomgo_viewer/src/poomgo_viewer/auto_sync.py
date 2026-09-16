import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone

from poomgo_viewer.client import PoomgoClient
from poomgo_viewer.auto_config import load_auto_config
from poomgo_viewer.db_config import get_database_url
from poomgo_viewer.config import Settings
from poomgo_viewer.storage import MariaDbStore
from poomgo_viewer.local_log import write_execution_log

logger = logging.getLogger(__name__)
KOREA = timezone(timedelta(hours=9))


async def run_scheduled_sync(settings: Settings) -> None:
    last_slot: str | None = None
    while True:
        now = datetime.now(KOREA)
        config = load_auto_config(settings)
        slot = now.strftime("%Y-%m-%d %H:%M")
        if config["enabled"] and now.strftime("%H:%M") in config["times"].split(",") and slot != last_slot:
            last_slot = slot
            try:
                await sync_two_days_ago(settings)
            except Exception:
                logger.exception("품고 자동 저장에 실패했습니다.")
        await asyncio.sleep(20)


def next_run_time(now: datetime, schedule: str) -> datetime:
    times = sorted(_parse_times(schedule))
    for scheduled_time in times:
        candidate = now.replace(hour=scheduled_time.hour, minute=scheduled_time.minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, times[0], tzinfo=KOREA)


async def sync_two_days_ago(settings: Settings) -> tuple[int, int]:
    database_url = get_database_url(settings)
    if not database_url:
        logger.warning("MARIADB_DATABASE_URL이 없어 자동 저장을 건너뜁니다.")
        return 0, 0

    today = datetime.now(KOREA).date()
    start_date = today - timedelta(days=3)
    end_date = today - timedelta(days=2)
    client = PoomgoClient(settings.poomgo_api_key, settings.poomgo_api_url, settings.poomgo_timeout_seconds)
    store = MariaDbStore(database_url)
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": settings.poomgo_api_key}
    params: list[tuple[str, str | int]] = [
        ("page", 1),
        ("pageSize", 20),
        ("closedAtGte", korea_midnight_utc(start_date)),
        ("closedAtLte", korea_midnight_utc(end_date)),
    ]
    saved = 0
    skipped = 0
    fetched = 0
    started_at = datetime.now(KOREA).isoformat()
    range_start = korea_midnight_utc(start_date)
    range_end = korea_midnight_utc(end_date)
    try:
        async for _, _, payload in client.iter_invoice_pages(headers=headers, params=params, page=1):
            rows = payload.get("data", [])
            fetched += len(rows)
            page_saved, page_skipped = await store.save_page(rows)
            saved += page_saved
            skipped += page_skipped
        write_execution_log(
            run_type="auto",
            started_at=started_at,
            status="success",
            range_start=range_start,
            range_end=range_end,
            fetched_count=fetched,
            saved_count=saved,
            skipped_count=skipped,
        )
        logger.info("품고 자동 저장 완료: %s ~ %s, 저장 %d건, 중복 %d건", start_date, end_date, saved, skipped)
        return saved, skipped
    except Exception as error:
        try:
            write_execution_log(
                run_type="auto",
                started_at=started_at,
                status="failed",
                range_start=range_start,
                range_end=range_end,
                fetched_count=fetched,
                saved_count=saved,
                skipped_count=skipped,
                error_message=str(error),
            )
        finally:
            raise
    finally:
        await store.close()


def korea_midnight_utc(value: date) -> str:
    local_midnight = datetime.combine(value, time.min, tzinfo=KOREA)
    return local_midnight.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_times(schedule: str) -> list[time]:
    parsed = []
    for value in schedule.split(","):
        hour, minute = (int(part) for part in value.strip().split(":"))
        parsed.append(time(hour=hour, minute=minute))
    if not parsed:
        raise ValueError("AUTO_SYNC_TIMES가 비어 있습니다.")
    return parsed
