# Portable Assistant

状态：**V0.1 可运行骨架（过程稿）**。

这个项目不是复制或“越狱”任何托管模型，而是把真正属于用户的部分从单一平台中拆出来：

- 模型调用入口可替换；
- OpenAI、Anthropic、Gemini 可按优先级故障切换；
- 记忆以本地 JSONL 保存，可确认、归档和导出；
- Skills 以普通 Markdown 文件保存；
- 身份原则、项目资产和操作规则保留在用户自己的仓库里；
- API 密钥只从环境变量读取，不进入仓库。

## 当前能力

- `ask`：调用指定模型或按优先级自动切换；
- `doctor`：检查配置、密钥、模型名、记忆目录和 Skills；
- `remember`：写入一条本地记忆，默认状态为 `draft`；
- `confirm-memory`：人工确认后才将记忆标记为 `confirmed`；
- `memories`：查看已有记忆；
- `export-memory`：导出可迁移的 Markdown 上下文；
- `skills`：列出本地 Skills；
- `--skill`：在单次请求中显式加载 Skill；
- `--memory-limit`：只注入最近若干条已确认记忆。

## 快速开始

要求 Python 3.11 或更高版本。

```bash
cd projects/portable-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp config.example.json config.local.json
cp .env.example .env.local
```

编辑 `.env.local`，然后手动导入环境变量：

```bash
set -a
source .env.local
set +a
```

先检查：

```bash
pa --config config.local.json doctor
```

发起请求：

```bash
pa --config config.local.json ask "把今天的项目进展整理成三条结论"
```

只使用某个供应商：

```bash
pa --config config.local.json ask --provider anthropic "检查这段方案的逻辑漏洞"
```

显式加载 Skill：

```bash
pa --config config.local.json ask --skill truth-first "评审这份技术结论"
```

写入记忆。未加 `--confirmed` 时，记忆只是过程稿，不会自动注入模型：

```bash
pa --config config.local.json remember \
  --title "仓库约定" \
  --tag collaboration \
  "过程稿不得被当作最终定稿。"

pa --config config.local.json confirm-memory <memory-id>
```

导出：

```bash
pa --config config.local.json export-memory --output exports/memory.md
```

## 配置原则

`config.example.json` 中不固定任何“最新模型名”。模型标识通过环境变量提供，避免代码因供应商改名或下线模型而静默失效。

故障切换只在以下情况下发生：

1. 当前供应商未配置；
2. 请求失败、超时或响应格式异常；
3. 用户没有使用 `--provider` 锁定单一供应商。

所有失败原因都会输出到标准错误，不会假装请求成功。

## 目录

```text
portable-assistant/
├── config.example.json
├── identity/core.md
├── skills/<skill-name>/SKILL.md
├── src/portable_assistant/
├── tests/
└── data/                 # 本地运行时生成，默认不提交
```

## 边界

- V0.1 只实现文本请求，不实现网页操作、代码执行或自主后台任务；
- 不导出平台内部隐藏推理；
- 不把聊天记录自动判定为长期记忆；
- 不承诺不同模型能够完整复现同一人格；
- 未做真实 API 联调前，不声称某个供应商已经调用成功。

真正可延续的是用户拥有的资料、规则、代码、Skills 和经过确认的记忆，而不是某个不可迁移的在线模型实例。
