# Wechat Flow Agent

面向中文工作群的信息流整理 MVP。它把群聊消息转换为四类可操作结果：**重点摘要、待办、风险、决策**。

第一版坚持 local-first：不登录个人微信、不注入客户端、不调用外部模型，先把消息分析内核、输入协议和本地界面跑通。

## 已实现

- JSON 消息导入；
- 中文规则分析器；
- 待办负责人和时间线索抽取；
- 高/中风险识别；
- 决策与未决问题提取；
- 本地 Web 看板；
- CLI Markdown/JSON 输出；
- 标准库单元测试，无运行时第三方依赖。

## 运行

要求 Python 3.11+。

```bash
cd projects/wechat-flow-agent
python -m unittest discover -s tests -v
python -m wechat_flow_agent.cli demo
python -m wechat_flow_agent.app
```

打开 `http://127.0.0.1:8765`。

也可以安装为命令：

```bash
python -m pip install -e .
wechat-flow demo
wechat-flow analyze data/demo_messages.json --json
```

## 输入协议

```json
{
  "messages": [
    {
      "id": "m1",
      "group": "项目群",
      "sender": "项目经理",
      "timestamp": "2026-07-16 09:00",
      "text": "明天提交报告，张三负责补架构图。"
    }
  ]
}
```

## 合规边界

- 不在未经群成员授权时采集、保存或上传聊天记录；
- 不使用个人微信非官方注入、Hook 或模拟协议作为默认生产方案；
- 原始消息与分析结果默认留在本机；
- 企业场景优先接企业微信官方接口、审计能力和私有模型；
- 接入第三方模型前必须完成脱敏、最小化传输和留存策略配置。

## 下一阶段

1. 增加企业微信/导出文件适配器；
2. 增加 SQLite 增量存储与去重；
3. 接入可选的 OpenAI-compatible 私有模型；
4. 增加“与我相关”“需立即处理”“项目状态变化”三层排序；
5. 输出日摘要、周报、工单和日历事件。

架构与路线见 [`docs/architecture.md`](docs/architecture.md)。
