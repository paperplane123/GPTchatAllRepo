from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """Raised when an LLM provider request fails."""


class ChatProvider(Protocol):
    mode: str

    def complete(self, messages: list[dict[str, str]], temperature: float) -> str:
        ...


@dataclass(slots=True)
class OpenAICompatibleProvider:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 120
    mode: str = "openai-compatible"

    @classmethod
    def from_env(cls) -> "OpenAICompatibleProvider":
        base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()
        if not base_url or not model:
            raise ProviderError("openai mode requires LLM_BASE_URL and LLM_MODEL")
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
        )

    def complete(self, messages: list[dict[str, str]], temperature: float) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"provider returned HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"provider request failed: {exc}") from exc

        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("provider response did not contain choices[0].message.content") from exc


class DemoProvider:
    """Deterministic provider for zero-configuration UI and pipeline testing."""

    mode = "demo"

    def complete(self, messages: list[dict[str, str]], temperature: float) -> str:
        system = messages[0]["content"]
        user = messages[-1]["content"]
        task = _extract_task(user)

        if "仲裁器" in system:
            data = {
                "summary": f"先交付“{task}”的最小闭环：双脑并行、仲裁决策、过程可见、结果可复现。",
                "reasoning_points": [
                    "采用右脑发散、左脑审查、仲裁器决策的三阶段流水线",
                    "第一版不追求多智能体自治，先保证接口稳定和输出可观测",
                    "用演示模式验证产品交互，再接入真实 OpenAI 兼容模型",
                ],
                "risks": ["演示模式不代表真实模型质量", "真实模型可能不严格返回 JSON"],
                "recommendations": [
                    "运行固定示例验证完整链路",
                    "接入真实模型后增加结构化输出重试",
                    "下一版加入会话记忆、工具调用和人工否决开关",
                ],
                "confidence": 0.9,
            }
        elif "右脑" in system:
            data = {
                "summary": f"围绕“{task}”先并行探索三条路线，再用最小实验淘汰低价值方向。",
                "reasoning_points": [
                    "把任务拆成产品价值、技术路径和验证机制三个视角",
                    "优先寻找可复用的能力，而不是只做一次性回答",
                    "允许提出大胆假设，但所有假设必须进入待验证清单",
                ],
                "risks": ["方案过多导致执行分散", "创意可能依赖尚未确认的数据或接口"],
                "recommendations": [
                    "生成三个差异明显的候选方案",
                    "为每个方案定义一天内可完成的最小验证",
                    "保留一个低成本备选路线",
                ],
                "confidence": 0.72,
            }
        elif "左脑" in system:
            data = {
                "summary": f"“{task}”可以启动，但应先锁定成功标准、输入边界和失败退出条件。",
                "reasoning_points": [
                    "当前任务目标存在解释空间，需要用可验收结果收敛",
                    "先验证最关键依赖，再投入界面和自动化工程",
                    "任何外部事实、接口与数据都必须可追溯",
                ],
                "risks": ["验收标准不清", "模型输出可能看似完整但无法复现", "外部依赖失败时缺少降级路径"],
                "recommendations": [
                    "定义一个可运行样例和一组固定测试输入",
                    "记录每次左右脑与仲裁器的原始输出",
                    "无模型密钥时提供确定性的演示模式",
                ],
                "confidence": 0.86,
            }
        else:
            data = {
                "summary": "未识别的演示角色。",
                "reasoning_points": [],
                "risks": ["系统提示词未匹配任何已知角色"],
                "recommendations": ["检查角色提示词"],
                "confidence": 0.2,
            }
        return json.dumps(data, ensure_ascii=False)


def build_provider_from_env() -> ChatProvider:
    mode = os.getenv("DUAL_BRAIN_MODE", "demo").strip().lower()
    if mode in {"openai", "openai-compatible", "llm"}:
        return OpenAICompatibleProvider.from_env()
    if mode != "demo":
        raise ProviderError(f"unsupported DUAL_BRAIN_MODE: {mode}")
    return DemoProvider()


def _extract_task(prompt: str) -> str:
    match = re.search(r"(?m)^任务：\s*\n?", prompt)
    if not match:
        return "当前任务"
    text = prompt[match.end() :]
    text = re.split(r"(?m)^上下文：\s*$", text, maxsplit=1)[0].strip()
    return (text[:42] + "…") if len(text) > 42 else text
