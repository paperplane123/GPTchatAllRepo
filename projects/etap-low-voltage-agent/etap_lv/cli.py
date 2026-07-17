from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import EtapConfig, EtapError, EtapRestClient
from .domain import AcceptanceLimits, ScenarioResult
from .ranking import rank_results
from .runner import read_json, run_study_file


def _load_demo(path: str | Path) -> tuple[AcceptanceLimits, list[ScenarioResult]]:
    raw = read_json(path)
    limits = AcceptanceLimits.from_dict(raw.get("acceptance_limits"))
    results = [
        ScenarioResult(
            scenario_id=str(item["id"]),
            name=str(item["name"]),
            cost_cny=float(item.get("cost_cny", 0)),
            min_voltage_pu=float(item["min_voltage_pu"]),
            max_loading_pct=float(item["max_loading_pct"]),
            max_unbalance_pct=float(item["max_unbalance_pct"]),
            source=str(item.get("source", "sample-data")),
            raw=item,
        )
        for item in raw.get("results", [])
    ]
    return limits, results


def _print_ranked(limits: AcceptanceLimits, results: list[ScenarioResult]) -> None:
    ranked = rank_results(results, limits)
    print(
        "验收约束："
        f"最低电压≥{limits.min_voltage_pu:.3f} pu，"
        f"最大负载率≤{limits.max_loading_pct:.1f}%，"
        f"最大三相不平衡度≤{limits.max_unbalance_pct:.1f}%"
    )
    print()
    for index, result in enumerate(ranked, start=1):
        violations = result.violations(limits)
        status = "通过" if not violations else "不通过"
        print(
            f"{index}. [{status}] {result.name} | 成本 ¥{result.cost_cny:,.0f} | "
            f"Umin={result.min_voltage_pu:.4f} pu | "
            f"负载率={result.max_loading_pct:.2f}% | "
            f"不平衡度={result.max_unbalance_pct:.2f}% | 来源={result.source}"
        )
        for violation in violations:
            print(f"   - {violation}")


def command_probe(args: argparse.Namespace) -> int:
    config = EtapConfig.from_file(args.config)
    client = EtapRestClient(config)
    path, document = client.discover_openapi()
    operations = client.find_operations(
        document,
        ("study", "load flow", "loadflow", "scenario", "bus", "voltage"),
    )
    print(f"已读取 OpenAPI：{config.base_url}{path}")
    print(f"发现 {len(operations)} 个候选接口：")
    for item in operations:
        detail = " | ".join(
            part for part in (item["operation_id"], item["summary"]) if part
        )
        suffix = f" | {detail}" if detail else ""
        print(f"- {item['method']:6} {item['path']}{suffix}")
    return 0


def command_demo(args: argparse.Namespace) -> int:
    limits, results = _load_demo(args.data)
    _print_ranked(limits, results)
    print("\n注意：以上是示例结果，只验证程序流程，不是 ETAP 实机计算。")
    return 0


def command_run(args: argparse.Namespace) -> int:
    limits, results = run_study_file(args.config, args.study)
    _print_ranked(limits, results)
    if args.output:
        payload = {
            "acceptance_limits": limits.__dict__,
            "results": [item.__dict__ for item in rank_results(results, limits)],
        }
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n结果已写入：{args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etap-lv", description="ETAP 低电压治理仿真自动化 PoC"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="只读探测 ETAP Swagger/OpenAPI")
    probe.add_argument("--config", required=True)
    probe.set_defaults(handler=command_probe)

    demo = subparsers.add_parser("demo", help="使用示例结果验证方案排序")
    demo.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent.parent / "data" / "sample_results.json"),
    )
    demo.set_defaults(handler=command_demo)

    run = subparsers.add_parser("run", help="调用已配置的真实 ETAP 同步研究接口")
    run.add_argument("--config", required=True)
    run.add_argument("--study", required=True)
    run.add_argument("--output")
    run.set_defaults(handler=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (EtapError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
