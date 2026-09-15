import assert from 'node:assert/strict';
import fs from 'node:fs';

const crime=JSON.parse(fs.readFileSync(new URL('../public/data/crime.json',import.meta.url)));
const local=crime.geography.features.filter(f=>f.properties.local);
const cities=new Set(local.map(f=>f.properties.city));
for(const city of ['Phoenix','Mesa','Tempe','Chandler','Glendale'])assert(cities.has(city),`${city} neighborhood coverage missing`);
const glendale=local.filter(f=>f.properties.city==='Glendale');
assert.equal(glendale.length,24);
assert.equal(new Set(glendale.map(f=>f.properties.id)).size,24);
for(const feature of glendale){
 const p=feature.properties;
 assert.match(p.id,/^glendale-\d{2}$/);
 for(const key of ['violent-crime_count','property-crime_count'])assert(Number.isInteger(p[key])&&p[key]>=0);
 for(const key of ['violent-crime_rate','property-crime_rate'])assert(p[key]===null||Number.isFinite(p[key])&&p[key]>=0);
}
const publicText=JSON.stringify(crime);
for(const forbidden of ['Case_Report_Number','Folder_Number','Location'])assert(!publicText.includes(forbidden),`${forbidden} leaked into public data`);
const source=crime.metadata.sources.find(s=>s.city==='Glendale');
assert.equal(source.status,'Neighborhood reports available');
assert.deepEqual(Object.keys(source.months),Array.from({length:12},(_,i)=>String(i+1)));
console.log(`PASS: ${glendale.length} Glendale beats; aggregate-only crime output verified.`);

