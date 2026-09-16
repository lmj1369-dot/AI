import sys
from pathlib import Path

import httpx
import pytest

from poomgo_viewer.app import resolve_static_dir
from poomgo_viewer.client import PoomgoClient


@pytest.mark.asyncio
async def test_client_sends_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {"queries": []}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["queries"].append(request.url.query.decode())
        page = request.url.params.get("page")
        return httpx.Response(200, json={"page": int(page), "totalPage": 2, "data": [{"invoice": page}]})

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def mocked_client(**kwargs: object) -> httpx.AsyncClient:
        return original_client(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)
    result = await PoomgoClient("secret", "https://example.test/invoice").get_invoices(
        page=1,
        page_size=50,
        closed_at_gte="2026-09-01T00:00:00",
        closed_at_lte="2026-09-14T23:59:59",
    )

    assert captured["authorization"] == "secret"
    assert captured["queries"][0] == (
        "page=1&pageSize=50&closedAtGte=2026-09-01T00%3A00%3A00&"
        "closedAtLte=2026-09-14T23%3A59%3A59"
    )
    assert captured["queries"][1].startswith("page=2&pageSize=50&")
    assert result["data"] == [{"invoice": "1"}, {"invoice": "2"}]
    assert result["rowCount"] == 2


def test_resolve_static_dir_for_pyinstaller_bundle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    static_dir = bundle_dir / "poomgo_viewer" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    assert resolve_static_dir(module_file=tmp_path / "not_used" / "app.py") == static_dir
