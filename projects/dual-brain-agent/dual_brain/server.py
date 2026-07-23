from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .models import TaskRequest
from .orchestrator import DualBrainOrchestrator
from .provider import ProviderError, build_provider_from_env

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class DualBrainHandler(SimpleHTTPRequestHandler):
    orchestrator: DualBrainOrchestrator

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {"ok": True, "mode": self.orchestrator.provider.mode},
            )
            return
        if self.path in {"/", "/index.html"}:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 200_000:
                raise ValueError("invalid request body size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            constraints = payload.get("constraints", [])
            if isinstance(constraints, str):
                constraints = [line.strip() for line in constraints.splitlines() if line.strip()]
            request = TaskRequest(
                task=str(payload.get("task", "")),
                context=str(payload.get("context", "")),
                constraints=list(constraints),
            )
            result = self.orchestrator.run(request)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except ProviderError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - last-resort HTTP boundary
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"internal error: {exc}"})
            return

        self._send_json(HTTPStatus.OK, result.to_dict())

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[dual-brain] {self.address_string()} - {fmt % args}")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    provider = build_provider_from_env()
    orchestrator = DualBrainOrchestrator(provider)
    handler = type(
        "ConfiguredDualBrainHandler",
        (DualBrainHandler,),
        {"orchestrator": orchestrator},
    )
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    server = create_server(host, port)
    print(f"Dual-Brain Agent running at http://{host}:{port} ({server.RequestHandlerClass.orchestrator.provider.mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
