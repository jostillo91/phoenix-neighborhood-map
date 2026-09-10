#!/usr/bin/env python3
"""Build the Summer Heat layer from public Landsat Collection 2 Level-2 ST.

The script queries the Microsoft Planetary Computer STAC mirror for the
official USGS Landsat Collection 2 Level-2 products, signs the public blob
assets, masks non-land pixels with QA_PIXEL, converts ST_B10 to Fahrenheit,
and aggregates valid pixel observations to the existing Census block groups.

Usage:
  .heat-venv\\Scripts\\python.exe scripts/process_heat.py
  .heat-venv\\Scripts\\python.exe scripts/process_heat.py --refresh

Temporary catalog and raster access details stay in .data-cache/; only the
small generated public/data/heat.json file is committed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import Window, from_bounds


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CACHE = ROOT / ".data-cache"
STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN_ENDPOINT = "https://planetarycomputer.microsoft.com/api/sas/v1/sign?href="
SIGNED_CACHE_FILE = CACHE / "heat-signed-assets.json"
COLLECTION = "landsat-c2-l2"
BBOX = [-113.5, 32.75, -110.8, 34.3]
YEARS = (2022, 2023, 2024)
MAX_CLOUD = 20.0
MAX_SCENES_PER_PATH_ROW_YEAR = 1
MIN_SCENE_OBSERVATIONS = 2
ST_B10_SCALE = 0.00341802
ST_B10_OFFSET_K = 149.0
SIGNED_CACHE: dict[str, str] = {}


def get_json(url: str, *, body: dict | None = None) -> dict:
    if body is None:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
    else:
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Accept": "application/geo+json", "Content-Type": "application/json"},
            method="POST",
        )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def query_scenes(refresh: bool) -> list[dict]:
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / "heat-stac-scenes.json"
    if cached.exists() and not refresh:
        return json.loads(cached.read_text(encoding="utf-8"))

    body: dict = {
        "collections": [COLLECTION],
        "bbox": BBOX,
        "datetime": f"{YEARS[0]}-06-01T00:00:00Z/{YEARS[-1]}-08-31T23:59:59Z",
        "limit": 500,
    }
    features: list[dict] = []
    while True:
        result = get_json(STAC_SEARCH, body=body)
        features.extend(result.get("features", []))
        next_link = next((link for link in result.get("links", []) if link.get("rel") == "next"), None)
        if not next_link:
            break
        body = next_link.get("body") or {}
        if not body:
            break

    candidates = []
    for item in features:
        properties = item.get("properties", {})
        raw_date = properties.get("datetime")
        if not raw_date:
            continue
        date = dt.datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        cloud = float(properties.get("eo:cloud_cover", 100))
        if date.year not in YEARS or date.month not in (6, 7, 8):
            continue
        if cloud > MAX_CLOUD or properties.get("landsat:collection_category") != "T1":
            continue
        if not properties.get("landsat:wrs_path") or not properties.get("landsat:wrs_row"):
            continue
        if "lwir11" not in item.get("assets", {}) or "qa_pixel" not in item.get("assets", {}):
            continue
        candidates.append(item)

    groups: defaultdict[tuple[int, str, str], list[dict]] = defaultdict(list)
    for item in candidates:
        p = item["properties"]
        date = dt.datetime.fromisoformat(p["datetime"].replace("Z", "+00:00"))
        groups[(date.year, p["landsat:wrs_path"], p["landsat:wrs_row"])].append(item)

    selected = []
    for key, items in sorted(groups.items()):
        items.sort(key=lambda item: (float(item["properties"].get("eo:cloud_cover", 100)), item["id"]))
        selected.extend(items[:MAX_SCENES_PER_PATH_ROW_YEAR])
    selected.sort(key=lambda item: item["properties"]["datetime"])
    if not selected:
        raise RuntimeError("No qualifying Landsat summer scenes were returned by the STAC catalog.")
    cached.write_text(json.dumps(selected, separators=(",", ":")), encoding="utf-8")
    return selected


def sign_asset(href: str) -> str:
    cached = SIGNED_CACHE.get(href)
    if cached:
        expiry = urllib.parse.parse_qs(urllib.parse.urlsplit(cached).query).get("se", [""])[0]
        if expiry:
            try:
                if dt.datetime.fromisoformat(urllib.parse.unquote(expiry).replace("Z", "+00:00")) > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10):
                    return cached
            except ValueError:
                pass
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            signed = get_json(SIGN_ENDPOINT + urllib.parse.quote(href, safe=""))
            SIGNED_CACHE[href] = signed["href"]
            SIGNED_CACHE_FILE.write_text(json.dumps(SIGNED_CACHE, separators=(",", ":")), encoding="utf-8")
            return signed["href"]
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Unable to sign Landsat asset: {href}") from last_error


def points(geometry: dict):
    coordinates = geometry["coordinates"]
    stack = [coordinates]
    while stack:
        value = stack.pop()
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            yield value
        elif isinstance(value, list):
            stack.extend(value)


def geometry_bounds(geometry: dict) -> tuple[float, float, float, float]:
    coords = list(points(geometry))
    return (
        min(p[0] for p in coords),
        min(p[1] for p in coords),
        max(p[0] for p in coords),
        max(p[1] for p in coords),
    )


def percentile(values: list[float], p: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), p * 100))


def normalize(value: float, anchors: tuple[float, float, float]) -> int:
    low, median, high = anchors
    value = max(low, min(high, value))
    if value <= median:
        score = 50 * (value - low) / (median - low) if median > low else 50
    else:
        score = 50 + 50 * (value - median) / (high - median) if high > median else 50
    return max(0, min(100, math.floor(score + 0.5)))


def scene_window(ds, bbox: list[float]) -> Window:
    west, south, east, north = transform_bounds("EPSG:4326", ds.crs, *bbox, densify_pts=21)
    requested = from_bounds(west, south, east, north, ds.transform)
    full = Window(0, 0, ds.width, ds.height)
    return requested.round_offsets().round_lengths().intersection(full)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Refresh the STAC catalog query.")
    args = parser.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    if SIGNED_CACHE_FILE.exists():
        SIGNED_CACHE.update(json.loads(SIGNED_CACHE_FILE.read_text(encoding="utf-8")))
    neighborhoods = json.loads((DATA / "neighborhoods.geojson").read_text(encoding="utf-8"))
    features = neighborhoods["features"]
    ids = [feature["properties"]["id"] for feature in features]
    geometries = [feature["geometry"] for feature in features]

    scenes = query_scenes(args.refresh)
    print(f"Selected {len(scenes)} scenes across {len({(s['properties']['landsat:wrs_path'], s['properties']['landsat:wrs_row']) for s in scenes})} path/rows.", flush=True)

    sums = np.zeros(len(features), dtype=np.float64)
    pixel_counts = np.zeros(len(features), dtype=np.int64)
    scene_counts = np.zeros(len(features), dtype=np.int16)
    used_scene_ids: list[str] = []
    scene_records: list[dict] = []
    source_bounds = geometry_bounds(geometries[0])
    for geometry in geometries[1:]:
        b = geometry_bounds(geometry)
        source_bounds = (min(source_bounds[0], b[0]), min(source_bounds[1], b[1]), max(source_bounds[2], b[2]), max(source_bounds[3], b[3]))

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MULTIRANGE="YES"):
        for number, item in enumerate(scenes, start=1):
            props = item["properties"]
            date = dt.datetime.fromisoformat(props["datetime"].replace("Z", "+00:00"))
            assets = item["assets"]
            st_href = sign_asset(assets["lwir11"]["href"])
            qa_href = sign_asset(assets["qa_pixel"]["href"])
            print(f"[{number}/{len(scenes)}] {item['id']} cloud={props.get('eo:cloud_cover')}%", flush=True)
            with rasterio.open(st_href) as st_ds, rasterio.open(qa_href) as qa_ds:
                window = scene_window(st_ds, list(source_bounds))
                st = st_ds.read(1, window=window)
                qa = qa_ds.read(1, window=window)
                window_transform = st_ds.window_transform(window)
                transformed = ((transform_geom("EPSG:4326", st_ds.crs, geometry), index + 1) for index, geometry in enumerate(geometries))
                burned = rasterize(transformed, out_shape=st.shape, transform=window_transform, fill=0, dtype="int32")

                bad_bits = 1 | 2 | 4 | 8 | 16 | 32 | 128
                temperature_k = st.astype(np.float32) * ST_B10_SCALE + ST_B10_OFFSET_K
                valid = (
                    (burned > 0)
                    & (st > 0)
                    & ((qa & bad_bits) == 0)
                    & np.isfinite(temperature_k)
                    & (temperature_k >= 200)
                    & (temperature_k <= 400)
                )
                labels = burned[valid] - 1
                temps_f = (temperature_k[valid] - 273.15) * 9 / 5 + 32
                if labels.size:
                    sums += np.bincount(labels, weights=temps_f, minlength=len(features))
                    pixel_counts += np.bincount(labels, minlength=len(features)).astype(np.int64)
                    scene_counts[np.unique(labels)] += 1
                used_scene_ids.append(item["id"])
                scene_records.append({
                    "id": item["id"],
                    "date": date.date().isoformat(),
                    "platform": props.get("platform"),
                    "path": props.get("landsat:wrs_path"),
                    "row": props.get("landsat:wrs_row"),
                    "cloudCover": props.get("eo:cloud_cover"),
                    "surfaceTemperatureAsset": assets["lwir11"]["href"],
                    "qualityAsset": assets["qa_pixel"]["href"],
                })

    means = np.divide(sums, pixel_counts, out=np.full(len(features), np.nan), where=pixel_counts > 0)
    scored = [float(value) for value, count in zip(means, scene_counts) if math.isfinite(value) and count >= MIN_SCENE_OBSERVATIONS]
    if len(scored) < 10:
        raise RuntimeError(f"Only {len(scored)} block groups met the minimum observation requirement.")
    anchors = (percentile(scored, 0.05), percentile(scored, 0.50), percentile(scored, 0.95))

    areas = {}
    for geoid, mean, pixels, scene_count in zip(ids, means, pixel_counts, scene_counts):
        if not math.isfinite(float(mean)) or scene_count < MIN_SCENE_OBSERVATIONS:
            areas[geoid] = {"heat_score": None, "heat_temp_f": None, "heat_temp_c": None, "heat_observations": int(scene_count), "heat_pixels": int(pixels)}
            continue
        temp_f = float(mean)
        score = normalize(temp_f, anchors)
        areas[geoid] = {
            "heat_score": score,
            "heat_temp_f": round(temp_f, 1),
            "heat_temp_c": round((temp_f - 32) * 5 / 9, 1),
            "heat_observations": int(scene_count),
            "heat_pixels": int(pixels),
        }

    valid_areas = [area for area in areas.values() if area["heat_score"] is not None]
    output = {
        "metadata": {
            "title": "Summer Heat Exposure",
            "source": "USGS Landsat Collection 2 Level-2 Surface Temperature (ST_B10) via the public Microsoft Planetary Computer STAC mirror",
            "collection": COLLECTION,
            "missions": sorted({scene["platform"] for scene in scene_records}),
            "period": f"{YEARS[0]}-06-01 through {YEARS[-1]}-08-31",
            "summerMonths": [6, 7, 8],
            "studyArea": "Same 2,806 Maricopa County Census block groups as neighborhoods.geojson",
            "sceneCount": len(scene_records),
            "scoredBlockGroups": len(valid_areas),
            "unscoredBlockGroups": len(areas) - len(valid_areas),
            "minSceneObservations": MIN_SCENE_OBSERVATIONS,
            "normalization": "Piecewise linear 5th percentile→0, median→50, 95th percentile→100, with clipping. Higher scores mean hotter relative summer surface temperature.",
            "temperatureConversion": "ST_B10 Kelvin = DN × 0.00341802 + 149.0; Fahrenheit = (Kelvin − 273.15) × 9/5 + 32.",
            "qualityMask": "Excluded fill, dilated cloud, cirrus, cloud, cloud shadow, snow/ice, water, nonpositive values, and ST_B10 values outside 200–400 K using QA_PIXEL and valid ST_B10 values.",
            "aggregation": "For each Census block group, mean of all valid 30 m pixel observations across the selected scenes; at least two distinct scene dates are required for a score.",
            "anchorsFahrenheit": [round(value, 3) for value in anchors],
            "retrieved": dt.date.today().isoformat(),
            "scenes": scene_records,
            "limitations": [
                "Land surface temperature is not the same as weather-station air temperature or a forecast.",
                "Landsat observes clear-sky daytime conditions on intermittent dates; shaded and cloud-covered pixels are excluded.",
                "Surface materials, vegetation, soil moisture, elevation, and sensor viewing conditions affect the result.",
                "Water is excluded, and block groups with fewer than two valid scene dates remain unscored.",
                "A mean across available valid pixels is a relative exposure indicator, not a health-risk or indoor-temperature estimate.",
            ],
        },
        "areas": areas,
    }
    (DATA / "heat.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"scoredBlockGroups": len(valid_areas), "unscoredBlockGroups": len(areas) - len(valid_areas), "temperatureF": [round(float(np.nanmin(means)), 1), round(float(np.nanmedian(means)), 1), round(float(np.nanmax(means)), 1)], "anchorsFahrenheit": output["metadata"]["anchorsFahrenheit"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
