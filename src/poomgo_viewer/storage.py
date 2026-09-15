from typing import Any

from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

metadata = MetaData()

items_table = Table(
    "poomgo_invoice",
    metadata,
    Column("invoiceId", String(50), nullable=False, index=True),
    Column("invoiceSerial", String(50)),
    Column("code", String(50)),
    Column("expiry", String(100)),
    Column("itemNumber", String(20)),
    Column("name", String(500)),
    Column("optionvalue", String(20)),
    Column("depth", String(11)),
    Column("height", String(11)),
    Column("isGift", String(20)),
    Column("quantity", String(11)),
    Column("weight", String(11)),
    Column("width", String(11)),
    Column("orderid", String(100)),
    Column("channelorderid", String(100)),
    Column("channelname", String(20)),
    Column("status", String(5)),
    Column("createdAt", String(50)),
    Column("closedAt", String(50)),
    Column("procdate", String(20)),
    Column("deptgubun", String(20)),
    Column("courierName", String(500)),
    Column("partnerName", String(500)),
    Column("brandName", String(200)),
    Column("trackingnumber", String(20)),
)


class MariaDbStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("MARIADB_DATABASE_URL이 설정되지 않았습니다.")
        self.engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)

    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

    async def save_page(self, rows: list[dict[str, Any]]) -> tuple[int, int]:
        if not rows:
            return 0, 0
        saved = 0
        skipped = 0
        async with self.engine.begin() as connection:
            for invoice in rows:
                invoice_id = str(invoice.get("invoiceId", ""))
                if not invoice_id:
                    continue
                invoice_items = invoice.get("items") or []
                if not invoice_items:
                    continue
                exists = await connection.scalar(
                    select(items_table.c.invoiceId).where(items_table.c.invoiceId == invoice_id).limit(1)
                )
                if exists:
                    skipped += 1
                    continue
                order = invoice.get("order") or {}
                for item in invoice_items:
                    await connection.execute(
                        items_table.insert().values(
                            invoiceId=invoice_id,
                            invoiceSerial=invoice.get("invoiceSerial"),
                            code=item.get("code"),
                            expiry=item.get("expiry"),
                            itemNumber=item.get("itemNumber"),
                            name=item.get("name"),
                            optionvalue="",
                            depth=_as_text(item.get("depth")),
                            height=_as_text(item.get("height")),
                            isGift=_as_text(item.get("isGift")),
                            quantity=_as_text(item.get("quantity")),
                            weight=_as_text(item.get("weight")),
                            width=_as_text(item.get("width")),
                            orderid=_as_text(order.get("orderId")),
                            channelorderid=order.get("channelOrderId"),
                            channelname=order.get("channelName"),
                            status="N",
                            createdAt=invoice.get("createdAt"),
                            closedAt=invoice.get("closedAt"),
                            procdate=None,
                            deptgubun="40",
                            courierName=invoice.get("courierName"),
                            partnerName=invoice.get("partnerName"),
                            brandName=invoice.get("brandName"),
                            trackingnumber=invoice.get("trackingNumber"),
                        )
                    )
                saved += 1
        return saved, skipped

    async def close(self) -> None:
        await self.engine.dispose()


def _as_text(value: Any) -> str | None:
    return None if value is None else str(value)

