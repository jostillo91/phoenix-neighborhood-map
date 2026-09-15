#!/usr/bin/env python3
"""Build aggregate-only crime layers from audited public exports.

Usage: python scripts/process_crime.py --cache PATH --phoenix-csv PATH
See CRIME_DATA.md for source contracts, privacy exclusions and refresh procedure.
Requires shapely, pyproj, pyshp. Never writes incident addresses or IDs to public/.
"""
import argparse, collections, csv, datetime, hashlib, io, json, re, zipfile
from pathlib import Path
import shapefile
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
V='violent-crime'; P='property-crime'; CATS=[V,P]
VC={'09A','11A','11B','11C','120','13A'}
PC={'220','240',*[f'23{x}' for x in 'ABCDEFGH']}
LOCAL=['Phoenix','Mesa','Tempe','Chandler']
PLACES=LOCAL+['Scottsdale','Glendale','Gilbert','Peoria','Surprise','Avondale','Goodyear','Buckeye',
 'El Mirage','Tolleson','Paradise Valley','Queen Creek','Apache Junction','Maricopa','Wickenburg',
 'Fountain Hills','Cave Creek','Carefree','Guadalupe','Litchfield Park','Youngtown','Sun City',
 'Sun City West','Anthem','New River','San Tan Valley']
proj=Transformer.from_crs(4326,26912,always_xy=True).transform
unproj=Transformer.from_crs(26912,4326,always_xy=True).transform

def clean_geom(g):
 if not g.is_valid:g=g.buffer(0)
 if g.geom_type=='GeometryCollection':g=unary_union([x for x in g.geoms if x.geom_type in ('Polygon','MultiPolygon')])
 return g
def round_coords(v):
 if isinstance(v,(list,tuple)):return [round_coords(x) for x in v]
 return round(v,5) if isinstance(v,float) else v
def feature(g,p):return {'type':'Feature','geometry':{'type':g.geom_type,'coordinates':round_coords(mapping(g)['coordinates'])},'properties':p}
def number(s):
 try:
  n=float(s);return n if n>=0 else None
 except (ValueError,TypeError):return None
