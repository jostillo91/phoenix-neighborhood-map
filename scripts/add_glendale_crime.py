#!/usr/bin/env python3
"""Add Glendale's official 2025 crime reports to the aggregate crime layer.

The source table has no point geometry, but it publishes a police-beat code for
most reports and Glendale publishes the matching beat polygons separately. This
script downloads only the fields needed to classify and aggregate reports. Raw
report identifiers remain in the ignored cache and are never written to public/.

Usage: python scripts/add_glendale_crime.py [--refresh]
Requires shapely and pyproj from scripts/requirements.txt.
"""
import argparse
import datetime
import hashlib
import json
import math
import pathlib
import urllib.parse
import urllib.request

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.data-cache' / 'glendale-crime'
OUTPUT = ROOT / 'public' / 'data' / 'crime.json'
NEIGHBORHOODS = ROOT / 'public' / 'data' / 'neighborhoods.geojson'
YEAR = 2025
V = 'violent-crime'
P = 'property-crime'
VIOLENT_CODES = {'09A', '11A', '11B', '11C', '120', '13A'}
PROPERTY_CODES = {'220', '240', *(f'23{x}' for x in 'ABCDEFGH')}
ALL_CODES = sorted(VIOLENT_CODES | PROPERTY_CODES)
CRIME_LAYER = 'https://gismaps.glendaleaz.com/gisserver/rest/services/OpenData/GPD_Crime_Data/MapServer/5'
CRIME_QUERY = CRIME_LAYER + '/query'
BEAT_LAYER = 'https://gismaps.glendaleaz.com/gisserver/rest/services/POLICE_BEATS/MapServer/0'
BEAT_QUERY = BEAT_LAYER + '/query'
POPULATION_URL = 'https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b01003.dat'
PREFIX = '1500000US04013'
TO_UTM = Transformer.from_crs(4326, 26912, always_xy=True).transform


def fetch_json(url, params, path, refresh=False):
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    request = urllib.request.Request(url + '?' + urllib.parse.urlencode(params), headers={'User-Agent': 'Phoenix-Neighborhood-Map/1.0'})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    if 'error' in data:
        raise RuntimeError(data['error'])
    path.write_text(json.dumps(data, separators=(',', ':')))
    return data


def download_population(refresh=False):
    path = CACHE / 'population.json'
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    rows = {}
    digest = hashlib.sha256()
    with urllib.request.urlopen(POPULATION_URL, timeout=120) as response:
        first = response.readline()
        digest.update(first)
        header = first.decode('utf-8-sig').strip().split('|')
        for line in response:
            digest.update(line)
            if line.startswith(PREFIX.encode()):
                values = line.decode().strip().split('|')
                row = dict(zip(header, values))
                rows[row['GEO_ID'].split('US')[1]] = {
                    'estimate': row.get('B01003_E001'),
                    'moe': row.get('B01003_M001'),
                }
    if len(rows) != 2806:
        raise ValueError(f'Expected 2,806 Maricopa block groups, found {len(rows)}')
    result = {'url': POPULATION_URL, 'sha256': digest.hexdigest(), 'rows': rows}
    path.write_text(json.dumps(result, separators=(',', ':')))
    return result


def valid_number(value):
    try:
        value = float(value)
        return value if value >= 0 and math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def clean_geometry(value):
    geometry = shape(value)
    return geometry if geometry.is_valid else geometry.buffer(0)


def rounded(value):
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    return round(value, 5) if isinstance(value, float) else value


def make_feature(geometry, properties):
    payload = mapping(geometry)
    return {'type': 'Feature', 'geometry': {'type': payload['type'], 'coordinates': rounded(payload['coordinates'])}, 'properties': properties}


