from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class TaskRequest:
    task: str
    context: str = ""
    constraints: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.task.strip():
            raise ValueError("task cannot be empty")
        if len(self.task) > 20_000:
            raise ValueError("task is too long")
        if len(self.context) > 50_000:
            raise ValueError("context is too long")
        if len(self.constraints) > 50:
            raise ValueError("too many constraints")


@dataclass(slots=True)
class AgentOutput:
    role: str
    summary: str
    reasoning_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.5
    raw: str = ""

    @classmethod
    def from_mapping(cls, role: str, data: dict[str, Any], raw: str = "") -> "AgentOutput":
        confidence = data.get("confidence", 0.5)
        try:
            confidence = min(1.0, max(0.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.5

        return cls(
            role=role,
            summary=str(data.get("summary", "")).strip(),
            reasoning_points=_string_list(data.get("reasoning_points")),
            risks=_string_list(data.get("risks")),
            recommendations=_string_list(data.get("recommendations")),
            confidence=confidence,
            raw=raw,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DecisionResult:
    run_id: str
    task: TaskRequest
    right_brain: AgentOutput
    left_brain: AgentOutput
    arbiter: AgentOutput
    duration_ms: int
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": asdict(self.task),
            "right_brain": self.right_brain.to_dict(),
            "left_brain": self.left_brain.to_dict(),
            "arbiter": self.arbiter.to_dict(),
            "duration_ms": self.duration_ms,
            "mode": self.mode,
        }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]
