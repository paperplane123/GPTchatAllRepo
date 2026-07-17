from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "prototype" / "index.html"
APP = ROOT / "prototype" / "app.js"
STYLE = ROOT / "prototype" / "styles.css"


class PrototypeStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = INDEX.read_text(encoding="utf-8")
        cls.js = APP.read_text(encoding="utf-8")
        cls.css = STYLE.read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
