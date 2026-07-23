from pathlib import Path

from geo_style_map.osm import BoundingBox, bbox_around, build_overpass_query, normalize_elements
from geo_style_map.render import render_svg


def test_bbox_around_is_valid() -> None:
    bbox = bbox_around(22.533, 113.930, 1800)
    assert bbox.south < 22.533 < bbox.north
    assert bbox.west < 113.930 < bbox.east


def test_query_contains_required_layers() -> None:
    bbox = BoundingBox(22.51, 113.91, 22.55, 113.95)
    query = build_overpass_query(bbox, "cafe")
    assert 'way["highway"]' in query
    assert 'nwr["amenity"="cafe"]' in query
    assert "out tags center geom;" in query


def test_normalize_and_render_svg(tmp_path: Path) -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "tags": {"highway": "primary", "name": "测试路"},
                "geometry": [
                    {"lon": 113.92, "lat": 22.52},
                    {"lon": 113.94, "lat": 22.54},
                ],
            },
            {
                "type": "way",
                "tags": {"natural": "water"},
                "geometry": [
                    {"lon": 113.925, "lat": 22.515},
                    {"lon": 113.93, "lat": 22.515},
                    {"lon": 113.93, "lat": 22.52},
                    {"lon": 113.925, "lat": 22.515},
                ],
            },
            {
                "type": "node",
                "lat": 22.53,
                "lon": 113.935,
                "tags": {"amenity": "cafe", "name": "测试咖啡"},
            },
        ]
    }
    layers = normalize_elements(payload)
    svg = render_svg(
        layers,
        BoundingBox(22.51, 113.91, 22.55, 113.95),
        title="测试地图",
    )

    output = tmp_path / "map.svg"
    output.write_text(svg, encoding="utf-8")

    assert "测试地图" in svg
    assert "测试咖啡" in svg
    assert "OpenStreetMap contributors" in svg
    assert output.read_text(encoding="utf-8").startswith("<?xml")
