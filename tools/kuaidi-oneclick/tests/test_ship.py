import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ship import build_param, make_sign, parse_sentence


class ShipTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "sender": {
                "name": "李四",
                "mobile": "13900139000",
                "address": "广东省佛山市顺德区陈村镇测试路1号",
            },
            "callback_url": "https://example.com/kuaidi100/callback",
            "default_cargo": "文件",
            "default_weight": "1",
        }

    def test_sign_is_uppercase_md5(self):
        sign = make_sign('{"a":1}', "1576123932000", "key", "secret")
        self.assertEqual(len(sign), 32)
        self.assertEqual(sign, sign.upper())
        self.assertEqual(sign, "80BBFB1A2ADDBACDE56E74C96E984E3B")

    def test_parse_recommended_sentence(self):
        order = parse_sentence(
            "顺丰到付；明天09:00-11:00；收件人张三；手机13800138000；"
            "地址广东省深圳市南山区科技园1号；物品文件；重量1kg；备注易碎"
        )
        self.assertEqual(order.kuaidicom, "shunfeng")
        self.assertEqual(order.payment, "CONSIGNEE")
        self.assertEqual(order.rec_name, "张三")
        self.assertEqual(order.weight, "1")
        self.assertEqual(order.day_type, "明天")
        self.assertEqual(order.pickup_start, "09:00")
        self.assertEqual(order.pickup_end, "11:00")
        self.assertEqual(order.remark, "易碎")

    def test_jin_converts_to_kg(self):
        order = parse_sentence(
            "中通寄付；收件人王五；手机13700137000；地址北京市朝阳区测试路2号；物品衣服；重量3斤"
        )
        self.assertEqual(order.weight, "1.5")

    def test_same_content_same_order_id(self):
        sentence = "顺丰到付；收件人张三；手机13800138000；地址广东省深圳市南山区科技园1号；物品文件；重量1kg"
        order = parse_sentence(sentence)
        first = build_param(self.config, order)
        second = build_param(self.config, order)
        self.assertEqual(first["thirdOrderId"], second["thirdOrderId"])
        self.assertLessEqual(len(first["thirdOrderId"]), 32)

    def test_force_new_changes_order_id(self):
        sentence = "顺丰到付；收件人张三；手机13800138000；地址广东省深圳市南山区科技园1号；物品文件；重量1kg"
        order = parse_sentence(sentence)
        first = build_param(self.config, order, force_new=True)
        second = build_param(self.config, order, force_new=True)
        self.assertNotEqual(first["thirdOrderId"], second["thirdOrderId"])


if __name__ == "__main__":
    unittest.main()
