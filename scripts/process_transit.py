#!/usr/bin/env python3
"""Build a block-group transit access layer from a Valley Metro GTFS feed.

The score describes scheduled service on one representative service date. It
combines scheduled trips, distinct routes, and served stops; it is not a travel
time, reliability, or real-time accessibility measure.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
from collections import defaultdict

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_GTFS = ROOT / ".data-cache" / "valley-metro-gtfs"
OUT = ROOT / "public" / "data" / "transit.json"
FEED_URL = (
    "https://www.phoenixopendata.com/dataset/3eae9a4a-98b9-40c8-8df7-8c00c1756235/"
    "resource/28ccc0a5-49c8-495c-b91f-193de5ce2cb7/download/googletransit.zip"
)


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        yield from csv.DictReader(fh)


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    at = (len(ordered) - 1) * fraction
    low, high = int(at), min(int(at) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (at - low)


def scaled(value, low, high):
    if high <= low:
        return 50.0
    return max(0.0, min(100.0, 100 * (value - low) / (high - low)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtfs", type=pathlib.Path, default=DEFAULT_GTFS)
    parser.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"))
    args = parser.parse_args()
    gtfs = args.gtfs
    OUT.parent.mkdir(parents=True, exist_ok=True)

    active = set()
    for row in rows(gtfs / "calendar_dates.txt"):
        if row["date"] != args.date:
            continue
        if row["exception_type"] == "1":
            active.add(row["service_id"])
        elif row["exception_type"] == "2":
            active.discard(row["service_id"])
    if not active:
        raise ValueError(f"No active GTFS service IDs for {args.date}")

    route_names = {}
    for row in rows(gtfs / "routes.txt"):
        route_names[row["route_id"]] = row["route_short_name"] or row["route_id"]

    trip_routes = {}
    for row in rows(gtfs / "trips.txt"):
        if row["service_id"] in active:
            trip_routes[row["trip_id"]] = route_names.get(row["route_id"], row["route_id"])
    if not trip_routes:
        raise ValueError(f"No trips found for active service IDs on {args.date}")

    stops = {}
    for row in rows(gtfs / "stops.txt"):
        if row.get("location_type", "0") not in ("", "0"):
            continue
        try:
            stops[row["stop_id"]] = (float(row["stop_lon"]), float(row["stop_lat"]))
        except (KeyError, TypeError, ValueError):
            continue

    neighborhoods = json.loads((ROOT / "public" / "data" / "neighborhoods.geojson").read_text())
    features = neighborhoods["features"]
    geometries = [shape(feature["geometry"]) for feature in features]
    index = STRtree(geometries)
    stats = defaultdict(lambda: {"stops": set(), "routes": set(), "trips": set()})

    trip_stops = defaultdict(list)
    for row in rows(gtfs / "stop_times.txt"):
        if row["trip_id"] in trip_routes and row["stop_id"] in stops:
            trip_stops[row["trip_id"]].append(row["stop_id"])

    for trip_id, stop_ids in trip_stops.items():
        route = trip_routes[trip_id]
        for stop_id in set(stop_ids):
            point = Point(stops[stop_id])
            matches = index.query(point, predicate="within")
            if len(matches) == 0:
                continue
            area_id = features[int(matches[0])]["properties"]["id"]
            stats[area_id]["stops"].add(stop_id)
            stats[area_id]["routes"].add(route)
            stats[area_id]["trips"].add(trip_id)

    values = []
    for feature in features:
        area_id = feature["properties"]["id"]
        item = stats[area_id]
        values.append((len(item["stops"]), len(item["routes"]), len(item["trips"])))
    p05 = [percentile([v[i] for v in values], 0.05) for i in range(3)]
    p95 = [percentile([v[i] for v in values], 0.95) for i in range(3)]

    areas = {}
    for feature in features:
        area_id = feature["properties"]["id"]
        item = stats[area_id]
        raw = (len(item["stops"]), len(item["routes"]), len(item["trips"]))
        score = round(
            0.45 * scaled(raw[2], p05[2], p95[2])
            + 0.35 * scaled(raw[0], p05[0], p95[0])
            + 0.20 * scaled(raw[1], p05[1], p95[1]),
            1,
        )
        areas[area_id] = {
            "transit_access_score": score,
            "transit_stops": raw[0],
            "transit_routes": raw[1],
            "transit_trips": raw[2],
        }

    feed_info = next(rows(gtfs / "feed_info.txt"), {})
    result = {
        "metadata": {
            "title": "Valley Metro scheduled transit access",
            "source": FEED_URL,
            "agency": "Valley Metro",
            "serviceDate": f"{args.date[:4]}-{args.date[4:6]}-{args.date[6:]}",
            "feedStart": feed_info.get("feed_start_date"),
            "feedEnd": feed_info.get("feed_end_date"),
            "feedVersion": feed_info.get("feed_version"),
            "areaCount": len(features),
            "tripCount": len(trip_routes),
            "method": "45% scheduled trips + 35% served stops + 20% distinct routes; each component is clipped between county-area P05 and P95.",
            "limitations": [
                "Scheduled service is not real-time service or a reliability measure.",
                "The score is relative across Maricopa County block groups, not a travel-time or walk-shed analysis.",
                "Stops and scheduled trips can cross block-group boundaries and do not describe every nearby stop outside the area.",
            ],
        },
        "areas": areas,
    }
    OUT.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print(json.dumps({"areas": len(areas), "active_services": len(active), "active_trips": len(trip_routes), "service_date": args.date}))


if __name__ == "__main__":
    main()

