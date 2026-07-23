from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .osm import (
    DEFAULT_NOMINATIM,
    DEFAULT_OVERPASS,
    MapDataError,
    bbox_around,
    build_overpass_query,
    fetch_overpass,
    geocode,
    normalize_elements,
    parse_bbox,
)
from .render import THEMES, render_svg, write_prompt_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geo-style-map",
        description="从 OpenStreetMap 生成拓扑准确的 SVG 底图与图像模型提示包。",
    )
    parser.add_argument("place", nargs="?", help="地点名称，例如：深圳南山科技园")
    parser.add_argument(
        "--bbox",
        help="直接指定 south,west,north,east；指定后不调用 Nominatim。",
    )
    parser.add_argument(
        "--radius-m",
        type=float,
        default=1800,
        help="围绕地点中心抓取的半径，默认 1800 米。",
    )
    parser.add_argument(
        "--poi",
        choices=["cafe", "none"],
        default="cafe",
        help="POI 类型，当前支持 cafe 或 none。",
    )
    parser.add_argument(
        "--theme",
        choices=sorted(THEMES),
        default="sketch",
        help="SVG 主题。",
    )
    parser.add_argument("--title", help="地图标题；默认使用地点名称。")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out/map.svg"),
        help="SVG 输出路径。",
    )
    parser.add_argument(
        "--prompt-output",
        type=Path,
        default=Path("out/prompt.md"),
        help="图像模型提示包输出路径。",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/geo-style-map"),
        help="API 缓存目录。",
    )
    parser.add_argument(
        "--max-poi",
        type=int,
        default=80,
        help="最多保留的 POI 数量。",
    )
    parser.add_argument(
        "--max-labels",
        type=int,
        default=30,
        help="最多绘制的 POI 标签数量。",
    )
    parser.add_argument(
        "--nominatim-endpoint",
        default=DEFAULT_NOMINATIM,
        help="Nominatim 搜索端点。",
    )
    parser.add_argument(
        "--overpass-endpoint",
        default=DEFAULT_OVERPASS,
        help="Overpass API 端点。",
    )
    return parser


def run(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.bbox:
        bbox = parse_bbox(args.bbox)
        display_name = args.place or "自定义区域"
    else:
        if not args.place:
            raise ValueError("请提供地点名称，或使用 --bbox")
        location = geocode(args.place, args.cache_dir, args.nominatim_endpoint)
        bbox = bbox_around(location["lat"], location["lon"], args.radius_m)
        display_name = location["display_name"]

    title = args.title or (args.place if args.place else display_name)
    query = build_overpass_query(bbox, args.poi)
    payload = fetch_overpass(query, args.cache_dir, args.overpass_endpoint)
    layers = normalize_elements(payload, max_poi=max(0, args.max_poi))

    svg = render_svg(
        layers=layers,
        bbox=bbox,
        title=title,
        theme_name=args.theme,
        max_labels=max(0, args.max_labels),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    write_prompt_package(args.prompt_output, title, args.theme, args.output)
    return args.output, args.prompt_output


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        svg_path, prompt_path = run(args)
    except (ValueError, MapDataError) as exc:
        parser.exit(2, f"错误：{exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "已取消。\n")

    print(f"SVG：{svg_path}")
    print(f"提示包：{prompt_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
