from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .domain import Message


def load_messages(path: str | Path) -> list[Message]:
    payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("messages", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("输入必须是消息数组，或包含 messages 数组的对象")
    return [Message.from_dict(row, index) for index, row in enumerate(rows)]


def parse_messages(payload: Any) -> list[Message]:
    rows = payload.get("messages", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("messages 必须是数组")
    return [Message.from_dict(row, index) for index, row in enumerate(rows)]
