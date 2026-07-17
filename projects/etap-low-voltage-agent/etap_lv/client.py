from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EtapError(RuntimeError):
    """Base error raised by the ETAP integration layer."""


@dataclass(frozen=True)
class EtapConfig:
    base_url: str
    token_env: str = "ETAP_API_TOKEN"
    verify_tls: bool = True
    timeout_seconds: float = 30.0
    openapi_paths: tuple[str, ...] = (
        "/swagger/v1/swagger.json",
        "/swagger/swagger.json",
        "/openapi.json",
    )
    study_route: dict[str, Any] | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "EtapConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            base_url=str(raw["base_url"]).rstrip("/"),
            token_env=str(raw.get("token_env", "ETAP_API_TOKEN")),
            verify_tls=bool(raw.get("verify_tls", True)),
            timeout_seconds=float(raw.get("timeout_seconds", 30.0)),
            openapi_paths=tuple(raw.get("openapi_paths", cls.openapi_paths)),
            study_route=raw.get("study_route"),
        )


class EtapRestClient:
    def __init__(self, config: EtapConfig) -> None:
        self.config = config
        self._ssl_context = self._build_ssl_context(config.verify_tls)

    @staticmethod
    def _build_ssl_context(verify_tls: bool) -> ssl.SSLContext:
        if verify_tls:
            return ssl.create_default_context()
        return ssl._create_unverified_context()  # noqa: SLF001 - explicit lab-only option

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
    ) -> Any:
        url = self._url(path)
        headers = {"Accept": "application/json"}
        token = os.getenv(self.config.token_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            url=url,
            data=body,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
                context=self._ssl_context,
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise EtapError(f"ETAP HTTP {exc.code} {url}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise EtapError(f"无法连接 ETAP DataHub/API：{url}；原因：{exc.reason}") from exc

        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            preview = raw.decode("utf-8", errors="replace")[:500]
            raise EtapError(f"ETAP 返回的不是 JSON：{preview}") from exc

    def discover_openapi(self) -> tuple[str, dict[str, Any]]:
        errors: list[str] = []
        for path in self.config.openapi_paths:
            try:
                document = self.request_json("GET", path)
            except EtapError as exc:
                errors.append(str(exc))
                continue
            if isinstance(document, dict) and isinstance(document.get("paths"), dict):
                return path, document
            errors.append(f"{self._url(path)} 未返回含 paths 的 OpenAPI 文档")

        joined = "\n- ".join(errors)
        raise EtapError(f"未发现 ETAP Swagger/OpenAPI 文档：\n- {joined}")

    @staticmethod
    def find_operations(
        document: dict[str, Any], keywords: tuple[str, ...]
    ) -> list[dict[str, str]]:
        matches: list[dict[str, str]] = []
        for path, path_item in document.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if not isinstance(operation, dict):
                    continue
                haystack = " ".join(
                    [
                        path,
                        str(operation.get("summary", "")),
                        str(operation.get("description", "")),
                        str(operation.get("operationId", "")),
                        " ".join(map(str, operation.get("tags", []))),
                    ]
                ).lower()
                if any(keyword.lower() in haystack for keyword in keywords):
                    matches.append(
                        {
                            "method": method.upper(),
                            "path": path,
                            "operation_id": str(operation.get("operationId", "")),
                            "summary": str(operation.get("summary", "")),
                        }
                    )
        return sorted(matches, key=lambda item: (item["path"], item["method"]))

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urllib.parse.urljoin(f"{self.config.base_url}/", path.lstrip("/"))
