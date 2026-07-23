---
name: geo-style-map
description: Generate a topology-faithful SVG map basemap and an image-model prompt package from a place name or bounding box.
---

# Geo Style Map Skill

Use this skill when the user wants a hand-drawn, tourism, site-selection, planning, coffee, inspection, or presentation map whose geography must remain accurate.

## Workflow

1. Confirm the requested area, radius, POI category, title, and visual theme.
2. Prefer `--bbox` when the user provides exact coordinates or a GIS extent.
3. For place-name geocoding, set `GEO_STYLE_MAP_USER_AGENT` to an identifiable application User-Agent with contact information.
4. Run:

```bash
geo-style-map "深圳南山科技园" \
  --radius-m 1800 \
  --poi cafe \
  --theme sketch \
  --title "南山咖啡地图"
```

5. Use the generated SVG as the factual geometry layer.
6. Use the generated `prompt.md` with an image model for style transfer or controlled editing.
7. Never claim the styled image is geographically accurate unless it was constrained by the generated SVG.
8. Keep the OpenStreetMap attribution visible.

## Output contract

- `out/map.svg`: deterministic source-of-truth basemap.
- `out/prompt.md`: hard constraints and style instructions for an image model.
- Cached API responses under `.cache/geo-style-map/`.

## Safety and policy

- Do not implement search autocomplete against the public Nominatim endpoint.
- Do not exceed one uncached public Nominatim request per second.
- Cache repeated geocoding requests.
- For regular, bulk, or commercial use, switch to a self-hosted or commercial geocoder and an appropriate OSM data source.
