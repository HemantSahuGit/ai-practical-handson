from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def _serialize_cell(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, memoryview)):
        return bytes(value).decode("utf-8", errors="replace")
    return value


async def run_readonly_query(engine: AsyncEngine, sql: str) -> list[dict[str, Any]]:
    async with engine.connect() as conn:
        result = await conn.execute(text(sql))
        columns = list(result.keys())
        rows: list[dict[str, Any]] = []
        for row in result.fetchall():
            rows.append(
                {
                    col: _serialize_cell(row[i])
                    for i, col in enumerate(columns)
                }
            )
        return rows
