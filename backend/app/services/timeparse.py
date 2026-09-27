"""Parse user-entered arrival times; reject empty or unparseable input."""
from __future__ import annotations
from datetime import datetime


def parse_actual_arrive(raw: object) -> datetime:
    """Parse an arrival-time string into a naive datetime.

    Accepts ISO 8601 forms such as "2026-09-17 07:08", "2026-09-17T07:08:00".
    Raises ValueError for empty/blank or unparseable input.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("到站时刻不能为空")
    text = raw.strip()
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"无法解析的到站时刻: {text}") from None
    if value.tzinfo is not None:
        # 站内数据均为本地墙钟时间，忽略时区标记
        value = value.replace(tzinfo=None)
    return value
