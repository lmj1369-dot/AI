from collections.abc import AsyncIterator
from typing import Any

import httpx


class PoomgoClient:
    def __init__(self, api_key: str, api_url: str, timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    async def get_invoices(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        closed_at_gte: str | None = None,
        closed_at_lte: str | None = None,
    ) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.api_key,
        }
        params: list[tuple[str, str | int]] = [
            ("page", page),
            ("pageSize", page_size),
        ]
        if closed_at_gte:
            params.append(("closedAtGte", closed_at_gte))
        if closed_at_lte:
            params.append(("closedAtLte", closed_at_lte))
        all_rows: list[Any] = []
        first_payload: dict[str, Any] | None = None
        async for _, _, payload in self.iter_invoice_pages(
            headers=headers,
            params=params,
            page=page,
        ):
            if first_payload is None:
                first_payload = payload
            all_rows.extend(payload.get("data", []))

        if first_payload is None:
            return {}

        result = dict(first_payload)
        result["data"] = all_rows
        result["rowCount"] = len(all_rows)
        return result

    async def iter_invoice_pages(
        self,
        *,
        headers: dict[str, str],
        params: list[tuple[str, str | int]],
        page: int,
    ) -> AsyncIterator[tuple[int, int, dict[str, Any]]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            current_page = page
            while True:
                page_params = [(key, current_page if key == "page" else value) for key, value in params]
                response = await client.get(self.api_url, headers=headers, params=page_params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    yield current_page, 1, {"data": payload if isinstance(payload, list) else []}
                    return
                total_page = _positive_int(payload.get("totalPage"), current_page)
                yield current_page, total_page, payload
                if current_page >= total_page or not isinstance(payload.get("data"), list):
                    return
                current_page += 1


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
