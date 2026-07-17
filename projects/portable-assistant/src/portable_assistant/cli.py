from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .config import AppConfig, ConfigError, load_config
from .memory import MemoryError, MemoryStore, render_memory_context
from .providers import ChatMessage
from .router import AllProvidersFailedError, ProviderRouter
from .skills import SkillError, discover_skills, load_skills, render_skill_context


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pa",
        description="User-owned multi-provider assistant control layer.",
    )
    parser.add_argument(
        "--config",
        default="config.local.json",
        help="Path to local JSON configuration (default: config.local.json).",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Configuration profile name; defaults to config.default_profile.",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    ask = commands.add_parser("ask", help="Send one text request with failover.")
    ask.add_argument("prompt", help="User prompt.")
    ask.add_argument("--provider", help="Lock the request to one provider name.")
    ask.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Load a local skill by directory name; repeatable.",
    )
    ask.add_argument(
        "--memory-limit",
        type=int,
        default=10,
        help="Maximum recent confirmed memories to inject (default: 10).",
    )
    ask.add_argument(
        "--no-memory",
        action="store_true",
        help="Do not inject confirmed memory for this request.",
    )
    ask.add_argument(
        "--system",
        default="",
        help="Additional one-off system instruction.",
    )
    ask.add_argument(
        "--json",
        action="store_true",
        help="Print result metadata and text as JSON.",
    )

    doctor = commands.add_parser(
        "doctor", help="Inspect local configuration without calling providers."
    )
    doctor.set_defaults(handler=_doctor)

    remember = commands.add_parser("remember", help="Append a user-owned memory.")
    remember.add_argument("content", help="Memory content.")
    remember.add_argument("--title", default="Untitled")
    remember.add_argument("--kind", default="note")
    remember.add_argument("--tag", action="append", default=[])
    remember.add_argument(
        "--confirmed",
        action="store_true",
        help="Store as confirmed immediately; default is draft.",
    )

    confirm = commands.add_parser(
        "confirm-memory", help="Mark one draft memory as confirmed."
    )
    confirm.add_argument("memory_id")

    archive = commands.add_parser(
        "archive-memory", help="Archive one memory so it is not injected."
    )
    archive.add_argument("memory_id")

    memories = commands.add_parser("memories", help="List stored memory items.")
    memories.add_argument(
        "--status", choices=["draft", "confirmed", "archived"], default=None
    )
    memories.add_argument("--json", action="store_true")

    export = commands.add_parser(
        "export-memory", help="Export memory to portable Markdown."
    )
    export.add_argument("--output", required=True)
    export.add_argument(
        "--status", choices=["draft", "confirmed", "archived"], default=None
    )

    commands.add_parser("skills", help="List local skills.")
    return parser


def _read_identity(config: AppConfig) -> str:
    if not config.identity_file.exists():
        raise RuntimeError(f"Identity file not found: {config.identity_file}")
    return config.identity_file.read_text(encoding="utf-8").strip()


def _system_context(config: AppConfig, args: argparse.Namespace) -> str:
    sections = [_read_identity(config)]

    selected_skills = load_skills(config.skills_path, args.skill)
    skill_context = render_skill_context(selected_skills)
    if skill_context:
        sections.append(skill_context)

    if not args.no_memory:
        if args.memory_limit < 0:
            raise ValueError("--memory-limit must be zero or greater.")
        memories = MemoryStore(config.memory_path).recent_confirmed(args.memory_limit)
        memory_context = render_memory_context(memories)
        if memory_context:
            sections.append(memory_context)

    if args.system.strip():
        sections.append(f"# One-off instruction\n{args.system.strip()}")
    return "\n\n".join(section for section in sections if section)


