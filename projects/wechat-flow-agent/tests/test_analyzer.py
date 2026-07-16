import unittest

from wechat_flow_agent.analyzer import analyze_messages
from wechat_flow_agent.domain import Message


class AnalyzerTest(unittest.TestCase):
    def test_extracts_action_owner_deadline_and_risk(self) -> None:
        messages = [
            Message("1", "项目群", "经理", "", "明天提交报告，张三负责补架构图。"),
            Message("2", "研发群", "后端", "", "接口挂了，今天下午3点前必须恢复。"),
        ]

        result = analyze_messages(messages)

        self.assertEqual(2, result.stats["messages"])
        self.assertGreaterEqual(len(result.actions), 2)
        self.assertEqual("张三", result.actions[0].owner)
        self.assertEqual("明天", result.actions[0].deadline)
        self.assertTrue(any(risk.level == "high" for risk in result.risks))

    def test_detects_decision_and_question(self) -> None:
        messages = [
            Message("1", "研发群", "负责人", "", "结论：先做本地导入，暂缓微信自动登录。"),
            Message("2", "研发群", "产品", "", "谁来确认授权说明？"),
        ]

        result = analyze_messages(messages)

        self.assertEqual(1, len(result.decisions))
        self.assertEqual(1, len(result.questions))

    def test_empty_input_is_supported(self) -> None:
        result = analyze_messages([])
        self.assertEqual(0, result.stats["messages"])
        self.assertEqual([], result.actions)


if __name__ == "__main__":
    unittest.main()
