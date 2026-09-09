#!/usr/bin/env python3
"""Download official ACS table files + matching Census boundaries. No API key.
Usage: python scripts/prepare_data.py [--refresh]
Requires pyshp==3.1.6 (pip install -r scripts/requirements.txt).
Only county rows are cached. Full national raw files are streamed, never stored.
"""
import argparse, csv, datetime, hashlib, io, json, pathlib, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import shapefile
from scoring import clean, ratio, calculate, WEIGHTS

ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT/'.data-cache';OUT=ROOT/'public/data'
YEAR=2024
BASE=f'https://www2.census.gov/programs-surveys/acs/summary_file/{YEAR}/table-based-SF/data/5YRData/'
GEOMETRY=f'https://www2.census.gov/geo/tiger/GENZ{YEAR}/shp/cb_{YEAR}_04_bg_500k.zip'
TABLES=['B19013','C17002','B25002','B25077','B25070']
PREFIX='1500000US04013'

def download_table(table,refresh=False):
    cache=CACHE/f'{table}.json'
    if cache.exists() and not refresh:return json.loads(cache.read_text())
    url=BASE+f'acsdt5y{YEAR}-{table.lower()}.dat'
    print(f'Downloading {table} from Census…',flush=True)
    rows={};sha=hashlib.sha256()
    with urllib.request.urlopen(url,timeout=120) as response:
        first=response.readline();sha.update(first);header=first.decode('utf-8-sig').strip().split('|')
        for line in response:
            sha.update(line)
            if line.startswith(PREFIX.encode()):
                values=line.decode().strip().split('|')
                row=dict(zip(header,values));rows[row['GEO_ID'].split('US')[1]]=row
    if len(rows)<2000:raise ValueError(f'Incomplete county table {table}: {len(rows)} rows')
    result={'url':url,'retrieved':datetime.date.today().isoformat(),'sha256':sha.hexdigest(),'rows':rows}
    cache.write_text(json.dumps(result,separators=(',',':')))
    print(f'{table}: {len(rows)} block groups',flush=True)
    return result

def main():
    refresh=argparse.ArgumentParser();refresh.add_argument('--refresh',action='store_true');args=refresh.parse_args()
    CACHE.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool: tables=dict(zip(TABLES,pool.map(lambda t:download_table(t,args.refresh),TABLES)))
    geo=CACHE/'boundaries.zip'
    if not geo.exists() or args.refresh:
        with urllib.request.urlopen(GEOMETRY,timeout=120) as response:geo.write_bytes(response.read())
    z=zipfile.ZipFile(geo);stem=f'cb_{YEAR}_04_bg_500k'
    reader=shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),shx=io.BytesIO(z.read(stem+'.shx')),dbf=io.BytesIO(z.read(stem+'.dbf')))
    features=[];audit={};geography_ids=set()
    def rounded(coords):
        if isinstance(coords[0],(float,int)):return [round(c,5) for c in coords]
        return [rounded(c) for c in coords]
    for sr in reader.iterShapeRecords():
        rec=sr.record.as_dict()
        if rec['COUNTYFP']!='013':continue
        geoid=rec['GEOID'];geography_ids.add(geoid)
        cells={k:v for t in TABLES for k,v in tables[t]['rows'].get(geoid,{}).items() if k!='GEO_ID'}
        def e(t,n):return clean(cells.get(f'{t}_E{n:03}'))
        def total(t,ns):
            vals=[e(t,n) for n in ns]
            return sum(vals) if all(v is not None for v in vals) else None
        burden_den= e('B25070',1)-e('B25070',11) if e('B25070',1) is not None and e('B25070',11) is not None else None
        tract=rec['TRACTCE'];tract_name=str(int(tract[:4]))+('.'+tract[4:] if tract[4:]!='00' else '')
        row={'id':geoid,'name':f'Block group {rec["BLKGRPCE"]}, Census tract {tract_name}, Maricopa County, Arizona',
             'tract':tract_name,'raw_income':e('B19013',1),'raw_poverty':ratio(total('C17002',[2,3]),e('C17002',1)),
             'raw_vacancy':ratio(e('B25002',3),e('B25002',1)),'raw_value':e('B25077',1),
             'raw_affordability':ratio(total('B25070',[7,8,9,10]),burden_den),'renters_computed':burden_den,
             'housing_units':e('B25002',1),'poverty_universe':e('C17002',1),
             'income_moe':clean(cells.get('B19013_M001')),'value_moe':clean(cells.get('B25077_M001'))}
        geom=sr.shape.__geo_interface__;geom['coordinates']=rounded(geom['coordinates'])
        features.append({'type':'Feature','properties':row,'geometry':geom});audit[geoid]=cells
    unmatched={t:sorted(set(tables[t]['rows'])-geography_ids) for t in TABLES}
    if any(unmatched.values()):raise ValueError(f'ACS rows lack geometry: {unmatched}')
    features.sort(key=lambda f:f['properties']['id'])
    anchors=calculate([f['properties'] for f in features])
    result={'type':'FeatureCollection','features':features}
    (OUT/'neighborhoods.geojson').write_text(json.dumps(result,separators=(',',':'),allow_nan=False))
    (OUT/'source-estimates.json').write_text(json.dumps(audit,separators=(',',':')))
    metadata={'title':'Phoenix Valley Neighborhood Conditions Map','year':YEAR,'period':'2020–2024','geographyYear':YEAR,
      'retrieved':max(t['retrieved'] for t in tables.values()),'unitLabel':'Block groups','featureCount':len(features),
      'scope':'All Maricopa County, Arizona (FIPS 04013), including rural areas; excludes Pinal County.',
      'overallScored':sum(f['properties']['overall'] is not None for f in features),
      'missingByMetric':{k:sum(f['properties'][k] is None for f in features) for k in WEIGHTS},
      'sources':[{k:v for k,v in tables[t].items() if k!='rows'}|{'table':t} for t in TABLES]+[{'url':GEOMETRY,'year':YEAR,'scale':'1:500,000','sha256':hashlib.sha256(geo.read_bytes()).hexdigest()}],
      'weights':WEIGHTS,'anchorsP05P50P95':anchors,'normalization':'Piecewise linear P05→0, P50→50, P95→100 with clipping; reverse poverty, vacancy, affordability. Equal weight per block group in percentile calculation. Compute overall from unrounded metric scores; round displayed scores half-up.',
      'missingPolicy':'Negative Census sentinels, nonnumeric values, nulls, invalid ratios and zero denominators become null. At least 75% available weight plus income and poverty required for overall; rescale available weights.',
      'variables':{'income':'B19013_E001','poverty':'100*(C17002_E002+C17002_E003)/C17002_E001','vacancy':'100*B25002_E003/B25002_E001','value':'B25077_E001','affordability':'100*(B25070_E007+E008+E009+E010)/(B25070_E001-B25070_E011)'},
      'limitations':['ACS 5-year estimates are not current live conditions.','Margins of error are retained in source-estimates.json; composite uncertainty is not modeled.','Income, poverty and value are correlated; score favors economic resources.','Vacancy includes seasonal and recreational units.','Rent burden excludes homeowners and renters without computable ratios.','Median income/value top-code sentinels are treated as missing, not fabricated exact values.','Generalized coast-clipped boundaries are for visualization, not cadastral use.','No crime data, schools, environmental conditions or protected demographic variables are scored.']}
    (OUT/'metadata.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:metadata[k] for k in ['featureCount','overallScored','missingByMetric']},indent=2),flush=True)
    print('GeoJSON bytes:',(OUT/'neighborhoods.geojson').stat().st_size)
if __name__=='__main__':main()
