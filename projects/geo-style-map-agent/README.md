# Geo Style Map Agent

把“AI 凭空画地图”改造成“真实 GIS 数据定骨架、图像模型只负责风格”的可运行 MVP。

当前版本先完成最关键的一层：

- 地点名称或精确 bbox 输入
- Nominatim 地理编码（可绕过）
- Overpass 拉取道路、水系、建筑、公园和咖啡 POI
- 生成拓扑稳定、可编辑的 SVG
- 自动生成图像模型风格化提示包
- 内置 `sketch`、`clean`、`blueprint` 三种底图主题
- API 结果本地缓存
- 自动保留 OpenStreetMap 署名

> 当前状态：MVP。它保证“底图结构来自真实 OSM 数据”，但还没有直接绑定某一家图像生成 API。下一步再接 OpenAI Image、Qwen-Image 或其他图生图后端。

## 1. 安装

需要 Python 3.11+。

```bash
cd projects/geo-style-map-agent
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. 设置 User-Agent

使用公共 Nominatim 和 Overpass 服务时，要提供能识别应用的 User-Agent，建议带联系方式：

```bash
export GEO_STYLE_MAP_USER_AGENT='geo-style-map-agent/0.1 (you@example.com)'
```

公共 Nominatim 只适合轻量、人工触发的查询。本项目已实现缓存并限制单次未缓存请求后的间隔；批量、定时、商业用途应改用自建或商业服务。

## 3. 生成南山咖啡地图

```bash
geo-style-map "深圳南山科技园" \
  --radius-m 1800 \
  --poi cafe \
  --theme sketch \
  --title "南山咖啡打卡地图"
```

输出：

```text
out/map.svg
out/prompt.md
```

直接用浏览器打开 `out/map.svg`，也可以导入 PPT、Figma、Illustrator 或 Inkscape。

## 4. 使用精确 bbox

已知 GIS 范围时建议直接传 bbox，避免地点解析的不确定性：

```bash
geo-style-map \
  --bbox "22.5100,113.9100,22.5500,113.9500" \
  --poi cafe \
  --theme clean \
  --title "项目选址分析图"
```

bbox 顺序固定为：

```text
south,west,north,east
```

## 5. 与图像模型配合

`out/map.svg` 是事实底图，`out/prompt.md` 是风格化约束。正确流程是：

```text
OSM 数据
  → SVG 几何底图
  → 图生图/受控编辑
  → 手绘地图、旅游地图、汇报图
```

不要只把地点名称交给图像模型重新画，因为它会改道路、错位 POI 或编造地名。

## 6. CLI 参数

```bash
geo-style-map --help
```

常用参数：

- `--radius-m`：地点中心周围半径
- `--bbox`：精确范围
- `--poi cafe|none`
- `--theme sketch|clean|blueprint`
- `--max-poi`：最多抓取的咖啡 POI
- `--max-labels`：最多显示的文字标签
- `--nominatim-endpoint`：替换地理编码服务
- `--overpass-endpoint`：替换 OSM 查询服务

## 7. 测试

```bash
python -m pytest
```

测试不访问网络，覆盖 bbox、Overpass 查询构造、数据归一化与 SVG 输出。

## 8. 数据与署名

地图数据来自 OpenStreetMap。对外使用生成物时必须保留：

```text
© OpenStreetMap contributors
```

并说明数据按 ODbL 提供。不得从高德、Google Maps 等受版权保护的地图中抄录或描摹数据，再混入 OSM 数据。

## 下一阶段

- 接入图像生成后端适配器
- 支持高德坐标纠偏与合法授权数据源
- 支持电网线路、变电站、台区等自定义 GeoJSON 图层
- 输出 PPT 友好的 16:9 SVG/PNG
- 增加 Web 界面和“地图生成 Skill”一键调用