def year(s):return str(s or '')[:4]=='2025'
def classify(codes):return [cat for cat,cs in [(V,VC),(P,PC)] if codes&cs]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);ap.add_argument('--phoenix-csv',required=True);a=ap.parse_args();cache=Path(a.cache)
 read=lambda n:json.loads((cache/n).read_text())
 pop=read('population.json');rows=pop['rows'];pp=read('place_population.json')['rows']
 z=zipfile.ZipFile(cache/'boundaries.zip');stem='cb_2024_04_place_500k'
 sr=shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),shx=io.BytesIO(z.read(stem+'.shx')),dbf=io.BytesIO(z.read(stem+'.dbf')))
 cities={}
 for s in sr.iterShapeRecords():
  d=s.record.as_dict()
  if d['NAME'] in PLACES:cities[d['NAME']]={'geometry':clean_geom(shape(s.shape.__geo_interface__)),'id':d['GEOID'],'population':number(pp.get(d['GEOID'],{}).get('B01003_E001')),'population_moe':number(pp.get(d['GEOID'],{}).get('B01003_M001'))}
 base=read('../unused.json') if False else json.loads((ROOT/'public/data/neighborhoods.geojson').read_text())
 bg=[transform(proj,clean_geom(shape(f['geometry']))) for f in base['features']];bg_tree=STRtree(bg)
 def estimate(g):
  g=transform(proj,g);total=0.;moe=0.;area=0.
  for i in bg_tree.query(g,predicate='intersects'):
   n=number(rows.get(base['features'][i]['properties']['id'],{}).get('B01003_E001'));m=number(rows.get(base['features'][i]['properties']['id'],{}).get('B01003_M001'))
   if n is None:continue
   w=g.intersection(bg[i]).area/bg[i].area
   total+=w*n;moe+=(w*(m or 0))**2;area+=g.intersection(bg[i]).area
  return total,moe**.5,min(1.,area/g.area) if g.area else 0
 cells=[];audit={};sources=[]
 grids=read('phoenix_grids.json')['features']+read('phoenix_grids2.json')['features']
 assert len(grids)==read('grid_count.json')['count']
 assert len({f['properties']['OBJECTID'] for f in grids})==len(grids)
 grouped=collections.defaultdict(list)
 for f in grids:grouped[f['properties']['GRID_NUMBER']].append(clean_geom(shape(f['geometry'])))
 for code,gg in grouped.items():
  g=clean_geom(unary_union(gg).intersection(cities['Phoenix']['geometry']))
  if not g.is_empty and transform(proj,g).area>100:
   cells.append({'city':'Phoenix','code':code,'name':f'Phoenix · police grid {code}','geometry':g,'geography':'Police grid, clipped to Phoenix boundary'})
 for city in LOCAL[1:]:
  tracts=collections.defaultdict(list)
  for f,g in zip(base['features'],bg):
   if clean_geom(shape(f['geometry'])).intersects(cities[city]['geometry']):tracts[f['properties']['id'][:11]].append(clean_geom(shape(f['geometry'])))
  for tract,gg in tracts.items():
   g=clean_geom(unary_union(gg).intersection(cities[city]['geometry']))
   if not g.is_empty and transform(proj,g).area>100:
    cells.append({'city':city,'code':tract,'name':f'{city} · tract {tract[5:9]}.{tract[9:]}','geometry':g,'geography':'Census tract portion inside city'})
 for cell in cells:
  n,m,c=estimate(cell['geometry']);cell.update(population=n,population_moe=m,population_coverage=c,counts={k:0 for k in CATS})
 lookup={c['code']:c for c in cells if c['city']=='Phoenix'}
 trees={city:STRtree([c['geometry'] for c in cells if c['city']==city]) for city in LOCAL[1:]}
 citycells={city:[c for c in cells if c['city']==city] for city in LOCAL[1:]}
 stats={city:{'counts':collections.Counter(),'mapped':collections.Counter(),'excluded':collections.Counter(),'months':collections.Counter(),'duplicates':0} for city in LOCAL}
 seen={city:set() for city in LOCAL}
 def add(city,ident,cats,month,point=None,grid=None):
  if not cats:return
  st=stats[city]
  for cat in cats:
   key=(ident,cat)
   if key in seen[city]:st['duplicates']+=1;continue
   seen[city].add(key);st['counts'][cat]+=1;st['months'][month]+=1
   cell=None
   if city=='Phoenix':cell=lookup.get(grid)
   elif point and all(v is not None for v in point) and -114<point[0]<-110 and 32<point[1]<35:
    hits=trees[city].query(Point(point),predicate='intersects')
    if len(hits):cell=citycells[city][min(hits)]
   if cell is not None:cell['counts'][cat]+=1;st['mapped'][cat]+=1
   else:st['excluded'][cat]+=1
 with open(a.phoenix_csv,encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):
   date=r['OCCURRED ON']
   if '/2025' not in date:continue
   cat=r['UCR CRIME CATEGORY'];cats=[V] if cat in ['MURDER AND NON-NEGLIGENT MANSLAUGHTER','RAPE','ROBBERY','AGGRAVATED ASSAULT'] else [P] if cat in ['BURGLARY','LARCENY-THEFT','MOTOR VEHICLE THEFT'] else []
   add('Phoenix',r['INC NUMBER'].strip(),cats,str(int(date.split('/')[0])),grid=r['GRID'].strip())
 for r in read('mesa_occurrence2025.json'):
  if not year(r.get('occurred_date')):continue
  codes=set(re.findall(r'[A-Z0-9]+',r.get('nibrs_code','')))
  add('Mesa',r['crime_id'],classify(codes),str(int(r['occurred_date'][5:7])),point=r.get('location',{}).get('coordinates'))
 tempe=[]
 for off in range(0,28000,2000):tempe+=read(f'tempe_all_{off}.json')['features']
 assert len(tempe)==26592 and len({r['attributes']['OBJECTID'] for r in tempe})==26592
 for f in tempe:
  r=f['attributes'];off=(r.get('OffenseCustom') or '').strip();match=re.match(r'\[([A-Z0-9]+)\]',off);codes={match[1]} if match else {'13A'} if off in ['AGGRAVATED ASSAULT','CHILD ABUSE - AGGRAVATED ASSAULT'] else set()
  add('Tempe',r['PrimaryKey'].strip(),classify(codes),str(r['OccurrenceMonth']),point=[r.get('Longitude'),r.get('Latitude')])
 chandler_property={'SHOPTHEF','SHOPLIFT','LARCENYT','VEHBURG','BURGLARY','MOTORVEH','MAILTHEF','OTHVEHTF'}
 chandler_violent={'1315-0','1315-1','1302-1','1311-1','1103-0','1103-1','0999-2','0999-7','0999-6'}
 with (cache/'chandler_csv.txt').open(encoding='cp1252') as f:
  for r in csv.DictReader(f):
   if not year(r.get('report_event_date')):continue
   if r['report_status']=='CLOSED - Unfounded':continue
   summary=r['report_summary_offense_code'].strip()
   cats=[V] if r['report_primary_offense_code'] in chandler_violent or summary in {'ROBBERY','CARJACK'} else [P] if summary in chandler_property else []
   add('Chandler',r['report_id'],cats,str(int(r['report_event_date'][5:7])),point=[number(r['report_longitude']) if False else float(r['report_longitude']) if r['report_longitude'] else None,float(r['report_latitude']) if r['report_latitude'] else None])
 features=[]
 for c in cells:
  p={'id':c['city'].lower()+'-'+c['code'],'name':c['name'],'tract':c['code'],'coverage':100,'city':c['city'],'geography':c['geography'],'population':round(c['population']),'population_moe':round(c['population_moe']),'population_coverage':round(c['population_coverage'],3),'population_method':'ACS 2020–2024, area-weighted estimate','local':True}
  for cat in CATS:
   p[cat+'_count']=c['counts'][cat]
   # Suppression is a stability guard, not a confidence interval.
   p[cat+'_rate']=round(c['counts'][cat]/c['population']*1000,2) if c['population']>=500 and c['population_coverage']>=.95 and c['population_moe']/c['population']<=.5 else None
  features.append(feature(c['geometry'],p))
 for city in PLACES:
  if city not in cities or city in LOCAL:continue
  c=cities[city];features.append(feature(c['geometry'],{'id':'coverage-'+c['id'],'name':city+' · neighborhood data unavailable','tract':'','coverage':0,'city':city,'local':False,'geography':'City or Census place boundary',V+'_count':None,P+'_count':None,V+'_rate':None,P+'_rate':None,'population':c['population']}))
 notes={
 'Phoenix':'Uploaded Phoenix incident file. Counts are incident/category pairs located by police grid. A grid may cross the city edge; its Phoenix reports are shown in its Phoenix portion. Boundaries are generalized and may have changed since 2025.',
 'Mesa':'Sensitive incident locations, including homicide and sexual assault, are withheld by Mesa. Neighborhood figures count only mappable reports and substantially understate some violent offenses. Use citywide DPS totals for the broader picture. Traffic and duplicate/partial reports are excluded by the source.',
 'Tempe':'Public general-offense locations may be obfuscated. Only selected NIBRS violent and property codes are included. Tempe PD data does not include a separate ASU Police feed; campus locations must not be interpreted as complete coverage.',
 'Chandler':'General-offense reports use block-level locations and a primary offense. Unfounded reports are excluded. Primary-offense counting differs from NIBRS victim/offense totals; this is not the official SRS rate.'}
 urls={'Phoenix':'https://www.phoenixopendata.com/dataset/crime-data','Mesa':'https://data.mesaaz.gov/Police/Police-Incidents-2020-present/hpbg-2wph','Tempe':'https://www.arcgis.com/home/item.html?id=1563be5b343b4f78b1163e97a9a503ad','Chandler':'https://data.chandlerpd.com/catalog/general-offenses/'}
 for city in LOCAL:
  st=stats[city];assert set(st['months'])=={str(i) for i in range(1,13)},(city,st['months'])
  sources.append({'city':city,'status':'Neighborhood reports available','geography':'Police grids' if city=='Phoenix' else 'Census tract portions','url':urls[city],'period':'Jan–Dec 2025 (occurrence date)','note':notes[city],'counts':dict(st['counts']),'mapped':dict(st['mapped']),'months':dict(st['months'])})
  audit[city]={k:dict(v) if isinstance(v,collections.Counter) else v for k,v in st.items()}
 agency_rows=read('dps/agency_counts.json');city_features=[]
 for city,c in cities.items():
  d=next((r for r in agency_rows if r['city']==city),None)
  p={'id':'city-'+c['id'],'name':city+' · citywide agency statistics','tract':'','coverage':100 if d else 0,'city':city,'geography':'Whole city / reporting agency','local':False,'population':c['population'],'population_moe':c['population_moe'],'population_method':'ACS 2020–2024 place population','url':d['url'] if d else 'https://azcrimestatistics.azdps.gov/','source_status':d.get('status','Published agency totals; submission completeness not independently verified') if d else 'No separate city-agency series imported'}
  for cat in CATS:
   n=d.get(cat) if d else None;p[cat+'_count']=n;p[cat+'_rate']=round(n/c['population']*1000,2) if n is not None and c['population'] else None
  city_features.append(feature(c['geometry'],p))
  if city not in LOCAL:sources.append({'city':city,'status':'Citywide agency statistics only' if d else 'No separate city-agency series imported','geography':'City boundary; no neighborhood detail','url':p['url'],'period':'2025' if d else 'Unavailable','note':'Citywide totals cannot reveal differences between neighborhoods. '+('Some Valley communities are served by the Sheriff; countywide Sheriff totals are not assigned to individual towns.' if not d else 'DPS published totals; a full 12-month submission audit was not available. Zero, if reported, is not proof of safety.')})
 metadata={'retrieved':'2026-09-13','period':'2025','populationSource':pop['url'],'populationMethod':'Citywide: published ACS 2020–2024 B01003 place population. Neighborhoods: ACS block-group population allocated by intersection area in UTM 12N, then aggregated to native police grids or city-clipped Census tracts. Assumes uniform residential density within each block group; not a measured grid population. Rates suppressed below 500 estimated residents, below 95% spatial population coverage, or above 50% relative ACS margin of error. MOE omits interpolation uncertainty.','sources':sources,'audit':audit,'citywideDefinition':'Arizona DPS violent crime is victim-based and includes murder, aggravated assault, robbery and sexual assaults. Property here is the sum of DPS burglary, larceny and motor-vehicle-theft cases. Arson, fraud and vandalism are excluded. These units differ from local incident counts.','regionalAgencies':agency_rows,'inputHashes':{str(f.relative_to(cache)):hashlib.sha256(f.read_bytes()).hexdigest() for f in cache.rglob('*') if f.is_file() and f.suffix in ['.json','.zip','.txt']},'phoenixInputSHA256':hashlib.sha256(Path(a.phoenix_csv).read_bytes()).hexdigest(),'localCodeSets':{'violent':sorted(VC),'property':sorted(PC),'chandlerViolentPrimaryCodes':sorted(chandler_violent),'chandlerPropertySummaryCodes':sorted(chandler_property)},'cautions':['Reported crime is not all crime experienced.','Citywide rates use an ACS five-year denominator, not a 2025 headcount or official DPS rate.','Neighborhood values are mapped reports, not complete crime counts or a probability of victimization.','Residents are not the only people exposed: visitors, commuting, retail, airports and ASU can distort residential rates.','Date coverage does not certify that every month or offense was completely reported.','No smoothing, imputation, demographic predictors, or changes to the economic score.']}
 out=ROOT/'public/data';out.mkdir(exist_ok=True)
 (out/'crime.json').write_text(json.dumps({'geography':{'type':'FeatureCollection','features':features},'cityGeography':{'type':'FeatureCollection','features':city_features},'metadata':metadata},separators=(',',':'),allow_nan=False))
 print(json.dumps({'neighborhoodAreas':len(features),'cities':len(city_features),'citywideSources':len(agency_rows),'audit':audit},indent=2))

if __name__=='__main__':main()

