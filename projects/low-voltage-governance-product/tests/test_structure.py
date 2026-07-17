from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "prototype" / "index.html"
APP = ROOT / "prototype" / "app.js"
STYLE = ROOT / "prototype" / "styles.css"
CATALOG = ROOT / "data" / "governance_catalog.v0.1.json"
KNOWLEDGE = ROOT / "docs" / "domain-knowledge-v0.1.md"


class PrototypeStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = INDEX.read_text(encoding="utf-8")
        cls.js = APP.read_text(encoding="utf-8")
        cls.css = STYLE.read_text(encoding="utf-8")
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.knowledge = KNOWLEDGE.read_text(encoding="utf-8")

    def test_required_views_exist(self) -> None:
        required = [
            "view-dashboard",
            "view-detail",
            "view-diagnosis",
            "view-measures",
            "view-comparison",
            "view-workorder",
        ]
        for view_id in required:
            with self.subTest(view_id=view_id):
                self.assertIn(f'id="{view_id}"', self.html)

    def test_management_and_engineering_are_separated(self) -> None:
        self.assertIn('id="tab-management"', self.html)
        self.assertIn('id="tab-engineering"', self.html)
        self.assertIn("管理措施", self.html)
        self.assertIn("工程治理", self.html)

    def test_demo_disclaimer_is_visible(self) -> None:
        self.assertIn("所有点位、参数、诊断及方案均为模拟数据", self.html)
        self.assertIn("未接入真实现场数据和 ETAP 正式计算", self.html)

    def test_interactions_are_wired(self) -> None:
        for token in [
            "start-diagnosis",
            "measure-toggle",
            "select-plan",
            "create-workorder",
            "print-report",
        ]:
            with self.subTest(token=token):
                self.assertIn(token, self.html + self.js)

    def test_assets_exist_and_are_nontrivial(self) -> None:
        self.assertGreater(len(self.html), 10_000)
        self.assertGreater(len(self.css), 8_000)
        self.assertGreater(len(self.js), 3_000)

    def test_catalog_has_five_professional_cause_categories(self) -> None:
        categories = self.catalog["cause_categories"]
        self.assertEqual(5, len(categories))
        self.assertEqual(
            {
                "source_side",
                "network_side",
                "transformer_side",
                "load_side",
                "operations_side",
            },
            {item["id"] for item in categories},
        )
        for category in categories:
            self.assertTrue(category["causes"])
            self.assertTrue(category["evidence"])

    def test_catalog_separates_management_and_engineering_measures(self) -> None:
        measures = self.catalog["measures"]
        classes = {measure["class"] for measure in measures}
        self.assertEqual({"management", "engineering"}, classes)
        self.assertTrue(all(0 <= measure["priority_level"] <= 4 for measure in measures))
        self.assertTrue(all(measure["applicable_when"] for measure in measures))
        self.assertTrue(all(measure["requires"] for measure in measures))

    def test_unverified_cases_cannot_look_verified(self) -> None:
        case_leads = self.catalog["case_leads"]
        self.assertTrue(case_leads)
        self.assertTrue(
            all(case["verification_status"] == "unverified" for case in case_leads)
        )
        self.assertIn("未核验前不得", self.knowledge)


if __name__ == "__main__":
    unittest.main()
