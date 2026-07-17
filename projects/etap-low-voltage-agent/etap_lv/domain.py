from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AcceptanceLimits:
    min_voltage_pu: float = 0.90
    max_loading_pct: float = 100.0
    max_unbalance_pct: float = 15.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "AcceptanceLimits":
        raw = raw or {}
        return cls(
            min_voltage_pu=float(raw.get("min_voltage_pu", 0.90)),
            max_loading_pct=float(raw.get("max_loading_pct", 100.0)),
            max_unbalance_pct=float(raw.get("max_unbalance_pct", 15.0)),
        )


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    name: str
    cost_cny: float
    min_voltage_pu: float
    max_loading_pct: float
    max_unbalance_pct: float
    source: str = "etap"
    raw: dict[str, Any] | None = None

    def violations(self, limits: AcceptanceLimits) -> list[str]:
        items: list[str] = []
        if self.min_voltage_pu < limits.min_voltage_pu:
            items.append(
                f"最低电压 {self.min_voltage_pu:.4f} pu < {limits.min_voltage_pu:.4f} pu"
            )
        if self.max_loading_pct > limits.max_loading_pct:
            items.append(
                f"最大负载率 {self.max_loading_pct:.2f}% > {limits.max_loading_pct:.2f}%"
            )
        if self.max_unbalance_pct > limits.max_unbalance_pct:
            items.append(
                f"最大三相不平衡度 {self.max_unbalance_pct:.2f}% > {limits.max_unbalance_pct:.2f}%"
            )
        return items

    def is_compliant(self, limits: AcceptanceLimits) -> bool:
        return not self.violations(limits)
