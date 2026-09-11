#!/usr/bin/env python3
"""Build the Tree Canopy layer from the public USFS/MRLC NLCD TCC service.

The service exposes the current CONUS NLCD Tree Canopy Cover product as a
30-meter, 0–100 percent raster. This script requests only the Phoenix Valley
extent, rasterizes the existing Census block groups onto the same grid, and
stores each block group's mean valid canopy percentage plus a robust relative
score. The downloaded raster stays in .data-cache/ and is never committed.

Usage:
  .heat-venv\\Scripts\\python.exe scripts/process_tree_canopy.py
  .heat-venv\\Scripts\\python.exe scripts/process_tree_canopy.py --refresh
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import urllib.parse
import urllib.request

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CACHE = ROOT / ".data-cache"
SERVICE = "https://imagery.geoplatform.gov/iipp/rest/services/Vegetation/USFS_EDW_NLCD_TCC_CONUS/ImageServer"
SOURCE_YEAR = 2025
SOURCE_VERSION = "v2025-6"
PIXEL_SIZE_METERS = 30


def points(geometry: dict):
    stack = [geometry["coordinates"]]
    while stack:
        value = stack.pop()
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            yield value
        elif isinstance(value, list):
            stack.extend(value)


def geometry_bounds(geometries: list[dict]) -> tuple[float, float, float, float]:
    coords = [point for geometry in geometries for point in points(geometry)]
    return (
        min(point[0] for point in coords),
        min(point[1] for point in coords),
        max(point[0] for point in coords),
        max(point[1] for point in coords),
    )


def percentile(values: list[float], fraction: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), fraction * 100))


def normalize(value: float, anchors: tuple[float, float, float]) -> int:
    low, median, high = anchors
    value = max(low, min(high, value))
    if value <= median:
        score = 50 * (value - low) / (median - low) if median > low else 50
    else:
        score = 50 + 50 * (value - median) / (high - median) if high > median else 50
    return max(0, min(100, math.floor(score + 0.5)))


def web_mercator_bounds(bounds: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, south, east, north = bounds

    def project(lon: float, lat: float) -> tuple[float, float]:
        x = lon * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        return x, y * 20037508.34 / 180

    west_x, south_y = project(west, south)
    east_x, north_y = project(east, north)
    return west_x, south_y, east_x, north_y


def download_raster(bounds: tuple[float, float, float, float], refresh: bool) -> pathlib.Path:
    CACHE.mkdir(exist_ok=True)
    output = CACHE / f"tree-canopy-{SOURCE_YEAR}.tif"
    if output.exists() and not refresh:
        return output

    west, south, east, north = web_mercator_bounds(bounds)
    width = math.ceil((east - west) / PIXEL_SIZE_METERS)
    height = math.ceil((north - south) / PIXEL_SIZE_METERS)
    east = west + width * PIXEL_SIZE_METERS
    south = north - height * PIXEL_SIZE_METERS
    params = {
        "f": "image",
        "format": "tiff",
        "bbox": f"{west},{south},{east},{north}",
        "bboxSR": "3857",
        "imageSR": "3857",
        "size": f"{width},{height}",
        "pixelType": "U8",
        "noData": "255",
        "interpolation": "RSP_NearestNeighbor",
        "mosaicRule": json.dumps({"where": f"beginyear={SOURCE_YEAR}"}, separators=(",", ":")),
    }
    url = f"{SERVICE}/exportImage?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "image/tiff"})
    with urllib.request.urlopen(request, timeout=300) as response:
        output.write_bytes(response.read())
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Redownload the source raster.")
    args = parser.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    neighborhoods = json.loads((DATA / "neighborhoods.geojson").read_text(encoding="utf-8"))
    features = neighborhoods["features"]
    ids = [feature["properties"]["id"] for feature in features]
    geometries = [feature["geometry"] for feature in features]
    source_bounds = geometry_bounds(geometries)
    raster_path = download_raster(source_bounds, args.refresh)

    with rasterio.open(raster_path) as source:
        values = source.read(1)
        transformed = [
            (transform_geom("EPSG:4326", source.crs, geometry), index + 1)
            for index, geometry in enumerate(geometries)
        ]
        labels = rasterize(
            transformed,
            out_shape=values.shape,
            transform=source.transform,
            fill=0,
            dtype="int32",
        )

    valid = (labels > 0) & (values >= 0) & (values <= 100)
    sums = np.bincount(labels[valid] - 1, weights=values[valid], minlength=len(features))
    counts = np.bincount(labels[valid] - 1, minlength=len(features)).astype(np.int64)
    means = np.divide(sums, counts, out=np.full(len(features), np.nan), where=counts > 0)
    scored_values = [float(value) for value in means if math.isfinite(float(value))]
    if len(scored_values) < 10:
        raise RuntimeError(f"Only {len(scored_values)} block groups received canopy pixels.")
    anchors = (
        percentile(scored_values, 0.05),
        percentile(scored_values, 0.50),
        percentile(scored_values, 0.95),
    )

    areas = {}
    for geoid, mean, pixel_count in zip(ids, means, counts):
        if not math.isfinite(float(mean)) or pixel_count == 0:
            areas[geoid] = {
                "tree_canopy_score": None,
                "tree_canopy_pct": None,
                "tree_canopy_valid_pixels": int(pixel_count),
            }
            continue
        raw = float(mean)
        areas[geoid] = {
            "tree_canopy_score": normalize(raw, anchors),
            "tree_canopy_pct": round(raw, 2),
            "tree_canopy_valid_pixels": int(pixel_count),
        }

    scored = [area for area in areas.values() if area["tree_canopy_score"] is not None]
    output = {
        "metadata": {
            "title": "Tree Canopy Coverage",
            "source": "USDA Forest Service NLCD Tree Canopy Cover CONUS",
            "sourceAgency": "USDA Forest Service Geospatial Office / Multi-Resolution Land Characteristics Consortium",
            "datasetVersion": SOURCE_VERSION,
            "year": SOURCE_YEAR,
            "period": str(SOURCE_YEAR),
            "spatialResolution": "30 meters",
            "metric": "Mean percent tree canopy cover across valid NLCD 30 m pixels intersecting each Census block group.",
            "waterMask": "The NLCD TCC product masks water and non-tree agriculture during production; non-processing and background pixels (254/255) are excluded here.",
            "denominator": "Valid NLCD TCC pixels inside the exact Census block-group geometry; each valid pixel contributes equally to the block-group mean.",
            "aggregation": "Rasterize the existing 2,806 Census block-group geometries onto the 30 m source grid and average valid pixel percentages by GEOID.",
            "studyArea": "Same 2,806 Maricopa County Census block groups as neighborhoods.geojson",
            "sourceService": SERVICE,
            "scoredBlockGroups": len(scored),
            "unscoredBlockGroups": len(areas) - len(scored),
            "normalization": "Piecewise linear 5th percentile→0, median→50, 95th percentile→100, with clipping. Higher scores mean more relative tree canopy.",
            "anchorsPercent": [round(value, 3) for value in anchors],
            "retrieved": dt.date.today().isoformat(),
            "limitations": [
                "The product estimates tree canopy percentage at 30 m and does not identify individual trees or canopy height.",
                "The source year is 2025, while the Summer Heat composite covers 2022–2024; the layers are independently measured and not mathematically derived from one another.",
                "The NLCD product applies its own water, non-tree agriculture, filtering, and interannual-noise processing before aggregation.",
                "Generalized Census boundaries and 30 m pixels can smooth small canopy patches along block-group edges.",
            ],
        },
        "areas": areas,
    }
    (DATA / "tree-canopy.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "scoredBlockGroups": len(scored),
        "unscoredBlockGroups": len(areas) - len(scored),
        "rawPercent": [round(float(np.nanmin(means)), 2), round(float(np.nanmedian(means)), 2), round(float(np.nanmax(means)), 2)],
        "anchorsPercent": output["metadata"]["anchorsPercent"],
        "raster": str(raster_path),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()

