# GPTchatAllRepo

本仓库是我与 ChatGPT 协作产生的项目代码、技术文档和阶段性成果的统一存放处。

## 当前项目

- [`projects/sleep-sense`](projects/sleep-sense)：基于 Android 公开传感器 API 的“躺下/睡眠准备姿态”检测与自动化触发 Demo。
- [`projects/wechat-flow-agent`](projects/wechat-flow-agent)：面向中文工作群的本地信息流助手，提取摘要、待办、风险、决策和未决问题。
- [`projects/etap-low-voltage-agent`](projects/etap-low-voltage-agent)：面向低压配电网问题点的 ETAP 批量仿真、指标校核与治理方案排序 PoC。
- [`projects/low-voltage-governance-product`](projects/low-voltage-governance-product)：低电压治理智能决策专家的产品方案、交互原型及单点治理闭环设计。
- [`projects/mac-readonly-doc-viewer`](projects/mac-readonly-doc-viewer)：独立的 macOS 真只读文档查看器，使用系统 Quick Look 预览 Word/PDF，界面不提供正文编辑与保存入口。
- [`projects/wps-mac-reader-addon`](projects/wps-mac-reader-addon)：WPS Mac 阅读加载项实验；在用户当前 WPS 构建中出现“选项卡可见但按钮完全不执行”，已停止作为推荐方案。

## 仓库约定

- 每个独立项目放在 `projects/<project-name>/`。
- 跨项目技术文档放在 `docs/`。
- 重要对话决策与阶段结论放在 `docs/conversations/`，只记录可复用结论，不保存私密推理过程。
- 过程稿明确标注状态；未经确认不得视作最终定稿。
- 可以暂时没有结果，但不得编造实现状态、测试结果或数据。

## 协作方式

创建 GitHub 仓库由仓库所有者完成；仓库内的初始化、代码实现、文档维护、提交和后续迭代可由 ChatGPT/Codex 执行。
