from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import analyze_messages
from .io import load_messages

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_FILE = PROJECT_ROOT / "data" / "demo_messages.json"


def _to_markdown(result: dict) -> str:
    lines = ["# 群聊信息流分析", "", result["overview"], ""]

    lines.extend(["## 重点消息"])
    lines.extend([f"- {item}" for item in result["highlights"]] or ["- 暂无"])

    lines.extend(["", "## 待办"])
    for action in result["actions"]:
        owner = action["owner"] or "待认领"
        deadline = action["deadline"] or "未识别"
        lines.append(f"- {action['title']}（负责人：{owner}；截止：{deadline}）")
    if not result["actions"]:
        lines.append("- 暂无")

    lines.extend(["", "## 风险"])
    lines.extend([f"- [{item['level']}] {item['detail']}" for item in result["risks"]] or ["- 暂无"])

    lines.extend(["", "## 已形成决策"])
    lines.extend([f"- {item}" for item in result["decisions"]] or ["- 暂无"])

    lines.extend(["", "## 未决问题"])
    lines.extend([f"- {item}" for item in result["questions"]] or ["- 暂无"])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="微信群信息流本地分析器")
    parser.add_argument("command", choices=["demo", "analyze"])
    parser.add_argument("path", nargs="?", help="analyze 模式下的 JSON 文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON，而不是 Markdown")
    args = parser.parse_args()

    source = DEMO_FILE if args.command == "demo" else args.path
    if not source:
        parser.error("analyze 模式需要提供 JSON 文件路径")

    result = analyze_messages(load_messages(source)).to_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _to_markdown(result))


if __name__ == "__main__":
    main()
