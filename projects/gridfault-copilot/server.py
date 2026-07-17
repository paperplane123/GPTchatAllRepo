from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
HOST = os.getenv("GRIDFAULT_HOST", "127.0.0.1")
PORT = int(os.getenv("GRIDFAULT_PORT", "8787"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")

DEVELOPER_INSTRUCTION = """You are an assistant for a distribution-grid control-room prototype.
Write a concise operator brief from the supplied diagnostic JSON.
Use only measurements and conclusions present in the JSON.
Never invent field readings, breaker states, or certainty.
Explicitly state when the case is ambiguous or not diagnosable.
Return plain text with four short sections: Assessment, Evidence, Uncertainty, Recommended next action.
This is decision support only; do not issue autonomous switching commands."""


def _read_json(handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0 or content_length > 1_000_000:
        raise ValueError("Invalid request body size")
    raw = handler.rfile.read(content_length)
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    parts: list[str] = []
    output = response.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                text = chunk.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    return "\n".join(parts).strip()


def _local_brief(payload: dict[str, Any]) -> str:
    result = payload.get("result", {})
    if not isinstance(result, dict):
        result = {}

    status = str(result.get("diagnosability", "unknown"))
    top_section = str(result.get("topSection", "unknown section"))
    confidence = result.get("confidence", 0)
    fault_type = str(result.get("faultType", "undetermined"))
    action = str(result.get("nextAction", "Review available telemetry and operating procedures."))
    evidence = result.get("evidence", [])
    if isinstance(evidence, list):
        evidence_text = "; ".join(str(item) for item in evidence[:3])
    else:
        evidence_text = str(evidence)

    uncertainty = (
        "The current evidence is insufficient for a reliable section decision."
        if status != "diagnosable"
        else "The result remains decision support and requires operator validation."
    )

    return (
        f"Assessment\n{fault_type} is most consistent with {top_section} "
        f"at {confidence}% confidence; diagnosability is {status}.\n\n"
        f"Evidence\n{evidence_text or 'No evidence summary was supplied.'}\n\n"
        f"Uncertainty\n{uncertainty}\n\n"
        f"Recommended next action\n{action}"
    )


def _openai_brief(payload: dict[str, Any]) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _local_brief(payload), "local-fallback"

    request_body = {
        "model": OPENAI_MODEL,
        "reasoning": {"effort": "low"},
        "input": [
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": DEVELOPER_INSTRUCTION}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    }
                ],
            },
        ],
        "max_output_tokens": 700,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API connection failed: {exc.reason}") from exc

    text = _extract_output_text(data)
    if not text:
        raise RuntimeError("OpenAI API returned no text output")
    return text, OPENAI_MODEL


class GridFaultHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self) -> None:  # noqa: N802 - inherited HTTP method name
        if self.path != "/api/explain":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            payload = _read_json(self)
            text, source = _openai_brief(payload)
            self._send_json(HTTPStatus.OK, {"text": text, "source": source})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
        except Exception as exc:  # defensive boundary for a demo server
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Unexpected error: {exc}"})

    def _send_json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[gridfault] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), GridFaultHandler)
    print(f"GridFault Copilot running at http://{HOST}:{PORT}")
    print(
        f"Operator brief: {'OpenAI ' + OPENAI_MODEL if os.getenv('OPENAI_API_KEY') else 'local fallback (set OPENAI_API_KEY to enable GPT-5.6)'}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GridFault Copilot")
    finally:
        server.server_close()
