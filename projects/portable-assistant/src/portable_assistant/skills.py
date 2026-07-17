from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SkillError(RuntimeError):
    """Raised when a requested local skill cannot be loaded safely."""


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    title: str
    content: str


def discover_skills(root: str | Path) -> list[Skill]:
    skills_root = Path(root)
    if not skills_root.exists():
        return []

    discovered: list[Skill] = []
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        content = skill_file.read_text(encoding="utf-8")
        title = skill_file.parent.name
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip() or title
                break
        discovered.append(
            Skill(
                name=skill_file.parent.name,
                path=skill_file,
                title=title,
                content=content.strip(),
            )
        )
    return discovered


def load_skills(root: str | Path, names: list[str]) -> list[Skill]:
    available = {skill.name: skill for skill in discover_skills(root)}
    loaded: list[Skill] = []
    for name in names:
        if name not in available:
            options = ", ".join(sorted(available)) or "none"
            raise SkillError(f"Skill '{name}' not found. Available skills: {options}.")
        loaded.append(available[name])
    return loaded


def render_skill_context(skills: list[Skill]) -> str:
    if not skills:
        return ""
    sections = ["# Explicitly loaded local skills"]
    for skill in skills:
        sections.append(f"\n## Skill: {skill.name}\n{skill.content}")
    return "\n".join(sections)
