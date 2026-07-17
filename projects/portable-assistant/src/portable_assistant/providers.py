from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import ProviderConfig


class ProviderError(RuntimeError):
    """A provider request failed or returned an unusable response."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant"}:
            raise ValueError(f"Unsupported message role: {self.role}")
        if not self.content.strip():
            raise ValueError("Message content must not be empty.")


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    model: str
    text: str
    latency_ms: int
    usage: dict[str, Any] | None = None


class TextProvider(Protocol):
    config: ProviderConfig

    def generate(
        self, messages: list[ChatMessage], timeout_seconds: int
    ) -> ProviderResult: ...


def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
    provider_name: str,
) -> dict[str, Any]:
    request = Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            error_body = ""
        detail = f"HTTP {exc.code}"
        if error_body:
            detail += f": {error_body}"
        raise ProviderError(f"{provider_name} request failed: {detail}") from exc
    except URLError as exc:
        raise ProviderError(
            f"{provider_name} network failure: {getattr(exc, 'reason', exc)}"
        ) from exc
    except TimeoutError as exc:
        raise ProviderError(
            f"{provider_name} timed out after {timeout_seconds}s"
        ) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        preview = body[:500]
        raise ProviderError(
            f"{provider_name} returned invalid JSON: {preview!r}"
        ) from exc

    if not isinstance(data, dict):
        raise ProviderError(f"{provider_name} returned a non-object JSON response.")
    return data


def _require_text(text: str, provider_name: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise ProviderError(f"{provider_name} returned no text content.")
    return cleaned


class OpenAIProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def generate(
        self, messages: list[ChatMessage], timeout_seconds: int
    ) -> ProviderResult:
        started = time.monotonic()
        payload: dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "max_output_tokens": self.config.max_tokens,
        }
        data = _post_json(
            f"{self.config.base_url}/responses",
            {"Authorization": f"Bearer {self.config.api_key}"},
            payload,
            timeout_seconds,
            self.config.name,
        )

        text = data.get("output_text")
        if not isinstance(text, str) or not text.strip():
            chunks: list[str] = []
            output = data.get("output", [])
            if isinstance(output, list):
                for item in output:
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content", [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        block_text = block.get("text")
                        if isinstance(block_text, str):
                            chunks.append(block_text)
            text = "\n".join(chunks)

        usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
        return ProviderResult(
            provider=self.config.name,
            model=self.config.model,
            text=_require_text(text if isinstance(text, str) else "", self.config.name),
            latency_ms=round((time.monotonic() - started) * 1000),
            usage=usage,
        )


class AnthropicProvider:
    API_VERSION = "2023-06-01"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def generate(
        self, messages: list[ChatMessage], timeout_seconds: int
    ) -> ProviderResult:
        started = time.monotonic()
        system_parts = [
            message.content for message in messages if message.role == "system"
        ]
        conversational = [
            {"role": message.role, "content": message.content}
            for message in messages
            if message.role in {"user", "assistant"}
        ]
        if not conversational:
            raise ProviderError("anthropic requires at least one user message.")

        payload: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": conversational,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)

        data = _post_json(
            f"{self.config.base_url}/v1/messages",
            {
                "x-api-key": self.config.api_key,
                "anthropic-version": self.API_VERSION,
            },
            payload,
            timeout_seconds,
            self.config.name,
        )

        chunks: list[str] = []
        content = data.get("content", [])
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    chunks.append(block["text"])

        usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
        return ProviderResult(
            provider=self.config.name,
            model=self.config.model,
            text=_require_text("\n".join(chunks), self.config.name),
            latency_ms=round((time.monotonic() - started) * 1000),
            usage=usage,
        )


class GeminiProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def generate(
        self, messages: list[ChatMessage], timeout_seconds: int
    ) -> ProviderResult:
        started = time.monotonic()
        system_parts = [
            message.content for message in messages if message.role == "system"
        ]
        contents: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})

        if not contents:
            raise ProviderError("gemini requires at least one user message.")

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": self.config.max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}]
            }

        model = self.config.model.removeprefix("models/")
        url = f"{self.config.base_url}/models/{quote(model, safe='')}:generateContent"
        data = _post_json(
            url,
            {"x-goog-api-key": self.config.api_key},
            payload,
            timeout_seconds,
            self.config.name,
        )

        chunks: list[str] = []
        candidates = data.get("candidates", [])
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, dict):
                content = first.get("content", {})
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    if isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict) and isinstance(part.get("text"), str):
                                chunks.append(part["text"])

        usage = (
            data.get("usageMetadata")
            if isinstance(data.get("usageMetadata"), dict)
            else None
        )
        return ProviderResult(
            provider=self.config.name,
            model=self.config.model,
            text=_require_text("\n".join(chunks), self.config.name),
            latency_ms=round((time.monotonic() - started) * 1000),
            usage=usage,
        )


def build_provider(config: ProviderConfig) -> TextProvider:
    if config.type == "openai":
        return OpenAIProvider(config)
    if config.type == "anthropic":
        return AnthropicProvider(config)
    if config.type == "gemini":
        return GeminiProvider(config)
    raise ProviderError(f"Unsupported provider type: {config.type}")
