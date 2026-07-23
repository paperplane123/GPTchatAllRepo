from __future__ import annotations

import json
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .models import AgentOutput, DecisionResult, TaskRequest
from .prompts import (
    ARBITER_SYSTEM,
    LEFT_BRAIN_SYSTEM,
    RIGHT_BRAIN_SYSTEM,
    build_arbiter_prompt,
    build_task_prompt,
)
from .provider import ChatProvider


class DualBrainOrchestrator:
    def __init__(self, provider: ChatProvider):
        self.provider = provider

    def run(self, request: TaskRequest) -> DecisionResult:
        request.validate()
        started = time.perf_counter()
        task_prompt = build_task_prompt(request.task, request.context, request.constraints)

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="dual-brain") as pool:
            right_future = pool.submit(
                self._run_agent, "right_brain", RIGHT_BRAIN_SYSTEM, task_prompt, 0.85
            )
            left_future = pool.submit(
                self._run_agent, "left_brain", LEFT_BRAIN_SYSTEM, task_prompt, 0.2
            )
            right = right_future.result()
            left = left_future.result()

        arbiter_prompt = build_arbiter_prompt(
            task_prompt,
            json.dumps(right.to_dict(), ensure_ascii=False),
            json.dumps(left.to_dict(), ensure_ascii=False),
        )
        arbiter = self._run_agent("arbiter", ARBITER_SYSTEM, arbiter_prompt, 0.15)
        elapsed = int((time.perf_counter() - started) * 1000)

        return DecisionResult(
            run_id=str(uuid.uuid4()),
            task=request,
            right_brain=right,
            left_brain=left,
            arbiter=arbiter,
            duration_ms=elapsed,
            mode=self.provider.mode,
        )

    def _run_agent(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> AgentOutput:
        raw = self.provider.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        data = parse_json_object(raw)
        output = AgentOutput.from_mapping(role=role, data=data, raw=raw)
        if not output.summary:
            output.summary = "模型返回了结构化结果，但 summary 为空。"
        return output


def parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {
        "summary": text[:800] or "模型未返回可解析内容。",
        "reasoning_points": [],
        "risks": ["模型输出不是合法 JSON，已降级为纯文本结果"],
        "recommendations": ["为该模型增加结构化输出约束或重试策略"],
        "confidence": 0.35,
    }
