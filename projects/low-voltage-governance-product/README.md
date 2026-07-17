# 低电压治理智能决策专家

状态：**阶段性产品定义与交互原型 V0.1，不是最终定稿。**

本项目面向配网运维、供电所和低电压专项治理人员，将低电压问题处理组织为一条可审计的业务闭环：

```text
监测/导入数据 → 识别问题 → 分析成因 → 管理措施 → 工程措施 → 方案比选 → 工单/报告 → 治理后复核
```

## 当前交付

- 一周方案底稿：[`docs/product-plan-v0.1.md`](docs/product-plan-v0.1.md)
- 两周原型范围：[`docs/prototype-scope.md`](docs/prototype-scope.md)
- 专业知识框架：[`docs/domain-knowledge-v0.1.md`](docs/domain-knowledge-v0.1.md)
- 结构化成因与措施目录：[`data/governance_catalog.v0.1.json`](data/governance_catalog.v0.1.json)
- 软硬一体机选型：[`docs/hardware-selection-v0.1.md`](docs/hardware-selection-v0.1.md)
- 华强北询价与验收清单：[`docs/huaqiangbei-purchase-checklist.md`](docs/huaqiangbei-purchase-checklist.md)
- 可编辑采购 BOM：[`data/hardware_bom.v0.1.csv`](data/hardware_bom.v0.1.csv)
- 可直接打开的静态交互原型：[`prototype/index.html`](prototype/index.html)
- 原型与知识目录校验：[`tests/test_structure.py`](tests/test_structure.py)

## 知识体系

当前知识框架采用五类低电压成因：

1. 电源侧；
2. 网架侧；
3. 配变侧；
4. 用户与负荷侧；
5. 运行管理侧。

治理措施同时按两套维度组织：

- 业务维度：管理措施、工程措施；
- 技术维度：源、网、荷、储。

默认治理顺序为：数据与安全校核 → 低成本管理措施 → 轻量工程 → 常规网架与容量改造 → 新型灵活调节技术。该顺序只是初始推荐逻辑，正式项目需由通科及专业人员确认。

## 硬件样机

第一台硬件定义为华强北可快速集成的 **15.6 英寸手提箱式展示/验证终端**：

- 32GB+1TB x86 迷你主机；
- Windows 11 Pro；
- 15.6 英寸 1080P 电容触摸屏；
- 隔离 USB-RS485；
- Modbus 安全模拟器；
- 三色状态灯、三个实体按键和旋钮；
- 可选外接三相导轨采集箱；
- 主控制台内不暴露 220/380V 接线。

样机目标预算为 5500—7500 元，加真实三相采集箱后约 6500—9000 元。第一台只验证产品形态和采集闭环，不等同于可直接部署的生产级现场终端。

## 产品原则

1. **用户先于技术**：用户看到的是问题、依据、建议、效果和工单，而不是 ETAP、模型或程序细节。
2. **管理与工程分层**：先恢复合格电压和保障供电，再判断是否需要根治性工程。
3. **不完整数据不瞎补**：缺失数据必须标识来源、区间、置信度和对结论的影响。
4. **AI 不直接替代责任人**：系统输出建议，用户确认后才能生成工单或进入实施流程。
5. **仿真引擎可替换**：ETAP 是后端适配器之一，产品层不与单一软件绑定。
6. **结果可追溯**：诊断结论、规则命中、仿真版本、参数和人工修改均保留记录。
7. **案例先核验再引用**：AI 汇总中的案例名称、治理效果和具体数值在找到原始来源前只作为线索。
8. **展示机与现场设备分离**：高压/市电采集放在独立防护箱，由有资质人员接线；主机只接隔离通信接口。

## 运行原型

无需安装依赖，直接用浏览器打开：

```text
projects/low-voltage-governance-product/prototype/index.html
```

也可在项目目录启动任意静态文件服务器：

```bash
python -m http.server 8080
```

然后访问 `http://127.0.0.1:8080/prototype/`。

## 原型说明

原型中的“佛山陈村北一号台区”及全部数值均为**演示数据**，只用于验证产品交互，不代表现场实测、ETAP 计算或正式治理结论。

## 与 ETAP PoC 的关系

已有项目 [`../etap-low-voltage-agent`](../etap-low-voltage-agent) 负责仿真接口探测和结果适配。本项目负责用户业务流程、产品交互、治理知识体系和报告输出。后续通过统一 `StudyResult` 数据协议连接，避免 UI 直接依赖 ETAP。
