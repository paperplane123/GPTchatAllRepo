from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when the local configuration is missing or invalid."""


_ENV_REF = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_ALLOWED_PROVIDER_TYPES = {"openai", "anthropic", "gemini"}


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        match = _ENV_REF.match(value)
        if match:
            return os.environ.get(match.group(1), "")
        return value
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    type: str
    model: str
    api_key_env: str
    base_url: str
    priority: int = 100
    max_tokens: int = 4096
    enabled: bool = True

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "").strip()

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.model.strip()) and bool(self.api_key)


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    providers: tuple[ProviderConfig, ...]
    timeout_seconds: int = 90
    max_attempts_per_provider: int = 1


@dataclass(frozen=True)
class AppConfig:
    root: Path
    default_profile: str
    profiles: dict[str, ProfileConfig]
    identity_file: Path
    memory_path: Path
    skills_path: Path

    def profile(self, name: str | None = None) -> ProfileConfig:
        selected = name or self.default_profile
        try:
            return self.profiles[selected]
        except KeyError as exc:
            available = ", ".join(sorted(self.profiles)) or "none"
            raise ConfigError(
                f"Unknown profile '{selected}'. Available profiles: {available}."
            ) from exc


def _require_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}.{key} must be a non-empty string.")
    return value.strip()


def _positive_int(value: Any, default: int, context: str) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(f"{context} must be a positive integer.")
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Invalid JSON in {config_path}: line {exc.lineno}, column {exc.colno}."
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigError("The configuration root must be a JSON object.")

    data = _expand_env(raw)
    root = config_path.parent
    default_profile = _require_string(data, "default_profile", "config")

    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ConfigError("config.profiles must be a non-empty object.")

    profiles: dict[str, ProfileConfig] = {}
    for profile_name, profile_data in raw_profiles.items():
        context = f"profiles.{profile_name}"
        if not isinstance(profile_name, str) or not profile_name.strip():
            raise ConfigError("Profile names must be non-empty strings.")
        if not isinstance(profile_data, dict):
            raise ConfigError(f"{context} must be an object.")

        raw_providers = profile_data.get("providers")
        if not isinstance(raw_providers, list) or not raw_providers:
            raise ConfigError(f"{context}.providers must be a non-empty array.")

        provider_names: set[str] = set()
        providers: list[ProviderConfig] = []
        for index, provider_data in enumerate(raw_providers):
            provider_context = f"{context}.providers[{index}]"
            if not isinstance(provider_data, dict):
                raise ConfigError(f"{provider_context} must be an object.")

            name = _require_string(provider_data, "name", provider_context)
            if name in provider_names:
                raise ConfigError(f"Duplicate provider name '{name}' in {context}.")
            provider_names.add(name)

            provider_type = _require_string(provider_data, "type", provider_context)
            if provider_type not in _ALLOWED_PROVIDER_TYPES:
                allowed = ", ".join(sorted(_ALLOWED_PROVIDER_TYPES))
                raise ConfigError(
                    f"{provider_context}.type must be one of: {allowed}."
                )

            enabled = provider_data.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ConfigError(f"{provider_context}.enabled must be boolean.")

            providers.append(
                ProviderConfig(
                    name=name,
                    type=provider_type,
                    model=str(provider_data.get("model", "")).strip(),
                    api_key_env=_require_string(
                        provider_data, "api_key_env", provider_context
                    ),
                    base_url=_require_string(
                        provider_data, "base_url", provider_context
                    ).rstrip("/"),
                    priority=int(provider_data.get("priority", 100)),
                    max_tokens=_positive_int(
                        provider_data.get("max_tokens"),
                        4096,
                        f"{provider_context}.max_tokens",
                    ),
                    enabled=enabled,
                )
            )

        providers.sort(key=lambda item: (item.priority, item.name))
        profiles[profile_name] = ProfileConfig(
            name=profile_name,
            providers=tuple(providers),
            timeout_seconds=_positive_int(
                profile_data.get("timeout_seconds"),
                90,
                f"{context}.timeout_seconds",
            ),
            max_attempts_per_provider=_positive_int(
                profile_data.get("max_attempts_per_provider"),
                1,
                f"{context}.max_attempts_per_provider",
            ),
        )

    if default_profile not in profiles:
        raise ConfigError(
            f"default_profile '{default_profile}' does not exist in config.profiles."
        )

    def local_path(key: str, default: str) -> Path:
        value = data.get(key, default)
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"config.{key} must be a non-empty path string.")
        path_value = Path(value).expanduser()
        return path_value if path_value.is_absolute() else (root / path_value)

    return AppConfig(
        root=root,
        default_profile=default_profile,
        profiles=profiles,
        identity_file=local_path("identity_file", "identity/core.md"),
        memory_path=local_path("memory_path", "data/memory.jsonl"),
        skills_path=local_path("skills_path", "skills"),
    )