def _ask(config: AppConfig, args: argparse.Namespace) -> int:
    profile = config.profile(args.profile)
    messages = [
        ChatMessage(role="system", content=_system_context(config, args)),
        ChatMessage(role="user", content=args.prompt),
    ]
    router = ProviderRouter(profile)
    result, earlier_failures = router.generate(
        messages, requested_provider=args.provider
    )

    if args.json:
        payload = asdict(result)
        payload["earlier_failures"] = [asdict(item) for item in earlier_failures]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(result.text)
        print(
            f"\n[provider={result.provider} model={result.model} "
            f"latency_ms={result.latency_ms}]",
            file=sys.stderr,
        )
        for failure in earlier_failures:
            print(
                f"[failover] {failure.provider} attempt {failure.attempt}: "
                f"{failure.reason}",
                file=sys.stderr,
            )
    return 0


def _doctor(config: AppConfig, args: argparse.Namespace) -> int:
    profile = config.profile(args.profile)
    print(f"config: {config.root}")
    print(f"profile: {profile.name}")
    print(
        f"identity: {'ok' if config.identity_file.exists() else 'missing'} "
        f"({config.identity_file})"
    )
    print(f"memory: {config.memory_path}")
    print(f"skills: {config.skills_path} ({len(discover_skills(config.skills_path))})")

    ready_count = 0
    for provider in profile.providers:
        problems: list[str] = []
        if not provider.enabled:
            problems.append("disabled")
        if not provider.model:
            problems.append("model missing")
        if not provider.api_key:
            problems.append(f"{provider.api_key_env} missing")
        state = "ready" if not problems else ", ".join(problems)
        if not problems:
            ready_count += 1
        print(
            f"provider {provider.name}: {state}; type={provider.type}; "
            f"priority={provider.priority}"
        )

    if ready_count == 0:
        print("No provider is currently ready.", file=sys.stderr)
        return 2
    return 0


def _remember(config: AppConfig, args: argparse.Namespace) -> int:
    status = "confirmed" if args.confirmed else "draft"
    item = MemoryStore(config.memory_path).add(
        args.content,
        title=args.title,
        kind=args.kind,
        tags=args.tag,
        status=status,
    )
    print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _set_memory_status(config: AppConfig, memory_id: str, status: str) -> int:
    item = MemoryStore(config.memory_path).set_status(memory_id, status)
    print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _list_memories(config: AppConfig, args: argparse.Namespace) -> int:
    items = MemoryStore(config.memory_path).load()
    if args.status:
        items = [item for item in items if item.status == args.status]

    if args.json:
        print(
            json.dumps(
                [item.to_dict() for item in items], ensure_ascii=False, indent=2
            )
        )
        return 0

    if not items:
        print("No matching memory items.")
        return 0
    for item in items:
        tags = f" tags={','.join(item.tags)}" if item.tags else ""
        print(f"{item.id} [{item.status}] {item.title}{tags}")
    return 0


def _export_memory(config: AppConfig, args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = config.root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        MemoryStore(config.memory_path).export_markdown(args.status),
        encoding="utf-8",
    )
    print(output)
    return 0


def _list_skills(config: AppConfig) -> int:
    skills = discover_skills(config.skills_path)
    if not skills:
        print("No local skills found.")
        return 0
    for skill in skills:
        print(f"{skill.name}: {skill.title} ({skill.path})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.command == "ask":
            return _ask(config, args)
        if args.command == "doctor":
            return _doctor(config, args)
        if args.command == "remember":
            return _remember(config, args)
        if args.command == "confirm-memory":
            return _set_memory_status(config, args.memory_id, "confirmed")
        if args.command == "archive-memory":
            return _set_memory_status(config, args.memory_id, "archived")
        if args.command == "memories":
            return _list_memories(config, args)
        if args.command == "export-memory":
            return _export_memory(config, args)
        if args.command == "skills":
            return _list_skills(config)
        parser.error(f"Unsupported command: {args.command}")
    except AllProvidersFailedError as exc:
        print("All configured providers failed:", file=sys.stderr)
        for failure in exc.failures:
            print(
                f"- {failure.provider} attempt {failure.attempt}: {failure.reason}",
                file=sys.stderr,
            )
        return 3
    except (ConfigError, MemoryError, SkillError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 2
