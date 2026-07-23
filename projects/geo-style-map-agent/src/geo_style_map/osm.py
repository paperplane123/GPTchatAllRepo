from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_NOMINATIM = "https://nominatim.openstreetmap.org/search"
DEFAULT_OVERPASS = "https://overpass-api.de/api/interpreter"


class MapDataError(RuntimeError):
    """Raised when map data cannot be fetched or interpreted."""


@dataclass(frozen=True)
class BoundingBox:
    south: float
    west: float
    north: float
    east: float

    def validate(self) -> "BoundingBox":
        if not (-90 <= self.south < self.north <= 90):
            raise ValueError("纬度范围无效，应满足 -90 <= south < north <= 90")
        if not (-180 <= self.west < self.east <= 180):
            raise ValueError("经度范围无效，应满足 -180 <= west < east <= 180")
        return self

    def as_overpass(self) -> str:
        return f"{self.south:.7f},{self.west:.7f},{self.north:.7f},{self.east:.7f}"


def bbox_around(lat: float, lon: float, radius_m: float) -> BoundingBox:
    if radius_m <= 0:
        raise ValueError("radius_m 必须大于 0")
    lat_delta = radius_m / 111_320.0
    lon_scale = max(math.cos(math.radians(lat)), 0.05)
    lon_delta = radius_m / (111_320.0 * lon_scale)
    return BoundingBox(
        south=max(-90.0, lat - lat_delta),
        west=max(-180.0, lon - lon_delta),
        north=min(90.0, lat + lat_delta),
        east=min(180.0, lon + lon_delta),
    ).validate()


def parse_bbox(value: str) -> BoundingBox:
    try:
        south, west, north, east = (float(part.strip()) for part in value.split(","))
    except (TypeError, ValueError) as exc:
        raise ValueError("bbox 格式应为 south,west,north,east") from exc
    return BoundingBox(south, west, north, east).validate()


def _cache_path(cache_dir: Path, prefix: str, payload: str) -> Path:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return cache_dir / f"{prefix}-{digest}.json"


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _user_agent() -> str:
    value = os.environ.get("GEO_STYLE_MAP_USER_AGENT", "").strip()
    if not value:
        raise MapDataError(
            "未设置 GEO_STYLE_MAP_USER_AGENT。请设置一个能识别应用且包含联系方式的 User-Agent，"
            '例如：geo-style-map-agent/0.1 (you@example.com)'
        )
    return value


def geocode(
    query: str,
    cache_dir: Path,
    endpoint: str = DEFAULT_NOMINATIM,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("地点查询不能为空")

    cache_key = json.dumps({"endpoint": endpoint, "query": query}, sort_keys=True)
    cache_file = _cache_path(cache_dir, "geocode", cache_key)
    cached = _read_json(cache_file)
    if isinstance(cached, dict):
        return cached

    params = urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1}
    )
    request = urllib.request.Request(
        f"{endpoint}?{params}",
        headers={
            "User-Agent": _user_agent(),
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MapDataError(f"地点解析失败：{exc}") from exc

    if not payload:
        raise MapDataError(f"没有找到地点：{query}")

    result = payload[0]
    normalized = {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "display_name": result.get("display_name", query),
        "boundingbox": [float(value) for value in result.get("boundingbox", [])],
    }
    _write_json(cache_file, normalized)

    # Public Nominatim allows at most 1 request/second. The cache prevents repeats.
    time.sleep(1.05)
    return normalized


def build_overpass_query(bbox: BoundingBox, poi: str = "cafe") -> str:
    area = bbox.as_overpass()
    poi_parts: list[str] = []
    if poi == "cafe":
        poi_parts = [
            f'nwr["amenity"="cafe"]({area});',
            f'nwr["shop"="coffee"]({area});',
        ]
    elif poi != "none":
        raise ValueError("当前 poi 仅支持 cafe 或 none")

    return "\n".join(
        [
            "[out:json][timeout:30];",
            "(",
            f'way["highway"]({area});',
            f'way["waterway"]({area});',
            f'way["natural"="water"]({area});',
            f'relation["natural"="water"]({area});',
            f'way["building"]({area});',
            f'way["leisure"="park"]({area});',
            f'way["landuse"="grass"]({area});',
            *poi_parts,
            ");",
            "out tags center geom;",
        ]
    )


def fetch_overpass(
    query: str,
    cache_dir: Path,
    endpoint: str = DEFAULT_OVERPASS,
) -> dict[str, Any]:
    cache_key = json.dumps({"endpoint": endpoint, "query": query}, sort_keys=True)
    cache_file = _cache_path(cache_dir, "overpass", cache_key)
    cached = _read_json(cache_file)
    if isinstance(cached, dict):
        return cached

    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "User-Agent": _user_agent(),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MapDataError(f"OpenStreetMap 数据获取失败：{exc}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise MapDataError("Overpass 返回格式异常")

    _write_json(cache_file, payload)
    return payload


def _point_from_element(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lon"]), float(element["lat"])
    center = element.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lon"]), float(center["lat"])
    geometry = element.get("geometry")
    if isinstance(geometry, list) and geometry:
        lons = [float(point["lon"]) for point in geometry if "lon" in point]
        lats = [float(point["lat"]) for point in geometry if "lat" in point]
        if lons and lats:
            return sum(lons) / len(lons), sum(lats) / len(lats)
    return None


def _geometry_from_element(element: dict[str, Any]) -> list[tuple[float, float]]:
    geometry = element.get("geometry")
    if not isinstance(geometry, list):
        return []
    points: list[tuple[float, float]] = []
    for point in geometry:
        try:
            points.append((float(point["lon"]), float(point["lat"])))
        except (KeyError, TypeError, ValueError):
            continue
    return points


def normalize_elements(
    payload: dict[str, Any],
    max_poi: int = 80,
) -> dict[str, list[dict[str, Any]]]:
    layers: dict[str, list[dict[str, Any]]] = {
        "water": [],
        "parks": [],
        "buildings": [],
        "roads": [],
        "pois": [],
    }

    poi_count = 0
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        geometry = _geometry_from_element(element)

        if tags.get("amenity") == "cafe" or tags.get("shop") == "coffee":
            if poi_count >= max_poi:
                continue
            point = _point_from_element(element)
            if point is not None:
                layers["pois"].append(
                    {
                        "point": point,
                        "name": tags.get("name:zh")
                        or tags.get("name")
                        or tags.get("brand")
                        or "咖啡",
                    }
                )
                poi_count += 1
            continue

        if tags.get("natural") == "water" or "waterway" in tags:
            if len(geometry) >= 2:
                layers["water"].append(
                    {"geometry": geometry, "closed": geometry[0] == geometry[-1]}
                )
            continue

        if tags.get("leisure") == "park" or tags.get("landuse") == "grass":
            if len(geometry) >= 3:
                layers["parks"].append({"geometry": geometry})
            continue

        if "building" in tags:
            if len(geometry) >= 3:
                layers["buildings"].append({"geometry": geometry})
            continue

        if "highway" in tags and len(geometry) >= 2:
            layers["roads"].append(
                {
                    "geometry": geometry,
                    "class": tags.get("highway", "road"),
                    "name": tags.get("name:zh") or tags.get("name") or "",
                }
            )

    return layers
