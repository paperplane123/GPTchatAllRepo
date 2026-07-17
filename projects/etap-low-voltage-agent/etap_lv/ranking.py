from __future__ import annotations

from .domain import AcceptanceLimits, ScenarioResult


def violation_penalty(result: ScenarioResult, limits: AcceptanceLimits) -> float:
    """Return a dimensionless penalty for infeasible scenarios.

    Voltage deficit is weighted strongly because the primary task is low-voltage
    governance. Loading and unbalance excesses remain explicit constraints.
    """

    voltage = max(0.0, limits.min_voltage_pu - result.min_voltage_pu) * 10_000
    loading = max(0.0, result.max_loading_pct - limits.max_loading_pct) * 10
    unbalance = max(0.0, result.max_unbalance_pct - limits.max_unbalance_pct) * 20
    return voltage + loading + unbalance


def rank_results(
    results: list[ScenarioResult], limits: AcceptanceLimits
) -> list[ScenarioResult]:
    """Place compliant, low-cost solutions first; rank failures by severity."""

    return sorted(
        results,
        key=lambda item: (
            not item.is_compliant(limits),
            violation_penalty(item, limits),
            item.cost_cny,
            -item.min_voltage_pu,
            item.name,
        ),
    )
