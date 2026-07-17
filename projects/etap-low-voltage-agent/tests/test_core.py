import unittest

from etap_lv.domain import AcceptanceLimits, ScenarioResult
from etap_lv.ranking import rank_results
from etap_lv.runner import extract_path, normalize_result, render_template


class RankingTest(unittest.TestCase):
    def test_compliant_low_cost_solution_ranks_first(self) -> None:
        limits = AcceptanceLimits()
        results = [
            ScenarioResult("a", "便宜但不合格", 10, 0.88, 90, 8),
            ScenarioResult("b", "合格方案", 100, 0.92, 95, 10),
            ScenarioResult("c", "更贵合格方案", 200, 0.95, 80, 5),
        ]

        ranked = rank_results(results, limits)

        self.assertEqual(["b", "c", "a"], [item.scenario_id for item in ranked])

    def test_reports_all_constraint_violations(self) -> None:
        result = ScenarioResult("a", "基准", 0, 0.85, 110, 20)
        violations = result.violations(AcceptanceLimits())
        self.assertEqual(3, len(violations))


class MappingTest(unittest.TestCase):
    def test_extract_and_template_rendering(self) -> None:
        context = {"scenario": {"name": "换相", "id": "s1"}}
        self.assertEqual("换相", extract_path(context, "scenario.name"))
        self.assertEqual(
            {"scenario": "s1", "label": "run-换相"},
            render_template(
                {"scenario": "${scenario.id}", "label": "run-${scenario.name}"},
                context,
            ),
        )

    def test_normalizes_configured_response_paths(self) -> None:
        response = {
            "result": {
                "summary": {
                    "umin": 0.93,
                    "loading": 88,
                    "unbalance": 7,
                }
            }
        }
        scenario = {"id": "s1", "name": "换相", "cost_cny": 10000}
        result = normalize_result(
            response,
            scenario,
            {
                "min_voltage_pu": "result.summary.umin",
                "max_loading_pct": "result.summary.loading",
                "max_unbalance_pct": "result.summary.unbalance",
            },
        )
        self.assertTrue(result.is_compliant(AcceptanceLimits()))
        self.assertEqual("etap-api", result.source)


if __name__ == "__main__":
    unittest.main()