def download_relevant_reports(refresh=False):
    records = []
    offset = 0
    codes = ','.join(f"'{code}'" for code in ALL_CODES)
    where = f"Occurred_On_Date >= DATE '{YEAR}-01-01' AND Occurred_On_Date < DATE '{YEAR + 1}-01-01' AND IBRCode IN ({codes})"
    while True:
        page = fetch_json(CRIME_QUERY, {
            'f': 'json', 'where': where,
            'outFields': 'OBJECTID,Case_Report_Number,Occurred_On_Date,IBRCode,BEAT_GIS',
            'returnGeometry': 'false', 'orderByFields': 'OBJECTID',
            'resultOffset': offset, 'resultRecordCount': 2000,
        }, CACHE / f'reports-{offset}.json', refresh)
        features = page.get('features', [])
        records.extend(feature['attributes'] for feature in features)
        if len(features) < 2000:
            break
        offset += len(features)
    return records, where


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    crime = json.loads(OUTPUT.read_text())
    neighborhoods = json.loads(NEIGHBORHOODS.read_text())
    population = download_population(args.refresh)
    reports, where = download_relevant_reports(args.refresh)
    beat_data = fetch_json(BEAT_QUERY, {
        'f': 'geojson', 'where': '1=1', 'outFields': 'BEAT,AGENCY',
        'returnGeometry': 'true', 'outSR': 4326,
    }, CACHE / 'beats.geojson', args.refresh)

    glendale_city = next(feature for feature in crime['cityGeography']['features'] if feature['properties']['city'] == 'Glendale')
    city_geometry = clean_geometry(glendale_city['geometry'])
    beats = {}
    for item in beat_data['features']:
        code = str(item['properties']['BEAT']).strip()
        geometry = clean_geometry(item['geometry']).intersection(city_geometry)
        if not geometry.is_empty:
            beats[code] = geometry
    if len(beats) != 24:
        raise ValueError(f'Expected 24 Glendale beats, found {len(beats)}')

    counts = {code: {V: 0, P: 0} for code in beats}
    total = {V: 0, P: 0}
    mapped = {V: 0, P: 0}
    months = {str(month): 0 for month in range(1, 13)}
    seen = set()
    for record in reports:
        code = str(record.get('IBRCode') or '').strip()
        category = V if code in VIOLENT_CODES else P if code in PROPERTY_CODES else None
        if not category:
            continue
        report_id = str(record.get('Case_Report_Number') or '').strip()
        key = (report_id, category)
        if not report_id or key in seen:
            continue
        seen.add(key)
        total[category] += 1
        timestamp = record.get('Occurred_On_Date')
        if timestamp:
            months[str(datetime.datetime.fromtimestamp(timestamp / 1000, datetime.timezone.utc).month)] += 1
        beat = str(record.get('BEAT_GIS') or '').strip()
        if beat in counts:
            counts[beat][category] += 1
            mapped[category] += 1
    if not all(months.values()):
        raise ValueError(f'Glendale source is missing one or more 2025 months: {months}')

    bg_features = neighborhoods['features']
    bg_geometries = [transform(TO_UTM, clean_geometry(feature['geometry'])) for feature in bg_features]
    tree = STRtree(bg_geometries)
    population_rows = population['rows']

    def estimate(geometry):
        projected = transform(TO_UTM, geometry)
        estimate_total = 0.0
        moe_squared = 0.0
        covered_area = 0.0
        for index in tree.query(projected, predicate='intersects'):
            source = bg_geometries[index]
            row = population_rows.get(bg_features[index]['properties']['id'], {})
            estimate_value = valid_number(row.get('estimate'))
            moe_value = valid_number(row.get('moe')) or 0
            if estimate_value is None or not source.area:
                continue
            intersection_area = projected.intersection(source).area
            weight = intersection_area / source.area
            estimate_total += weight * estimate_value
            moe_squared += (weight * moe_value) ** 2
            covered_area += intersection_area
        return estimate_total, math.sqrt(moe_squared), min(1.0, covered_area / projected.area) if projected.area else 0

    features = [feature for feature in crime['geography']['features'] if feature['properties'].get('city') != 'Glendale']
    for code, geometry in sorted(beats.items()):
        estimate_value, moe_value, coverage = estimate(geometry)
        properties = {
            'id': f'glendale-{code}', 'name': f'Glendale · police beat {code}', 'tract': code,
            'coverage': 100, 'city': 'Glendale', 'geography': 'Police beat, clipped to Glendale boundary',
            'population': round(estimate_value), 'population_moe': round(moe_value),
            'population_coverage': round(coverage, 3),
            'population_method': 'ACS 2020–2024, area-weighted estimate', 'local': True,
        }
        for category in (V, P):
            count = counts[code][category]
            properties[category + '_count'] = count
            stable = estimate_value >= 500 and coverage >= .95 and (moe_value / estimate_value if estimate_value else math.inf) <= .5
            properties[category + '_rate'] = round(count / estimate_value * 1000, 2) if stable else None
        features.append(make_feature(geometry, properties))
    crime['geography']['features'] = features

    source = {
        'city': 'Glendale', 'status': 'Neighborhood reports available',
        'geography': 'Police beats', 'url': CRIME_LAYER,
        'period': 'Jan–Dec 2025 (occurrence date)',
        'note': 'Glendale reports are assigned by the public BEAT_GIS field to official police-beat boundaries. The source transitioned to NIBRS on July 1, 2022; this layer uses the complete 2025 calendar year. Reports without a matching beat are excluded from neighborhood totals.',
        'counts': total, 'mapped': mapped, 'months': months,
    }
    crime['metadata']['sources'] = [source if item['city'] == 'Glendale' else item for item in crime['metadata']['sources']]
    crime['metadata']['audit']['Glendale'] = {
        'recordsDownloaded': len(reports), 'uniqueCategoryReports': total,
        'mapped': mapped, 'excluded': {category: total[category] - mapped[category] for category in (V, P)},
        'months': months, 'beatCount': len(beats), 'where': where,
    }
    digest = hashlib.sha256(json.dumps(reports, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    crime['metadata']['inputHashes']['glendale2025RelevantReports'] = digest
    crime['metadata']['inputHashes']['glendaleBeatGeometry'] = hashlib.sha256(json.dumps(beat_data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    crime['metadata']['inputHashes']['glendalePopulationTable'] = population['sha256']
    crime['metadata']['populationMethod'] = 'Citywide: published ACS 2020–2024 B01003 place population. Neighborhoods: ACS block-group population allocated by intersection area in UTM 12N, then aggregated to native police grids, police beats, or city-clipped Census tracts. Assumes uniform residential density within each block group; not a measured local-area population. Rates suppressed below 500 estimated residents, below 95% spatial population coverage, or above 50% relative ACS margin of error. MOE omits interpolation uncertainty.'
    crime['metadata']['retrieved'] = datetime.date.today().isoformat()
    OUTPUT.write_text(json.dumps(crime, separators=(',', ':'), allow_nan=False))
    print(json.dumps({'reportsDownloaded': len(reports), 'counts': total, 'mapped': mapped, 'months': months, 'beats': len(beats)}, indent=2))


if __name__ == '__main__':
    main()

