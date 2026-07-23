from __future__ import annotations

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .osm import BoundingBox


@dataclass(frozen=True)
class Theme:
    background: str
    paper: str
    water: str
    park: str
    building: str
    road: str
    road_major: str
    text: str
    poi: str
    border: str


THEMES: dict[str, Theme] = {
    "sketch": Theme(
        background="#eee6d4",
        paper="#f8f1df",
        water="#9fc8d8",
        park="#b8cf9b",
        building="#e0c8aa",
        road="#725f4f",
        road_major="#3f342c",
        text="#352d28",
        poi="#315d86",
        border="#7e6d58",
    ),
    "clean": Theme(
        background="#f3f5f7",
        paper="#ffffff",
        water="#b8dff1",
        park="#cfe6be",
        building="#e7e7e7",
        road="#a0a5aa",
        road_major="#535a61",
        text="#202428",
        poi="#145da0",
        border="#d2d6da",
    ),
    "blueprint": Theme(
        background="#18334c",
        paper="#18334c",
        water="#356b8d",
        park="#315f5c",
        building="#294c66",
        road="#80a9c7",
        road_major="#d6edf9",
        text="#eef8ff",
        poi="#ffce71",
        border="#7db5d7",
    ),
}


def mercator(lon: float, lat: float) -> tuple[float, float]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    x = math.radians(lon)
    y = math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
    return x, y


class Projector:
    def __init__(
        self,
        bbox: BoundingBox,
        width: int,
        height: int,
        margin: int,
        header: int,
        footer: int,
    ) -> None:
        west_x, north_y = mercator(bbox.west, bbox.north)
        east_x, south_y = mercator(bbox.east, bbox.south)
        span_x = max(east_x - west_x, 1e-12)
        span_y = max(north_y - south_y, 1e-12)

        usable_w = width - margin * 2
        usable_h = height - margin * 2 - header - footer
        scale = min(usable_w / span_x, usable_h / span_y)

        drawn_w = span_x * scale
        drawn_h = span_y * scale
        self.offset_x = margin + (usable_w - drawn_w) / 2.0 - west_x * scale
        self.offset_y = margin + header + (usable_h - drawn_h) / 2.0 + north_y * scale
        self.scale = scale

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        x, y = mercator(lon, lat)
        return x * self.scale + self.offset_x, -y * self.scale + self.offset_y


def _points(
    geometry: Iterable[tuple[float, float]],
    project: Projector,
) -> str:
    return " ".join(
        f"{x:.2f},{y:.2f}" for x, y in (project(lon, lat) for lon, lat in geometry)
    )


def _road_width(road_class: str) -> float:
    if road_class in {"motorway", "trunk", "primary"}:
        return 4.5
    if road_class in {"secondary", "tertiary"}:
        return 3.0
    if road_class in {"residential", "living_street", "unclassified"}:
        return 1.8
    return 1.1


def _is_major(road_class: str) -> bool:
    return road_class in {
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
    }


