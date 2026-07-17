from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


_ALLOWED_STATUSES = {"draft", "confirmed", "archived"}


class MemoryError(RuntimeError):
    """Raised when a memory store cannot be read or updated safely."""


@dataclass(frozen=True)
class MemoryItem:
    id: str
    created_at: str
    updated_at: str
    kind: str
    title: str
    content: str
    tags: tuple[str, ...]
    status: str = "draft"

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MemoryItem":
        tags = data.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise MemoryError("Memory item tags must be a string array.")
        status = str(data.get("status", "draft"))
        if status not in _ALLOWED_STATUSES:
            raise MemoryError(f"Unsupported memory status: {status}")
        return cls(
            id=str(data["id"]),
            created_at=str(data["created_at"]),
            updated_at=str(data.get("updated_at", data["created_at"])),
            kind=str(data.get("kind", "note")),
            title=str(data.get("title", "Untitled")),
            content=str(data["content"]),
            tags=tuple(tags),
            status=status,
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data


class MemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def load(self) -> list[MemoryItem]:
        if not self.path.exists():
            return []

        items: list[MemoryItem] = []
        for line_number, raw_line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise MemoryError("Memory line is not a JSON object.")
                items.append(MemoryItem.from_dict(data))
            except (json.JSONDecodeError, KeyError, MemoryError) as exc:
                raise MemoryError(
                    f"Invalid memory data at {self.path}:{line_number}: {exc}"
                ) from exc
        return items

    def add(
        self,
        content: str,
        *,
        title: str = "Untitled",
        kind: str = "note",
        tags: Iterable[str] = (),
        status: str = "draft",
    ) -> MemoryItem:
        cleaned = content.strip()
        if not cleaned:
            raise MemoryError("Memory content must not be empty.")
        if status not in _ALLOWED_STATUSES:
            raise MemoryError(f"Unsupported memory status: {status}")

        now = self._now()
        normalized_tags = tuple(
            sorted({tag.strip() for tag in tags if tag and tag.strip()})
        )
        item = MemoryItem(
            id=uuid.uuid4().hex,
            created_at=now,
            updated_at=now,
            kind=kind.strip() or "note",
            title=title.strip() or "Untitled",
            content=cleaned,
            tags=normalized_tags,
            status=status,
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return item

    def set_status(self, memory_id: str, status: str) -> MemoryItem:
        if status not in _ALLOWED_STATUSES:
            raise MemoryError(f"Unsupported memory status: {status}")

        items = self.load()
        updated: MemoryItem | None = None
        rewritten: list[MemoryItem] = []
        for item in items:
            if item.id == memory_id:
                updated = MemoryItem(
                    id=item.id,
                    created_at=item.created_at,
                    updated_at=self._now(),
                    kind=item.kind,
                    title=item.title,
                    content=item.content,
                    tags=item.tags,
                    status=status,
                )
                rewritten.append(updated)
            else:
                rewritten.append(item)

        if updated is None:
            raise MemoryError(f"Memory id not found: {memory_id}")
        self._rewrite(rewritten)
        return updated

    def _rewrite(self, items: list[MemoryItem]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                for item in items:
                    handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(self.path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def recent_confirmed(self, limit: int) -> list[MemoryItem]:
        if limit < 1:
            return []
        confirmed = [item for item in self.load() if item.status == "confirmed"]
        return confirmed[-limit:]

    def export_markdown(self, status: str | None = None) -> str:
        items = self.load()
        if status is not None:
            if status not in _ALLOWED_STATUSES:
                raise MemoryError(f"Unsupported memory status: {status}")
            items = [item for item in items if item.status == status]

        lines = [
            "# Portable Assistant Memory Export",
            "",
            "> This file contains user-owned context, not hidden model reasoning.",
            "",
        ]
        if not items:
            lines.append("No matching memory items.")
            return "\n".join(lines) + "\n"

        for item in items:
            lines.extend(
                [
                    f"## {item.title}",
                    "",
                    f"- ID: `{item.id}`",
                    f"- Status: `{item.status}`",
                    f"- Kind: `{item.kind}`",
                    f"- Created: `{item.created_at}`",
                    f"- Updated: `{item.updated_at}`",
                    f"- Tags: {', '.join(item.tags) if item.tags else 'none'}",
                    "",
                    item.content,
                    "",
                ]
            )
        return "\n".join(lines)


def render_memory_context(items: list[MemoryItem]) -> str:
    if not items:
        return ""
    sections = [
        "# Confirmed user-owned memory",
        "Use these notes as revisable context, not unquestionable truth.",
    ]
    for item in items:
        tags = f" [{', '.join(item.tags)}]" if item.tags else ""
        sections.append(f"\n## {item.title}{tags}\n{item.content}")
    return "\n".join(sections)
