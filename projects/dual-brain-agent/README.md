# Dual-Brain Agent MVP

一个可直接运行的“双脑智能体”最小闭环：

- **右脑 Agent**：高温度发散、类比、提出候选路径。
- **左脑 Agent**：低温度审查、验证约束、识别失败模式。
- **仲裁 Agent**：融合两侧结果，删除无依据内容，输出可执行决策。
- **可观测 Web UI**：同时展示左右脑与仲裁结果、置信度和运行耗时。
- **零配置 Demo 模式**：没有模型密钥也能跑通完整流程。
- **OpenAI 兼容接口**：可接 OpenAI、代理网关或其他兼容 `/chat/completions` 的服务。

## 架构

```text
用户任务
   │
   ├───────────────┐
   ▼               ▼
右脑 Agent      左脑 Agent
发散/探索       验证/约束
   └───────┬───────┘
           ▼
        仲裁 Agent
           ▼
      可执行决策
```

左右脑并行执行，仲裁器在两侧结果返回后运行。所有角色统一输出结构化 JSON，并保留原始模型响应，便于追踪和复盘。

## 运行

要求 Python 3.11+，无第三方依赖。

```bash
cd projects/dual-brain-agent
python -m dual_brain.server
```

浏览器打开：`http://127.0.0.1:8765`

默认使用 Demo 模式。它用于验证交互和调度链路，不代表真实模型能力。

## 接入真实模型

```bash
export DUAL_BRAIN_MODE=openai
export LLM_BASE_URL=https://your-endpoint.example/v1
export LLM_API_KEY=replace-me
export LLM_MODEL=replace-me
python -m dual_brain.server
```

`LLM_API_KEY` 可为空，以兼容无需鉴权的局域网模型服务；`LLM_BASE_URL` 与 `LLM_MODEL` 必须提供。

## API

### `POST /api/run`

```json
{
  "task": "为故障诊断智能体设计两周 MVP",
  "context": "已有拓扑、稳态量和告警数据",
  "constraints": ["不能虚构接口", "必须可验收"]
}
```

响应包含：`right_brain`、`left_brain`、`arbiter`、`duration_ms`、`mode` 与 `run_id`。

### `GET /api/health`

返回服务状态和当前 provider 模式。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 下一阶段

1. JSON Schema 强校验与自动重试。
2. 会话记忆和任务状态持久化。
3. MCP/工具调用，由左脑审查工具结果的证据链。
4. 人工否决、重新仲裁和“只保留已验证事实”开关。
5. 面向电网场景的专用 Brain：方案脑、物理校核脑、规程脑、调度仲裁器。
