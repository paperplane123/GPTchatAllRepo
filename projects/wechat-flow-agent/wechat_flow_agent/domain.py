from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Message:
    id: str
    group: str
    sender: str
    timestamp: str
    text: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int = 0) -> "Message":
        text = str(data.get("text", "")).strip()
        if not text:
            raise ValueError("message.text 不能为空")
        return cls(
            id=str(data.get("id") or f"msg-{index + 1}"),
            group=str(data.get("group") or "未命名群聊"),
            sender=str(data.get("sender") or "未知成员"),
            timestamp=str(data.get("timestamp") or ""),
            text=text,
        )


@dataclass(slots=True)
class ActionItem:
    title: str
    owner: str | None
    deadline: str | None
    source_message_id: str
    confidence: float


@dataclass(slots=True)
class RiskAlert:
    level: str
    title: str
    detail: str
    source_message_id: str


@dataclass(slots=True)
class AnalysisResult:
    overview: str
    highlights: list[str] = field(default_factory=list)
    actions: list[ActionItem] = field(default_factory=list)
    risks: list[RiskAlert] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
