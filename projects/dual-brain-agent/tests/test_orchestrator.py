import json
import unittest

from dual_brain.models import TaskRequest
from dual_brain.orchestrator import DualBrainOrchestrator, parse_json_object


class FakeProvider:
    mode = "test"

    def complete(self, messages, temperature):
        system = messages[0]["content"]
        if "仲裁器" in system:
            summary = "arbiter"
        elif "右脑" in system:
            summary = "right"
        elif "左脑" in system:
            summary = "left"
        else:
            summary = "unknown"
        return json.dumps(
            {
                "summary": summary,
                "reasoning_points": ["point"],
                "risks": [],
                "recommendations": ["next"],
                "confidence": 0.8,
            }
        )


class OrchestratorTests(unittest.TestCase):
    def test_runs_two_brains_and_arbiter(self):
        result = DualBrainOrchestrator(FakeProvider()).run(TaskRequest(task="build MVP"))
        self.assertEqual(result.right_brain.summary, "right")
        self.assertEqual(result.left_brain.summary, "left")
        self.assertEqual(result.arbiter.summary, "arbiter")
        self.assertEqual(result.mode, "test")
        self.assertTrue(result.run_id)

    def test_parse_markdown_json(self):
        parsed = parse_json_object('```json\n{"summary":"ok"}\n```')
        self.assertEqual(parsed["summary"], "ok")

    def test_parse_falls_back_for_plain_text(self):
        parsed = parse_json_object("not json")
        self.assertEqual(parsed["confidence"], 0.35)
        self.assertIn("not json", parsed["summary"])

    def test_rejects_empty_task(self):
        with self.assertRaises(ValueError):
            DualBrainOrchestrator(FakeProvider()).run(TaskRequest(task="  "))


if __name__ == "__main__":
    unittest.main()
