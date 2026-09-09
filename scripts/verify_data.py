"""Integrity and independent arithmetic checks for the shipped dataset."""
import json,math,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from scoring import WEIGHTS,normalize
root=pathlib.Path(__file__).resolve().parents[1]/'public/data'
fc=json.loads((root/'neighborhoods.geojson').read_text());meta=json.loads((root/'metadata.json').read_text());source=json.loads((root/'source-estimates.json').read_text())
features=fc['features'];ids=[f['properties']['id'] for f in features]
assert len(ids)==len(set(ids))==2806
assert set(ids)==set(source)
for f in features:
 p=f['properties'];s=source[p['id']]
 assert p['id'].startswith('04013') and len(p['id'])==12
 for k in [*WEIGHTS,'overall']:
  assert p[k] is None or isinstance(p[k],int) and 0<=p[k]<=100
 if p['raw_vacancy'] is not None:assert abs(p['raw_vacancy']-100*float(s['B25002_E003'])/float(s['B25002_E001']))<1e-9
 if p['raw_poverty'] is not None:assert abs(p['raw_poverty']-100*(float(s['C17002_E002'])+float(s['C17002_E003']))/float(s['C17002_E001']))<1e-9
 if p['raw_affordability'] is not None:
  den=float(s['B25070_E001'])-float(s['B25070_E011'])
  assert abs(p['raw_affordability']-100*sum(float(s[f'B25070_E{i:03}']) for i in [7,8,9,10])/den)<1e-9
 if p['overall'] is not None:
  vals={k:normalize(p['raw_'+k],meta['anchorsP05P50P95'][k],k in ['poverty','vacancy','affordability']) for k in WEIGHTS}
  weight=sum(WEIGHTS[k] for k in vals if vals[k] is not None)
  assert p['overall']==math.floor(sum(WEIGHTS[k]*v for k,v in vals.items() if v is not None)/weight+.5)
 def positions(c):
  if isinstance(c[0],(int,float)):yield c
  else:
   for part in c:yield from positions(part)
 for lon,lat in positions(f['geometry']['coordinates']):assert -114<lon<-110 and 32<lat<35
print(f'PASS: {len(features)} unique valid geometries; joins, raw rates, bounds, and all overall scores verified.')
