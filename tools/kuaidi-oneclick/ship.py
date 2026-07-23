#!/usr/bin/env python3
"""快递100上门取件（线下支付）一句话下单 CLI。

安全设计：
- 默认仅预览，不发起真实请求；必须显式传入 --submit。
- key/secret 只从环境变量读取，不写入配置文件。
- 手机号在终端预览中默认脱敏。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROD_URL = "https://order.kuaidi100.com/order/corderapi.do"
TEST_URL = "http://e-test.kuaidilab.com/api/order/corderapi.do"
DEFAULT_CONFIG = Path.home() / ".kuaidi-oneclick" / "config.json"

CARRIERS = {
    "顺丰": "shunfeng",
    "顺丰速运": "shunfeng",
    "京东": "jd",
    "京东物流": "jd",
    "德邦": "debangkuaidi",
    "德邦快递": "debangkuaidi",
    "圆通": "yuantong",
    "圆通快递": "yuantong",
    "中通": "zhongtong",
    "中通快递": "zhongtong",
    "顺丰快运": "shunfengkuaiyun",
    "顺心捷达": "sxjdfreight",
    "跨越": "kuayue",
    "跨越速运": "kuayue",
    "EMS": "ems",
    "ems": "ems",
}


class UserInputError(ValueError):
    pass


@dataclass(frozen=True)
class Sender:
    name: str
    mobile: str
    address: str


@dataclass(frozen=True)
class ParsedOrder:
    kuaidicom: str
    rec_name: str
    rec_mobile: str
    rec_address: str
    cargo: str
    payment: str
    weight: str
    day_type: str | None
    pickup_start: str | None
    pickup_end: str | None
    remark: str | None


def md5_upper(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest().upper()


def compact_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def make_sign(param_json: str, timestamp_ms: str, key: str, secret: str) -> str:
    return md5_upper(param_json + timestamp_ms + key + secret)


def normalize_time(hour: str, minute: str | None) -> str:
    h = int(hour)
    m = int(minute or "00")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise UserInputError(f"非法时间：{hour}:{minute or '00'}")
    return f"{h:02d}:{m:02d}"


def parse_sentence(text: str, default_cargo: str = "文件", default_weight: str = "1") -> ParsedOrder:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        raise UserInputError("下单语句不能为空")

    carrier_code = None
    for label in sorted(CARRIERS, key=len, reverse=True):
        if label in cleaned:
            carrier_code = CARRIERS[label]
            break
    if carrier_code is None:
        raise UserInputError("未识别到快递公司，例如：顺丰、京东、德邦、圆通、中通、EMS")

    payment = "CONSIGNEE" if "到付" in cleaned else "SHIPPER"
    day_type = next((x for x in ("今天", "明天", "后天") if x in cleaned), None)
    time_match = re.search(
        r"(?<!\d)(\d{1,2})(?::(\d{2}))?\s*(?:-|—|~|～|到|至)\s*(\d{1,2})(?::(\d{2}))?(?!\d)",
        cleaned,
    )
    pickup_start = pickup_end = None
    if time_match:
        pickup_start = normalize_time(time_match.group(1), time_match.group(2))
        pickup_end = normalize_time(time_match.group(3), time_match.group(4))
        if pickup_start >= pickup_end:
            raise UserInputError("预约截止时间必须晚于起始时间")

    name_match = re.search(r"(?:收件人(?:姓名)?|寄给)\s*[:：]?\s*([\u4e00-\u9fffA-Za-z·.]{2,30})", cleaned)
    mobile_match = re.search(r"(?:收件人)?(?:手机|手机号|电话)\s*[:：]?\s*(1\d{10})", cleaned)
    address_match = re.search(
        r"(?:收件地址|地址)\s*[:：]?\s*(.+?)(?=(?:[，,；;]\s*(?:物品|货物|重量|备注|今天|明天|后天|取件|付款|寄付|到付)\s*[:：]?)|$)",
        cleaned,
    )

    if not (name_match and mobile_match and address_match):
        compact_match = re.search(
            r"寄给\s*([\u4e00-\u9fffA-Za-z·.]{2,30})\s*[,， ]+\s*(1\d{10})\s*[,， ]+\s*(.+?)(?=(?:[，,；;]\s*(?:物品|货物|重量|备注|今天|明天|后天|取件|付款|寄付|到付))|$)",
            cleaned,
        )
        if compact_match:
            rec_name, rec_mobile, rec_address = (x.strip() for x in compact_match.groups())
        else:
            if not name_match:
                raise UserInputError("未识别到收件人姓名，建议写“收件人张三”")
            if not mobile_match:
                raise UserInputError("未识别到收件人手机号，建议写“手机13800138000”")
            if not address_match:
                raise UserInputError("未识别到收件地址，建议写“地址广东省……”")
            raise AssertionError("unreachable")
    else:
        rec_name = name_match.group(1).strip()
        rec_mobile = mobile_match.group(1).strip()
        rec_address = address_match.group(1).strip()

    cargo_match = re.search(r"(?:物品|货物)\s*[:：]?\s*([^，,；;]+)", cleaned)
    cargo = cargo_match.group(1).strip() if cargo_match else default_cargo
    cargo = re.sub(r"\s*(?:重量)?\s*\d+(?:\.\d+)?\s*(?:kg|公斤|千克|斤)\s*$", "", cargo, flags=re.I).strip() or default_cargo

    kg_match = re.search(r"(?:重量\s*[:：]?\s*)?(\d+(?:\.\d+)?)\s*(?:kg|公斤|千克)\b", cleaned, re.I)
    jin_match = re.search(r"(?:重量\s*[:：]?\s*)?(\d+(?:\.\d+)?)\s*斤\b", cleaned)
    if kg_match:
        weight = f"{float(kg_match.group(1)):g}"
    elif jin_match:
        weight = f"{float(jin_match.group(1)) / 2:g}"
    else:
        weight = str(default_weight)

    remark_match = re.search(r"备注\s*[:：]?\s*(.+?)(?=(?:[，,；;]\s*(?:物品|货物|重量|今天|明天|后天|取件|付款|寄付|到付))|$)", cleaned)
    remark = remark_match.group(1).strip() if remark_match else None

    return ParsedOrder(
        kuaidicom=carrier_code,
        rec_name=rec_name,
        rec_mobile=rec_mobile,
        rec_address=rec_address,
        cargo=cargo,
        payment=payment,
        weight=weight,
        day_type=day_type,
        pickup_start=pickup_start,
        pickup_end=pickup_end,
        remark=remark,
    )


def validate_mobile(value: str, label: str) -> None:
    if not re.fullmatch(r"1\d{10}", value):
        raise UserInputError(f"{label}必须是11位中国大陆手机号")


def validate_utf8_length(value: str, limit: int, label: str) -> None:
    size = len(value.encode("utf-8"))
    if size > limit:
        raise UserInputError(f"{label}超过{limit}字节，当前{size}字节")


def load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UserInputError(f"配置文件不存在：{path}。请先运行 python ship.py --init") from exc
    except json.JSONDecodeError as exc:
        raise UserInputError(f"配置文件不是合法JSON：{path}: {exc}") from exc

    sender = data.get("sender") or {}
    for key in ("name", "mobile", "address"):
        if not sender.get(key):
            raise UserInputError(f"配置缺少 sender.{key}")
    if not data.get("callback_url"):
        raise UserInputError("配置缺少 callback_url（快递100下单必填，且须为公网可访问地址）")
    return data


def init_config(path: Path) -> None:
    print("仅保存寄件人和回调地址；KEY/SECRET 请放环境变量，不会写入文件。")
    sender_name = input("寄件人姓名：").strip()
    sender_mobile = input("寄件人手机号：").strip()
    sender_address = input("寄件人完整地址：").strip()
    callback_url = input("公网回调地址 callBackUrl：https://").strip()
    if callback_url and not callback_url.startswith(("http://", "https://")):
        callback_url = "https://" + callback_url

    validate_mobile(sender_mobile, "寄件人手机号")
    validate_utf8_length(sender_address, 300, "寄件地址")
    validate_utf8_length(callback_url, 200, "回调地址")

    data = {
        "sender": {"name": sender_name, "mobile": sender_mobile, "address": sender_address},
        "callback_url": callback_url,
        "default_cargo": "文件",
        "default_weight": "1",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    print(f"配置已保存：{path}")


def deterministic_order_id(param_without_id: dict[str, Any], force_new: bool) -> str:
    day = time.strftime("%Y%m%d")
    salt = uuid.uuid4().hex if force_new else ""
    digest = hashlib.sha1((compact_json(param_without_id) + salt).encode("utf-8")).hexdigest()[:20]
    return f"oc{day}{digest}"


def build_param(config: dict[str, Any], order: ParsedOrder, force_new: bool = False) -> dict[str, Any]:
    sender_cfg = config["sender"]
    sender = Sender(sender_cfg["name"], sender_cfg["mobile"], sender_cfg["address"])
    validate_mobile(sender.mobile, "寄件人手机号")
    validate_mobile(order.rec_mobile, "收件人手机号")
    validate_utf8_length(sender.address, 300, "寄件地址")
    validate_utf8_length(order.rec_address, 300, "收件地址")
    validate_utf8_length(config["callback_url"], 200, "回调地址")

    param: dict[str, Any] = {
        "kuaidicom": order.kuaidicom,
        "recManName": order.rec_name,
        "recManMobile": order.rec_mobile,
        "recManPrintAddr": order.rec_address,
        "sendManName": sender.name,
        "sendManMobile": sender.mobile,
        "sendManPrintAddr": sender.address,
        "callBackUrl": config["callback_url"],
        "cargo": order.cargo,
        "payment": order.payment,
        "weight": order.weight,
    }
    optional = {
        "remark": order.remark,
        "dayType": order.day_type,
        "pickupStartTime": order.pickup_start,
        "pickupEndTime": order.pickup_end,
    }
    param.update({k: v for k, v in optional.items() if v is not None})
    param["thirdOrderId"] = deterministic_order_id(param, force_new)
    return param


def mask_mobile(value: str) -> str:
    return value[:3] + "****" + value[-4:] if len(value) == 11 else value


def masked_param(param: dict[str, Any]) -> dict[str, Any]:
    result = dict(param)
    for key in ("recManMobile", "sendManMobile"):
        if key in result:
            result[key] = mask_mobile(str(result[key]))
    return result


def submit_order(param: dict[str, Any], key: str, secret: str, test: bool, timeout: float) -> dict[str, Any]:
    timestamp_ms = str(int(time.time() * 1000))
    param_json = compact_json(param)
    body = urllib.parse.urlencode(
        {
            "method": "cOrder",
            "key": key,
            "t": timestamp_ms,
            "sign": make_sign(param_json, timestamp_ms, key, secret),
            "param": param_json,
        }
    ).encode("utf-8")
    url = TEST_URL if test else PROD_URL
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"网络请求失败：{exc.reason}") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"接口返回非JSON：{raw[:500]}") from exc
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="快递100一句话下单。默认仅预览；传 --submit 才会真实请求。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python ship.py --init\n"
            "  python ship.py '顺丰到付；明天09:00-11:00；收件人张三；手机13800138000；地址广东省深圳市南山区某路1号；物品文件；重量1kg'\n"
            "  python ship.py '顺丰到付；明天09:00-11:00；收件人张三；手机13800138000；地址广东省深圳市南山区某路1号；物品文件；重量1kg' --submit\n"
        ),
    )
    parser.add_argument("sentence", nargs="?", help="一句话订单")
    parser.add_argument("--init", action="store_true", help="初始化寄件人和回调地址")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help=f"配置文件路径（默认 {DEFAULT_CONFIG}）")
    parser.add_argument("--submit", action="store_true", help="真实提交订单；不传则只预览")
    parser.add_argument("--test", action="store_true", help="调用快递100测试地址")
    parser.add_argument("--new-order", action="store_true", help="允许同一天创建内容完全相同的新订单")
    parser.add_argument("--show-sensitive", action="store_true", help="预览时显示完整手机号")
    parser.add_argument("--timeout", type=float, default=15.0, help="请求超时秒数，默认15")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.init:
            init_config(args.config)
            return 0
        if not args.sentence:
            raise UserInputError("请提供一句话订单，或运行 --init")

        config = load_config(args.config)
        order = parse_sentence(
            args.sentence,
            default_cargo=str(config.get("default_cargo", "文件")),
            default_weight=str(config.get("default_weight", "1")),
        )
        param = build_param(config, order, force_new=args.new_order)
        print("订单预览：")
        print(json.dumps(param if args.show_sensitive else masked_param(param), ensure_ascii=False, indent=2))

        if not args.submit:
            print("\n当前为预览模式，没有调用接口。确认无误后追加 --submit。")
            return 0

        key = os.getenv("KUAIDI100_KEY", "").strip()
        secret = os.getenv("KUAIDI100_SECRET", "").strip()
        if not key or not secret:
            raise UserInputError("真实提交前请设置环境变量 KUAIDI100_KEY 和 KUAIDI100_SECRET")

        print(f"\n正在提交到{'测试' if args.test else '正式'}环境……")
        result = submit_order(param, key, secret, test=args.test, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("result") is True:
            return 0
        return 2
    except UserInputError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"下单失败：{exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