def render_svg(
    layers: dict[str, list[dict[str, Any]]],
    bbox: BoundingBox,
    title: str,
    theme_name: str = "sketch",
    width: int = 1600,
    height: int = 1000,
    max_labels: int = 30,
) -> str:
    try:
        theme = THEMES[theme_name]
    except KeyError as exc:
        raise ValueError(f"未知主题：{theme_name}") from exc

    margin = 42
    header = 90
    footer = 44
    project = Projector(bbox, width, height, margin, header, footer)

    out: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{html.escape(title)}">'
        ),
        "<defs>",
        '<filter id="paperTexture" x="-10%" y="-10%" width="120%" height="120%">',
        '<feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="8" result="noise"/>',
        '<feColorMatrix in="noise" type="saturate" values="0" result="gray"/>',
        '<feComponentTransfer in="gray" result="faded"><feFuncA type="table" tableValues="0 0.055"/></feComponentTransfer>',
        '<feBlend in="SourceGraphic" in2="faded" mode="multiply"/>',
        "</filter>",
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="{theme.background}"/>',
        (
            f'<rect x="18" y="18" width="{width-36}" height="{height-36}" rx="20" '
            f'fill="{theme.paper}" stroke="{theme.border}" stroke-width="2" filter="url(#paperTexture)"/>'
        ),
        (
            f'<text x="{margin}" y="70" font-family="system-ui, sans-serif" '
            f'font-size="34" font-weight="700" fill="{theme.text}">{html.escape(title)}</text>'
        ),
    ]

    for item in layers.get("water", []):
        points = _points(item["geometry"], project)
        if item.get("closed"):
            out.append(
                f'<polygon points="{points}" fill="{theme.water}" opacity="0.9" '
                f'stroke="{theme.water}" stroke-width="2"/>'
            )
        else:
            out.append(
                f'<polyline points="{points}" fill="none" stroke="{theme.water}" '
                f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    for item in layers.get("parks", []):
        out.append(
            f'<polygon points="{_points(item["geometry"], project)}" fill="{theme.park}" '
            f'opacity="0.78" stroke="{theme.border}" stroke-width="0.8"/>'
        )

    for item in layers.get("buildings", []):
        out.append(
            f'<polygon points="{_points(item["geometry"], project)}" fill="{theme.building}" '
            f'opacity="0.72" stroke="{theme.border}" stroke-width="0.45"/>'
        )

    roads = sorted(
        layers.get("roads", []),
        key=lambda item: (_is_major(item.get("class", "")), _road_width(item.get("class", ""))),
    )
    for item in roads:
        road_class = item.get("class", "road")
        stroke = theme.road_major if _is_major(road_class) else theme.road
        width_px = _road_width(road_class)
        out.append(
            f'<polyline points="{_points(item["geometry"], project)}" fill="none" '
            f'stroke="{stroke}" stroke-width="{width_px:.1f}" opacity="0.92" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    labeled = 0
    for poi in layers.get("pois", []):
        x, y = project(*poi["point"])
        name = str(poi.get("name", "咖啡"))
        out.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6.2" fill="{theme.poi}" '
            f'stroke="{theme.paper}" stroke-width="2"/>'
        )
        if labeled < max_labels:
            out.append(
                f'<text x="{x+9:.2f}" y="{y-7:.2f}" font-family="system-ui, sans-serif" '
                f'font-size="13" font-weight="600" fill="{theme.text}" '
                f'paint-order="stroke" stroke="{theme.paper}" stroke-width="3" '
                f'stroke-linejoin="round">{html.escape(name)}</text>'
            )
            labeled += 1

    out.extend(
        [
            (
                f'<text x="{margin}" y="{height-27}" font-family="system-ui, sans-serif" '
                f'font-size="15" fill="{theme.text}" opacity="0.8">'
                "© OpenStreetMap contributors · Data available under ODbL"
                "</text>"
            ),
            "</svg>",
        ]
    )
    return "\n".join(out)


def write_prompt_package(
    path: Path,
    title: str,
    theme: str,
    source_svg: Path,
) -> None:
    content = f"""# 图像模型风格化指令

## 任务
将 `{source_svg.name}` 风格化为“{theme}”地图。

## 硬约束
1. 不改变道路拓扑、道路交叉关系、河流位置、建筑轮廓和 POI 坐标。
2. 不新增不存在的道路、桥梁、地名或店铺。
3. 所有文字必须可读；无法确认的名称宁可不写。
4. 保留右下或左下角的 OpenStreetMap 署名。
5. 生成结果的地理结构以源 SVG 为唯一事实基准。

## 视觉目标
- 标题：{title}
- 风格：{theme}
- 允许改变：配色、纸张纹理、图标、描边、标题排版、装饰元素。
- 禁止改变：几何位置、相对距离、连通关系、POI 所属街区。

## 推荐工作流
先把源 SVG 作为结构参考图，再进行图生图或受控编辑；不要仅凭文字提示重新绘制整张地图。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
