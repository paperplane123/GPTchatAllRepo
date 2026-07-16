from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from .domain import ActionItem, AnalysisResult, Message, RiskAlert

ACTION_WORDS = (
    "请", "需要", "负责", "跟进", "完成", "提交", "上线", "补", "处理", "确认",
    "安排", "别忘了", "麻烦", "同步", "排查", "更新", "整理", "准备", "恢复", "必须",
)
DECISION_WORDS = ("决定", "确定", "结论", "统一", "采用", "改为", "不再", "先做", "暂缓", "按这个")
HIGH_RISK_WORDS = ("必须", "阻塞", "挂了", "故障", "严重", "延期", "来不及", "投诉", "超时", "泄露", "封号")
MEDIUM_RISK_WORDS = ("还有", "未完成", "缺少", "问题", "失败", "风险", "等待", "卡住", "异常")
QUESTION_WORDS = ("谁来", "怎么办", "是否", "能不能", "有没有", "怎么处理", "什么时间")

DEADLINE_RE = re.compile(
    r"(今天|今晚|明天|明早|后天|本周[一二三四五六日天]?|周[一二三四五六日天]|"
    r"上午\s*\d{1,2}\s*点|下午\s*\d{1,2}\s*点|晚上\s*\d{1,2}\s*点|"
    r"\d{1,2}[:：]\d{2}|\d{1,2}月\d{1,2}日)"
)
OWNER_RE = re.compile(
    r"(?:@|请|由)?\s*([\u4e00-\u9fa5A-Za-z0-9_]{2,12}?)\s*(?:负责|来|跟进|处理|补|确认|完成|排查|更新|整理)"
)


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _extract_deadline(text: str) -> str | None:
    match = DEADLINE_RE.search(text)
    return match.group(1).replace(" ", "") if match else None


def _extract_owner(message: Message) -> str | None:
    if any(phrase in message.text for phrase in ("我来", "我负责", "我补", "我处理", "我跟进", "我确认")):
        return message.sender
    match = OWNER_RE.search(message.text)
    return match.group(1) if match else None


def _clean_action_title(text: str) -> str:
    title = re.sub(r"\s+", " ", text).strip(" ，。；;！!")
    return title[:100]


def analyze_messages(messages: Iterable[Message]) -> AnalysisResult:
    rows = list(messages)
    if not rows:
        return AnalysisResult(
            overview="没有可分析的消息。",
            stats={"messages": 0, "groups": 0, "members": 0, "actions": 0, "risks": 0},
        )

    actions: list[ActionItem] = []
    risks: list[RiskAlert] = []
    decisions: list[str] = []
    questions: list[str] = []
    scored_highlights: list[tuple[int, str]] = []

    for message in rows:
        text = message.text
        score = 0

        if _contains_any(text, ACTION_WORDS):
            owner = _extract_owner(message)
            deadline = _extract_deadline(text)
            confidence = 0.55 + (0.2 if owner else 0.0) + (0.2 if deadline else 0.0)
            actions.append(
                ActionItem(
                    title=_clean_action_title(text),
                    owner=owner,
                    deadline=deadline,
                    source_message_id=message.id,
                    confidence=min(confidence, 0.95),
                )
            )
            score += 3

        if _contains_any(text, HIGH_RISK_WORDS):
            risks.append(
                RiskAlert(
                    level="high",
                    title="高优先级风险",
                    detail=text[:160],
                    source_message_id=message.id,
                )
            )
            score += 5
        elif _contains_any(text, MEDIUM_RISK_WORDS):
            risks.append(
                RiskAlert(
                    level="medium",
                    title="需关注事项",
                    detail=text[:160],
                    source_message_id=message.id,
                )
            )
            score += 2

        if _contains_any(text, DECISION_WORDS):
            decisions.append(f"{message.sender}：{text[:140]}")
            score += 4

        if text.endswith(("?", "？")) or _contains_any(text, QUESTION_WORDS):
            questions.append(f"{message.sender}：{text[:140]}")
            score += 1

        if score:
            scored_highlights.append((score, f"[{message.group}] {message.sender}：{text[:160]}"))

    group_counts = Counter(message.group for message in rows)
    overview = (
        f"共分析 {len(rows)} 条消息，来自 {len(group_counts)} 个群、"
        f"{len({message.sender for message in rows})} 位成员；识别出 "
        f"{len(actions)} 项待办、{len(risks)} 项风险、{len(decisions)} 条决策。"
    )

    highlights = [text for _, text in sorted(scored_highlights, key=lambda item: item[0], reverse=True)[:6]]
    return AnalysisResult(
        overview=overview,
        highlights=highlights,
        actions=actions,
        risks=risks,
        decisions=decisions,
        questions=questions,
        stats={
            "messages": len(rows),
            "groups": len(group_counts),
            "members": len({message.sender for message in rows}),
            "actions": len(actions),
            "risks": len(risks),
            "decisions": len(decisions),
            "questions": len(questions),
        },
    )
