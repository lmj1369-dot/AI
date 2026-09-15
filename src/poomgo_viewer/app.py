import json
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pydantic import BaseModel
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from poomgo_viewer.client import PoomgoClient
from poomgo_viewer.auto_config import load_auto_config, save_auto_config
from poomgo_viewer.db_config import get_database_url, load_db_config, save_db_config, test_db_connection
from poomgo_viewer.config import get_settings
from poomgo_viewer.storage import MariaDbStore
from poomgo_viewer.local_log import read_execution_logs, write_execution_log
from poomgo_viewer.auto_sync import run_scheduled_sync



@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    task = None
    if settings.auto_sync_enabled:
        task = asyncio.create_task(run_scheduled_sync(settings))
    try:
        yield
    finally:
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="Poomgo API Viewer", lifespan=lifespan)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AutoSettingsUpdate(BaseModel):
    enabled: bool
    times: str


class DbSettingsUpdate(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str = ""


class InvoiceSaveRequest(BaseModel):
    rows: list[dict[str, Any]]


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/settings/auto")
async def get_auto_settings() -> dict[str, Any]:
    return load_auto_config(get_settings())


@app.put("/api/settings/auto")
async def update_auto_settings(update: AutoSettingsUpdate) -> dict[str, Any]:
    try:
        return save_auto_config(update.enabled, update.times)
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/settings/database")
async def get_database_settings() -> dict[str, Any]:
    return load_db_config(get_settings())


@app.get("/api/logs")
async def get_logs() -> list[dict[str, Any]]:
    return read_execution_logs()


@app.put("/api/settings/database")
async def update_database_settings(update: DbSettingsUpdate) -> dict[str, Any]:
    try:
        return save_db_config(update.model_dump())
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/settings/database/test")
async def test_database_settings(update: DbSettingsUpdate) -> dict[str, str]:
    try:
        await test_db_connection(update.model_dump(), get_settings())
        return {"status": "ok", "message": "MariaDB 접속에 성공했습니다."}
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"MariaDB 접속 실패: {error}") from error


@app.post("/api/invoices/save")
async def save_invoices(request: InvoiceSaveRequest) -> dict[str, int]:
    settings = get_settings()
    started_at = datetime.now(timezone.utc).isoformat()
    store = None
    try:
        store = MariaDbStore(get_database_url(settings))
        await store.initialize()
        saved, skipped = await store.save_page(request.rows)
        write_execution_log(
            run_type="manual",
            started_at=started_at,
            status="success",
            fetched_count=len(request.rows),
            saved_count=saved,
            skipped_count=skipped,
        )
        return {"saved": saved, "skipped": skipped}
    except Exception as error:
        if store is not None:
            try:
                write_execution_log(
                    run_type="manual",
                    started_at=started_at,
                    status="failed",
                    fetched_count=len(request.rows),
                    error_message=str(error),
                )
            except Exception:
                pass
        raise HTTPException(status_code=502, detail=f"DB 저장 실패: {error}") from error
    finally:
        if store is not None:
            await store.close()


@app.get("/api/invoices")
async def invoices(
    closed_at_gte: str | None = Query(None, alias="closedAtGte"),
    closed_at_lte: str | None = Query(None, alias="closedAtLte"),
) -> Any:
    settings = get_settings()
    try:
        client = PoomgoClient(
            settings.poomgo_api_key,
            settings.poomgo_api_url,
            settings.poomgo_timeout_seconds,
        )
        return await client.get_invoices(
            page=1,
            page_size=20,
            closed_at_gte=closed_at_gte,
            closed_at_lte=closed_at_lte,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"품고 API 호출 실패: {error}") from error


@app.get("/api/invoices/stream")
async def invoice_stream(
    closed_at_gte: str | None = Query(None, alias="closedAtGte"),
    closed_at_lte: str | None = Query(None, alias="closedAtLte"),
) -> StreamingResponse:
    settings = get_settings()
    client = PoomgoClient(settings.poomgo_api_key, settings.poomgo_api_url, settings.poomgo_timeout_seconds)
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": settings.poomgo_api_key}
    params: list[tuple[str, str | int]] = [("page", 1), ("pageSize", 20)]
    if closed_at_gte:
        params.append(("closedAtGte", closed_at_gte))
    if closed_at_lte:
        params.append(("closedAtLte", closed_at_lte))

    async def events():
        async for page, total_page, payload in client.iter_invoice_pages(headers=headers, params=params, page=1):
            yield json.dumps({"page": page, "totalPage": total_page, "total": payload.get("total"), "data": payload.get("data", [])}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


def main() -> None:
    import uvicorn

    uvicorn.run("poomgo_viewer.app:app", host="127.0.0.1", port=8000)
