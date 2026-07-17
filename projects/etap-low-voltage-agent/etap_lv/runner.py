from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from .client import EtapConfig, EtapError, EtapRestClient
from .domain import AcceptanceLimits, ScenarioResult

_PLACEHOLDER = re.compile(r"^\$\{([A-Za-z0-9_.-]+)\}$")


def read_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根节点必须是对象：{path}")
    return value


def extract_path(value: Any, dotted_path: str) -> Any:
    current = value
    if not dotted_path:
        return current
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            current = current[int(part)]
            continue
        raise KeyError(f"结果中不存在字段路径：{dotted_path}（停在 {part}）")
    return current


def render_template(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: render_template(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [render_template(item, context) for item in value]
    if isinstance(value, str):
        match = _PLACEHOLDER.match(value)
        if match:
            return extract_path(context, match.group(1))
        rendered = value
        for placeholder in re.findall(r"\$\{([A-Za-z0-9_.-]+)\}", value):
            rendered = rendered.replace(
                "${" + placeholder + "}", str(extract_path(context, placeholder))
            )
        return rendered
    return value


def normalize_result(
    raw_response: Any,
    scenario: dict[str, Any],
    result_mapping: dict[str, str],
) -> ScenarioResult:
    def mapped(name: str) -> Any:
        path = result_mapping.get(name)
        if not path:
            raise EtapError(f"study_route.result_mapping 缺少 {name}")
        return extract_path(raw_response, path)

    return ScenarioResult(
        scenario_id=str(scenario["id"]),
        name=str(scenario["name"]),
        cost_cny=float(scenario.get("cost_cny", 0.0)),
        min_voltage_pu=float(mapped("min_voltage_pu")),
        max_loading_pct=float(mapped("max_loading_pct")),
        max_unbalance_pct=float(mapped("max_unbalance_pct")),
        source="etap-api",
        raw=raw_response if isinstance(raw_response, dict) else {"response": raw_response},
    )


def run_study_file(
    config_path: str | Path, study_path: str | Path
) -> tuple[AcceptanceLimits, list[ScenarioResult]]:
    config = EtapConfig.from_file(config_path)
    route = config.study_route
    if not isinstance(route, dict):
        raise EtapError("配置中尚未填写 study_route；先运行 probe 确认真实 ETAP 接口")

    method = str(route.get("method", "POST"))
    path_template = route.get("path")
    body_template = route.get("body")
    result_mapping = route.get("result_mapping")
    if not isinstance(path_template, str) or not path_template.strip():
        raise EtapError("study_route.path 为空")
    if body_template is not None and not isinstance(body_template, (dict, list)):
        raise EtapError("study_route.body 必须是 JSON 对象或数组")
    if not isinstance(result_mapping, dict):
        raise EtapError("study_route.result_mapping 未配置")

    study = read_json(study_path)
    limits = AcceptanceLimits.from_dict(study.get("acceptance_limits"))
    scenarios = study.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("study.scenarios 必须是非空数组")

    base_context = copy.deepcopy(study.get("context", {}))
    client = EtapRestClient(config)
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("每个 scenario 必须是对象")
        for required in ("id", "name"):
            if required not in scenario:
                raise ValueError(f"scenario 缺少 {required}")

        context = {"study": study, "scenario": scenario, **base_context}
        path = render_template(path_template, context)
        body = render_template(body_template, context) if body_template is not None else None
        response = client.request_json(method, str(path), body)
        results.append(normalize_result(response, scenario, result_mapping))

    return limits, results
