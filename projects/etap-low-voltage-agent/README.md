# ETAP 低电压治理自动化 PoC

面向广东低压配电网问题点的 ETAP 批量仿真与治理方案排序工具。目标流程：

```text
问题点数据 -> ETAP 基准潮流 -> 多方案批量仿真 -> 指标校核 -> 经济性排序 -> 单点报告
```

## 当前状态

**阶段性 PoC，不是已完成的 ETAP 实机验证。**

已经完成：

- ETAP REST API / Swagger 连通性探测；
- 可配置的同步研究调用适配器；
- 低电压、配变负载率、三相不平衡约束校核；
- 合规方案按成本优先排序；
- 示例数据、命令行入口和单元测试。

尚未完成：

- 尚未连接一台已安装并授权 `etapPy / etapAPI` 的 Windows ETAP 实例；
- 尚未拿到真实 `.oti` 工程、研究案例和最终报告模板；
- ETAP 不同版本暴露的具体 REST 路由需通过该机器的 Swagger 页面确认，仓库中不臆造接口名称。

ETAP 官方说明，etapPy 可批量执行研究、读取项目数据、生成报告，并可在 ETAP 内部或外部运行脚本；etapAPI 是由 DataHub 暴露的 RESTful API。真实运行仍要求 ETAP 软件、相应模块和许可证。

## 快速运行

要求 Python 3.11+，运行时仅使用标准库。

```bash
cd projects/etap-low-voltage-agent
python -m unittest discover -s tests -v
python -m etap_lv.cli demo
```

输出会对示例中的“基准、换相、换线、配变增容”方案进行约束校核与排序。示例结果只用于验证程序流程，不代表广州真实台区。

## 接上真实 ETAP

复制配置文件：

```bash
cp config/etap.example.json config/etap.local.json
```

配置 ETAP DataHub / etapAPI 地址和令牌后，先探测 Swagger：

```bash
export ETAP_API_TOKEN='由 ETAP 管理员提供的令牌'
python -m etap_lv.cli probe --config config/etap.local.json
```

探测命令会：

1. 尝试读取 OpenAPI/Swagger 文档；
2. 列出包含 `study`、`load flow`、`scenario`、`bus` 等关键词的候选接口；
3. 不修改 ETAP 项目，也不触发研究计算。

确认真实接口后，把同步研究路由和结果字段映射填入配置，再运行：

```bash
python -m etap_lv.cli run \
  --config config/etap.local.json \
  --study data/study_request.example.json
```

## 最小实机资料

真正跑第一遍至少需要：

- ETAP 版本、安装机器和可用许可证模块；
- DataHub / etapAPI 或 etapPy 可调用环境；
- 一个真实低电压问题点的 `.oti` 工程；
- 已配置好的 Load Flow 或 Unbalanced Load Flow Study Case；
- 一个基准工况和至少一个治理方案；
- 节点电压、配变负载率、三相不平衡的结果字段定义。

## 安全边界

- 默认不关闭 TLS 校验；仅在封闭测试网使用自签名证书时显式配置；
- 令牌只从环境变量读取，不写入仓库；
- 实机运行前先复制工程，禁止直接在唯一生产模型上批量改参数；
- 每次结果记录 ETAP 项目、修订、配置、研究案例和输入参数，保证可追溯。
