from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .config import ProfileConfig, ProviderConfig
from .providers import (
    ChatMessage,
    ProviderError,
    ProviderResult,
    TextProvider,
    build_provider,
)


@dataclass(frozen=True)
class ProviderFailure:
    provider: str
    attempt: int
    reason: str


class AllProvidersFailedError(RuntimeError):
    def __init__(self, failures: list[ProviderFailure]) -> None:
        self.failures = failures
        summary = "; ".join(
            f"{item.provider} attempt {item.attempt}: {item.reason}"
            for item in failures
        )
        super().__init__(summary or "No provider was available.")


ProviderFactory = Callable[[ProviderConfig], TextProvider]


class ProviderRouter:
    def __init__(
        self,
        profile: ProfileConfig,
        provider_factory: ProviderFactory = build_provider,
    ) -> None:
        self.profile = profile
        self.provider_factory = provider_factory

    def _select(self, requested_provider: str | None) -> list[ProviderConfig]:
        enabled = [provider for provider in self.profile.providers if provider.enabled]
        if requested_provider is None:
            return enabled

        selected = [
            provider for provider in enabled if provider.name == requested_provider
        ]
        if not selected:
            available = ", ".join(provider.name for provider in enabled) or "none"
            raise ValueError(
                f"Unknown or disabled provider '{requested_provider}'. "
                f"Available providers: {available}."
            )
        return selected

    def generate(
        self,
        messages: list[ChatMessage],
        requested_provider: str | None = None,
    ) -> tuple[ProviderResult, list[ProviderFailure]]:
        failures: list[ProviderFailure] = []

        for config in self._select(requested_provider):
            if not config.model.strip():
                failures.append(
                    ProviderFailure(config.name, 0, "model is not configured")
                )
                continue
            if not config.api_key:
                failures.append(
                    ProviderFailure(
                        config.name,
                        0,
                        f"environment variable {config.api_key_env} is empty",
                    )
                )
                continue

            provider = self.provider_factory(config)
            for attempt in range(1, self.profile.max_attempts_per_provider + 1):
                try:
                    result = provider.generate(
                        messages=messages,
                        timeout_seconds=self.profile.timeout_seconds,
                    )
                    return result, failures
                except ProviderError as exc:
                    failures.append(
                        ProviderFailure(config.name, attempt, str(exc))
                    )
                    if attempt < self.profile.max_attempts_per_provider:
                        time.sleep(min(2 ** (attempt - 1), 4))
                except Exception as exc:
                    failures.append(
                        ProviderFailure(
                            config.name,
                            attempt,
                            f"unexpected {type(exc).__name__}: {exc}",
                        )
                    )
                    break

        raise AllProvidersFailedError(failures)
